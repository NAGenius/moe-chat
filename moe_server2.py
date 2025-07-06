# moe_server.py
from typing import Union  # 用于类型注解兼容
import argparse  # 新增：用于解析命令行参数

import os
import time
import uuid
import torch
import torch.nn.functional as F
from typing import List, Optional, Literal, Generator
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from collections import defaultdict
from transformers import AutoModelForCausalLM, AutoTokenizer

# ========== 环境配置 ==========
os.environ['DISABLE_MODELSCOPE_HUBUTILS'] = '1'
os.environ['WORLD_SIZE'] = '1'
os.environ['RANK'] = '0'
os.environ['LOCAL_RANK'] = '0'

# ========== 常量 ==========
MODEL_PATH = "/mnt/nvme/qwen/Qwen1___5-MoE-A2___7B-Chat"
device = "cuda" if torch.cuda.is_available() else "cpu"
DEBUG_MODE = False  # 是否启用详细调试输出

# ========== FastAPI 初始化 ==========
app = FastAPI()

# ========== 请求结构定义 ==========
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 100
    stream: Optional[bool] = False

# ========== 全局变量 ==========
model = None
tokenizer = None
expert_activations = []
hook_call_count = 0

# ========== Hook 函数 ==========
def detailed_track_experts(module, input, output):
    global hook_call_count, expert_activations
    hook_call_count += 1
    router_logits = None

    if isinstance(output, tuple):
        for item in output:
            if hasattr(item, 'shape') and item.shape[-1] in [60, 64, 8, 4]:
                router_logits = item
    elif hasattr(output, 'shape') and output.shape[-1] in [60, 64, 8, 4]:
        router_logits = output
    if DEBUG_MODE:
        print(f"Hook调用 #{hook_call_count}: {type(module).__name__}")

    if router_logits is not None:
        if router_logits.dim() == 1:
            router_logits = router_logits.unsqueeze(0).unsqueeze(0)
        elif router_logits.dim() == 2:
            router_logits = router_logits.unsqueeze(1)
        probs = F.softmax(router_logits, dim=-1)
        top_experts = torch.topk(probs, k=4, dim=-1).indices.cpu().tolist()
        expert_activations.append({
            'module': type(module).__name__,
            'hook_call': hook_call_count,
            'experts': top_experts,
            'shape': router_logits.shape
        })
        if DEBUG_MODE:
            print(f"  ✅ 成功记录专家激活: {top_experts}")


# ========== 模型加载函数 ==========
def check_model_path(path):
    if not os.path.exists(path):
        return False
    required = ['config.json', 'tokenizer.json', 'tokenizer_config.json']
    return all(os.path.exists(os.path.join(path, f)) for f in required)

def load_model():
    global model, tokenizer
    if not check_model_path(MODEL_PATH):
        raise RuntimeError(f"模型路径不完整: {MODEL_PATH}")

    print("✅ 正在加载模型...")
    model_local = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        device_map="auto",
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    tokenizer_local = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
    if tokenizer_local.pad_token is None:
        tokenizer_local.pad_token = tokenizer_local.eos_token

    # ========== Hook 注册策略 ==========
    # Hook 注册采用三阶段回退策略：
    #   1. 精确注册 MoE / Expert / Router / Gate 层
    #   2. 若失败则尝试所有 MLP 层
    #   3. 最后退化注册前 5 个 Transformer 层
    hook_targets = []

    for name, module in model_local.named_modules():
        if any(k in name.lower() for k in ['moe', 'expert', 'router', 'gate']):
            module.register_forward_hook(detailed_track_experts)
            hook_targets.append(name)

    if len(hook_targets) == 0:
        if DEBUG_MODE:
            print("⚠️ 未检测到 MoE 相关模块，尝试回退到 MLP 层 Hook...")
        for name, module in model_local.named_modules():
            if 'mlp' in name.lower():
                module.register_forward_hook(detailed_track_experts)
                hook_targets.append(name)

    if len(hook_targets) == 0:
        if DEBUG_MODE:
            print("⚠️ MLP 也未命中，尝试回退到 Transformer 层（仅注册前5个）")
        for name, module in model_local.named_modules():
            if any(k in name.lower() for k in ['layer', 'block', 'transformer']):
                if len(hook_targets) < 5:
                    module.register_forward_hook(detailed_track_experts)
                    hook_targets.append(name)

    if DEBUG_MODE:
        print(f"✅ 已注册 {len(hook_targets)} 个 Hook 层:")
        for name in hook_targets[:10]:
            print(f"  • {name}")
        if len(hook_targets) > 10:
            print(f"  ... 还有 {len(hook_targets) - 10} 个未显示")

    model_local.eval()
    model = model_local
    tokenizer = tokenizer_local

# ========== 启动事件 ==========
@app.on_event("startup")
def startup_event():
    load_model()

# ========== 专家信息封装 ==========
def get_expert_info(max_records: int = 5):
    info = {
        "total_hooks": hook_call_count,
        "activation_records": len(expert_activations),
        "details": [],
        "usage": {}
    }

    for i, act in enumerate(expert_activations[:max_records]):
        info["details"].append({
            "module": act["module"],
            "hook_call": act["hook_call"],
            "shape": list(act["shape"]),
            "experts": act["experts"]
        })

    usage = defaultdict(int)
    for record in expert_activations:
        for batch in record['experts']:
            for token_experts in batch:
                for expert_id in token_experts:
                    usage[expert_id] += 1

    info["usage"] = dict(sorted(usage.items(), key=lambda x: x[1], reverse=True))
    return info

# ========== 模型结构诊断函数 ==========
def diagnose_model_structure(model, max_items=20):
    total_modules = 0
    moe_related = []
    module_list = []

    for name, module in model.named_modules():
        total_modules += 1
        module_type = type(module).__name__
        module_list.append((name, module_type))
        if any(k in name.lower() for k in ['moe', 'expert', 'gate', 'router', 'mlp']):
            moe_related.append({
                "name": name,
                "type": module_type
            })
    if DEBUG_MODE:
        print(f"�� 模型总模块数: {total_modules}")
        print(f"�� MoE 相关模块数: {len(moe_related)}")
    return {
        "total_modules": total_modules,
        "sample_modules": [{"name": name, "type": t} for name, t in module_list[:max_items]],
        "moe_related": moe_related
    }

# ========== 推理主函数 ==========
def chat_generate(prompt_text, temperature=0.7, max_tokens=100, stream=False) -> Union[str, Generator]:
    inputs = tokenizer([prompt_text], return_tensors="pt").to(device)
    if stream:
        def token_stream():
            generated = model.generate(
                inputs.input_ids,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
                use_cache=True
            )
            new_tokens = generated[:, inputs.input_ids.shape[1]:]
            for token_id in new_tokens[0]:
                text = tokenizer.decode(token_id, skip_special_tokens=True)
                yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        return token_stream()

    with torch.no_grad():
        outputs = model.generate(
            inputs.input_ids,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            use_cache=True
        )
    generated_ids = outputs[:, inputs.input_ids.shape[1]:]
    return tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

# ========== Chat API ==========
@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    global expert_activations, hook_call_count
    expert_activations.clear()
    hook_call_count = 0

    messages = [m.dict() for m in req.messages]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    if req.stream:
        stream = chat_generate(prompt, req.temperature, req.max_tokens, stream=True)
        return StreamingResponse(stream, media_type="text/event-stream")

    result = chat_generate(prompt, req.temperature, req.max_tokens)
    response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    print(f'响应：{result}')
    print(get_expert_info())

    return {
        "id": response_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(tokenizer.encode(prompt)),
            "completion_tokens": len(tokenizer.encode(result)),
            "total_tokens": len(tokenizer.encode(prompt)) + len(tokenizer.encode(result))
        },
        "expert_info": get_expert_info()
    }

# ========== 健康检查 ==========
@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": device,
        "torch_version": torch.__version__,
        "model_loaded": model is not None
    }

# ========== 模型结构调试接口 ==========
@app.get("/debug/model_structure")
def get_model_structure():
    if model is None:
        return {"error": "模型未加载"}
    return diagnose_model_structure(model)

# ========== 获取模型信息 ==========
@app.get("/v1/models")
async def list_models():
    """列出所有可用模型（兼容OpenAI API格式）"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen1.5-moe-a2-7b-chat",
                "object": "model",
                "created": 1751604676,
                "owned_by": "vllm",
                "root": "models/qwen1.5-moe-a2-7b-chat",
                "parent": None,
                "max_model_len": 4096,
                "permission": [
                    {
                        "id": "modelperm-132753c82dfa4e1a966dea5a0100ace9",
                        "object": "model_permission",
                        "created": 1751604676,
                        "allow_create_engine": False,
                        "allow_sampling": True,
                        "allow_logprobs": True,
                        "allow_search_indices": False,
                        "allow_view": True,
                        "allow_fine_tuning": False,
                        "organization": "*",
                        "group": None,
                        "is_blocking": False
                    }
                ]
            }
        ]
    }
    
# ========== 命令行启动入口 ==========
def main():
    global DEBUG_MODE
    import uvicorn
    import argparse

    # 命令行参数解析
    parser = argparse.ArgumentParser(description="启动 MoE Debug Server")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--port", type=int, default=8002, help="设置运行端口，默认为8000")
    args = parser.parse_args()

    DEBUG_MODE = args.debug
    port = args.port

    print("�� 启动 MoE Debug Server")
    print(f"�� 地址: http://127.0.0.1:{port}")
    print(f"��️  调试模式: {'开启' if DEBUG_MODE else '关闭'}")

    uvicorn.run("moe_server:app", host="0.0.0.0", port=port, reload=False)



if __name__ == "__main__":
    main()

