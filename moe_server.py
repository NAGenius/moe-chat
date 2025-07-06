# moe_server.py
import argparse
import os
import time
import uuid
import torch
import torch.nn.functional as F
from typing import List, Optional, Literal, Generator, Union
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from collections import defaultdict
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig
import datetime
import json

# ========== 环境配置 ==========
os.environ['DISABLE_MODELSCOPE_HUBUTILS'] = '1'
os.environ['WORLD_SIZE'] = '1'
os.environ['RANK'] = '0'
os.environ['LOCAL_RANK'] = '0'

# ========== 常量 ==========
MODEL_PATH = "/home/nvidia/MoE/deepseek-ai/deepseek-moe-16b-chat"
DEVICE = "cuda"
DEVICE_ID = "0"
CUDA_DEVICE = f"{DEVICE}:{DEVICE_ID}" if DEVICE_ID else DEVICE
DEBUG_MODE = False

# ========== FastAPI 初始化 ==========
app = FastAPI(title="DeepSeek MoE API Server", version="2.0")

# ========== 请求结构定义 ==========
class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    model: str = "deepseek-moe-16b-chat"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False

class LegacyRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 512

# ========== 全局变量 ==========
model = None
tokenizer = None
expert_activations = []
hook_call_count = 0
hooks = []

# ========== GPU内存清理函数 ==========
def torch_gc():
    if torch.cuda.is_available():
        with torch.cuda.device(CUDA_DEVICE):
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()

# ========== Hook函数 - 保留原有的详细追踪逻辑 ==========
def detailed_track_experts(module, input, output):
    """详细的专家激活追踪函数 - 专门针对DeepSeek MoE优化"""
    global hook_call_count
    hook_call_count += 1

    try:
        module_name = str(type(module).__name__)
        module_full_name = getattr(module, "_module_name", "unknown")

        # 重点关注MoEGate层 - 这是专家选择的核心
        is_moe_gate = module_name == "MoEGate"
        is_deepseek_moe = module_name == "DeepseekMoE"
        is_potential_moe = any(
            keyword in module_full_name.lower()
            for keyword in ["moe", "expert", "gate", "router"]
        )

        # 对于MoE相关层或前50个调用，打印详细信息
        should_log_detail = (
            (hook_call_count <= 50 and DEBUG_MODE)
            or is_moe_gate
            or is_deepseek_moe
            or is_potential_moe
        )

        should_log_detail = False

        if should_log_detail:
            print(f"\n=== Hook调用 #{hook_call_count} ===")
            print(f"模块类型: {module_name}")
            print(f"完整路径: {module_full_name}")
            print(
                f"MoE相关: Gate={is_moe_gate}, MoE={is_deepseek_moe}, 潜在={is_potential_moe}"
            )

        # 专门处理MoEGate的输出格式
        if is_moe_gate and isinstance(output, tuple) and len(output) >= 2:
            expert_indices = None
            expert_weights = None

            # 根据日志分析，MoEGate输出格式为：(indices, weights, aux_loss)
            if len(output) >= 2:
                item0, item1 = output[0], output[1]

                # 检查第一个输出是否是专家索引 (int64类型)
                if hasattr(item0, "shape") and hasattr(item0, "dtype"):
                    if item0.dtype == torch.int64 and len(item0.shape) == 2:
                        expert_indices = item0
                        if should_log_detail:
                            print(
                                f"✅ 发现专家索引: shape={item0.shape}, dtype={item0.dtype}"
                            )

                # 检查第二个输出是否是专家权重 (float类型)
                if hasattr(item1, "shape") and hasattr(item1, "dtype"):
                    if (
                        item1.dtype in [torch.float32, torch.float16, torch.bfloat16]
                        and len(item1.shape) == 2
                    ):
                        expert_weights = item1
                        if should_log_detail:
                            print(
                                f"✅ 发现专家权重: shape={item1.shape}, dtype={item1.dtype}"
                            )

            # 如果同时找到索引和权重，记录专家激活
            if expert_indices is not None and expert_weights is not None:
                try:
                    # 转换为Python列表以便后续处理
                    indices_list = expert_indices.cpu().tolist()
                    weights_list = expert_weights.cpu().tolist()

                    expert_activations.append(
                        {
                            "module": module_name,
                            "full_name": module_full_name,
                            "hook_call": hook_call_count,
                            "expert_indices": indices_list,
                            "expert_weights": weights_list,
                            "indices_shape": list(expert_indices.shape),
                            "weights_shape": list(expert_weights.shape),
                            "type": "moe_gate_output",
                            "num_tokens": expert_indices.shape[0],
                            "experts_per_token": expert_indices.shape[1],
                        }
                    )

                    if should_log_detail:
                        print(f"🎉 成功记录MoE专家激活!")
                        print(f"   Token数量: {expert_indices.shape[0]}")
                        print(f"   每个token的专家数: {expert_indices.shape[1]}")
                        # 显示第一个token选择的专家
                        if len(indices_list) > 0 and len(indices_list[0]) > 0:
                            first_token_experts = indices_list[0]
                            first_token_weights = weights_list[0]
                            print(f"   第一个token选择的专家: {first_token_experts}")
                            print(
                                f"   对应权重: {[f'{w:.4f}' for w in first_token_weights]}"
                            )

                except Exception as e:
                    if DEBUG_MODE:
                        print(f"❌ 处理MoE Gate输出时出错: {e}")

        # 继续检查其他可能的MoE输出格式（保持兼容性）
        elif isinstance(output, tuple):
            for i, item in enumerate(output):
                if hasattr(item, "shape") and len(item.shape) >= 2:
                    # 检查是否是router logits（需要softmax的概率分布）
                    if item.dtype in [torch.float32, torch.float16, torch.bfloat16]:
                        last_dim = item.shape[-1]
                        if 8 <= last_dim <= 256:  # 合理的专家数量范围
                            try:
                                # 尝试作为router logits处理
                                probs = F.softmax(item, dim=-1)
                                k = min(8, last_dim)
                                top_k_result = torch.topk(probs, k=k, dim=-1)
                                top_experts = top_k_result.indices.cpu().tolist()
                                top_probs = top_k_result.values.cpu().tolist()

                                expert_activations.append(
                                    {
                                        "module": module_name,
                                        "full_name": module_full_name,
                                        "hook_call": hook_call_count,
                                        "expert_indices": top_experts,
                                        "expert_probabilities": top_probs,
                                        "logits_shape": list(item.shape),
                                        "type": "router_logits",
                                    }
                                )

                                if should_log_detail:
                                    print(
                                        f"🎯 发现Router Logits: 项{i}, shape={item.shape}"
                                    )
                                    print(f"   Top专家: {top_experts}")

                            except Exception as e:
                                if should_log_detail and DEBUG_MODE:
                                    print(f"❌ 处理Router Logits时出错: {e}")

        if should_log_detail:
            print("=" * 50)

    except Exception as e:
        if DEBUG_MODE:
            print(f"Hook #{hook_call_count} 处理错误: {e}")

# ========== Hook设置函数 - 保留原有逻辑 ==========
def setup_expert_hooks(model):
    """为模型设置专家追踪hooks"""
    global hooks

    # 清理之前的hooks
    for hook in hooks:
        hook.remove()
    hooks = []

    hook_targets = []

    if DEBUG_MODE:
        print("🔍 分析模型结构...")

    # 首先打印模型的基本结构
    layer_types = {}
    for name, module in model.named_modules():
        module_type = type(module).__name__
        if module_type not in layer_types:
            layer_types[module_type] = []
        layer_types[module_type].append(name)

    if DEBUG_MODE:
        print("📊 模型中的层类型:")
        for layer_type, names in layer_types.items():
            print(f"  {layer_type}: {len(names)}个")

    # 策略1: 寻找DeepSeek MoE相关的层
    moe_keywords = ["moe", "expert", "gate", "router", "ffn", "feed_forward"]

    for name, module in model.named_modules():
        module_name_lower = name.lower()
        # 为每个模块设置一个标识符
        module._module_name = name

        # 检查是否是MoE相关层
        if any(keyword in module_name_lower for keyword in moe_keywords):
            hook = module.register_forward_hook(detailed_track_experts)
            hooks.append(hook)
            hook_targets.append(name)

    # 策略2: 如果策略1没找到足够的层，扩大搜索范围
    if len(hook_targets) < 5:
        if DEBUG_MODE:
            print("🔧 策略1结果不足，扩大搜索范围...")

        # 寻找可能包含FFN或MLP的层
        additional_keywords = ["mlp", "linear", "dense", "layer"]

        for name, module in model.named_modules():
            if name not in [target for target in hook_targets]:  # 避免重复
                module_name_lower = name.lower()
                module._module_name = name

                # 检查是否包含FFN相关的层
                if any(keyword in module_name_lower for keyword in additional_keywords):
                    # 限制hook数量避免过多输出
                    if len(hook_targets) < 20:
                        hook = module.register_forward_hook(detailed_track_experts)
                        hooks.append(hook)
                        hook_targets.append(name)

    print(f"✅ 总共注册了 {len(hook_targets)} 个Hook")
    return len(hook_targets) > 0

# ========== 专家统计函数 ==========
def get_expert_info(max_records: int = 5):
    """获取专家使用统计信息"""
    info = {
        "total_hooks": hook_call_count,
        "activation_records": len(expert_activations),
        "details": [],
        "usage": {},
        "summary": ""
    }

    # 添加详细记录
    for i, activation in enumerate(expert_activations[:max_records]):
        detail = {
            "module": activation["module"],
            "hook_call": activation["hook_call"],
            "type": activation.get("type", "unknown")
        }
        
        if "indices_shape" in activation:
            detail["shape"] = activation["indices_shape"]
            detail["experts"] = activation["expert_indices"]
        elif "logits_shape" in activation:
            detail["shape"] = activation["logits_shape"]
            detail["experts"] = activation["expert_indices"]
            
        info["details"].append(detail)

    # 统计专家使用
    expert_usage = defaultdict(int)
    for activation in expert_activations:
        experts = activation.get("expert_indices", [])
        if isinstance(experts, list):
            for batch in experts:
                if isinstance(batch, list):
                    for token_experts in batch:
                        if isinstance(token_experts, list):
                            for expert_id in token_experts:
                                expert_usage[expert_id] += 1
                        else:
                            expert_usage[token_experts] += 1
                else:
                    expert_usage[batch] += 1

    info["usage"] = dict(sorted(expert_usage.items(), key=lambda x: x[1], reverse=True))
    
    # 生成摘要
    if expert_usage:
        top_experts = list(info["usage"].keys())[:5]
        info["summary"] = f"共激活{len(expert_activations)}次，主要使用专家: {top_experts}"
    else:
        info["summary"] = "未检测到专家激活信息"

    return info

def reset_expert_tracking():
    """重置专家追踪状态"""
    global expert_activations, hook_call_count
    expert_activations = []
    hook_call_count = 0

# ========== 模型加载函数 ==========
def load_model():
    global model, tokenizer
    
    print("正在加载模型...")
    # 加载分词器
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_PATH, trust_remote_code=True
    )

    # 加载语言模型
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    # 加载并设置生成配置
    model.generation_config = GenerationConfig.from_pretrained(MODEL_PATH)
    model.generation_config.pad_token_id = model.generation_config.eos_token_id
    model.eval()

    print("模型加载完成!")

    # 设置专家追踪hooks
    hooks_setup = setup_expert_hooks(model)
    if hooks_setup:
        print("✅ 专家追踪功能已启用")
    else:
        print("⚠️ 未找到MoE相关层，专家追踪可能无法正常工作")

# ========== 推理函数 ==========
def chat_generate(prompt_text, temperature=0.7, max_tokens=100, stream=False) -> Union[str, Generator]:
    """生成聊天回复"""
    if stream:
        def token_stream():
            # 构建输入
            messages = [{"role": "user", "content": prompt_text}]
            input_tensor = tokenizer.apply_chat_template(
                messages, add_generation_prompt=True, return_tensors="pt"
            )
            
            # 生成响应ID
            response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
            created_time = int(time.time())
            
            # 流式生成
            with torch.no_grad():
                # 这里需要实现真正的流式生成
                # 由于transformers的generate方法不直接支持流式，我们先生成完整结果然后模拟流式
                generated = model.generate(
                    input_tensor.to(model.device),
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True,
                    pad_token_id=tokenizer.pad_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    use_cache=True
                )
            
            new_tokens = generated[:, input_tensor.shape[1]:]
            result = tokenizer.decode(new_tokens[0], skip_special_tokens=True)
            
            # 将结果分成单词进行流式输出
            words = result.split()
            
            for i, word in enumerate(words):
                chunk_data = {
                    "id": response_id,
                    "object": "chat.completion.chunk",
                    "created": created_time,
                    "model": "deepseek-moe-16b-chat",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {
                                "content": word + " "
                            },
                            "finish_reason": None
                        }
                    ]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                time.sleep(0.05)  # 模拟流式延迟
            
            # 发送结束标记
            final_chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": "deepseek-moe-16b-chat",
                "choices": [
                    {
                        "index": 0,
                        "delta": {},
                        "finish_reason": "stop"
                    }
                ]
            }
            yield f"data: {json.dumps(final_chunk)}\n\n"
            yield "data: [DONE]\n\n"
        
        return token_stream()
        
    # 非流式生成
    messages = [{"role": "user", "content": prompt_text}]
    input_tensor = tokenizer.apply_chat_template(
        messages, add_generation_prompt=True, return_tensors="pt"
    )
    
    with torch.no_grad():
        outputs = model.generate(
            input_tensor.to(model.device),
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
            use_cache=True
        )
    
    result = tokenizer.decode(
        outputs[0][input_tensor.shape[1]:], skip_special_tokens=True
    )
    return result

# ========== 启动事件 ==========
@app.on_event("startup")
def startup_event():
    load_model()

# ========== API端点 ==========

# 1. OpenAI标准API
@app.post("/v1/chat/completions")
def chat_completions(req: ChatRequest):
    reset_expert_tracking()
    
    # 构建对话文本
    messages = [m.dict() for m in req.messages]
    if len(messages) > 0:
        prompt = messages[-1]["content"]  # 简化处理，取最后一条消息
    else:
        prompt = ""
    
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

# 2. 兼容原有API格式
@app.post("/")
async def legacy_endpoint(request: Request):
    """保持与原api6(3).py兼容的端点"""
    try:
        json_post_raw = await request.json()
        json_post = json.dumps(json_post_raw)
        json_post_list = json.loads(json_post)
        prompt = json_post_list.get("prompt")
        max_length = json_post_list.get("max_length", 512)

        # 重置专家追踪状态
        reset_expert_tracking()

        # 生成回复
        result = chat_generate(prompt, max_tokens=max_length)

        now = datetime.datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 构建响应JSON
        answer = {
            "response": result,
            "status": 200,
            "time": time_str,
            "expert_info": get_expert_info()  # 添加专家信息
        }

        # 构建日志信息
        log = (
            "["
            + time_str
            + "] "
            + 'prompt:"'
            + prompt
            + '", response:"'
            + repr(result)
            + '"'
        )
        print(log)
        torch_gc()

        return answer

    except Exception as e:
        print(f"处理请求时发生错误: {e}")
        now = datetime.datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "response": f"处理请求时发生错误: {str(e)}",
            "status": 500,
            "time": time_str,
        }

# 3. 健康检查
@app.get("/health")
def health():
    return {
        "status": "ok",
        "device": CUDA_DEVICE,
        "torch_version": torch.__version__,
        "model_loaded": model is not None,
        "hooks_registered": len(hooks)
    }

# 4. 专家信息查询
@app.get("/expert/info")
def get_expert_statistics():
    return get_expert_info(max_records=10)

# 5. 模型结构诊断
@app.get("/debug/model_structure")
def get_model_structure():
    if model is None:
        return {"error": "模型未加载"}
    
    total_modules = 0
    moe_related = []
    
    for name, module in model.named_modules():
        total_modules += 1
        if any(k in name.lower() for k in ['moe', 'expert', 'gate', 'router']):
            moe_related.append({
                "name": name,
                "type": type(module).__name__
            })
    
    return {
        "total_modules": total_modules,
        "moe_related_count": len(moe_related),
        "moe_modules": moe_related[:20],  # 只返回前20个
        "hooks_registered": len(hooks)
    }

# 6. 获取模型信息
@app.get("/v1/models")
async def list_models():
    """列出所有可用模型（兼容OpenAI API格式）"""
    return {
        "object": "list",
        "data": [
            {
                "id": "deepseek-moe-16b",
                "object": "model",
                "created": 1751604676,
                "owned_by": "vllm",
                "root": "models/deepseek-moe-16b",
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

    # 命令行参数解析
    parser = argparse.ArgumentParser(description="启动 DeepSeek MoE API Server")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    parser.add_argument("--port", type=int, default=6006, help="设置运行端口，默认为6006")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="设置绑定地址，默认为0.0.0.0")
    args = parser.parse_args()

    DEBUG_MODE = args.debug
    port = args.port
    host = args.host

    print("🚀 启动 DeepSeek MoE API Server")
    print(f"📍 地址: http://{host}:{port}")
    print(f"🔧 调试模式: {'开启' if DEBUG_MODE else '关闭'}")
    print(f"📊 支持端点:")
    print(f"   - POST /v1/chat/completions (OpenAI标准)")
    print(f"   - POST / (兼容原API)")
    print(f"   - GET /health (健康检查)")
    print(f"   - GET /expert/info (专家信息)")
    print(f"   - GET /debug/model_structure (模型结构)")

    uvicorn.run("moe_server:app", host=host, port=port, workers=1, reload=False)

if __name__ == "__main__":
    main()