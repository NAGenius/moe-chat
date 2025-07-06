# vLLM 服务集成说明

## vLLM服务API

vLLM服务提供OpenAI兼容的API，主要用于项目中的聊天生成功能：

```
INFO 06-30 01:33:45 [launcher.py:28] Available routes are:
INFO 06-30 01:33:45 [launcher.py:36] Route: /openapi.json, Methods: GET, HEAD
INFO 06-30 01:33:45 [launcher.py:36] Route: /docs, Methods: GET, HEAD
INFO 06-30 01:33:45 [launcher.py:36] Route: /docs/oauth2-redirect, Methods: GET, HEAD
INFO 06-30 01:33:45 [launcher.py:36] Route: /redoc, Methods: GET, HEAD
INFO 06-30 01:33:45 [launcher.py:36] Route: /health, Methods: GET
INFO 06-30 01:33:45 [launcher.py:36] Route: /load, Methods: GET
INFO 06-30 01:33:45 [launcher.py:36] Route: /ping, Methods: GET, POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /tokenize, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /detokenize, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/models, Methods: GET
INFO 06-30 01:33:45 [launcher.py:36] Route: /version, Methods: GET
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/chat/completions, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/completions, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/embeddings, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /pooling, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /score, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/score, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/audio/transcriptions, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /rerank, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v1/rerank, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /v2/rerank, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /invocations, Methods: POST
INFO 06-30 01:33:45 [launcher.py:36] Route: /metrics, Methods: GET
```

## 流式响应格式

vLLM的流式响应采用SSE (Server-Sent Events) 格式，每一块增量内容如下：

```json
{
    "id": "chatcmpl-0e9f43a01be04a7e8b0ab7f1eadad022",
    "object": "chat.completion.chunk",
    "created": 1751479516,
    "model": "DeepSeek-R1-Distill-Qwen-1.5B",
    "choices": [
        {
            "index": 0,
            "delta": {
                "content": " the"
            },
            "logprobs": null,
            "finish_reason": null
        }
    ]
}
```

## 思考模型格式

如果模型为思考模型 (has_thinking = true)，vLLM 返回的响应会包含思考过程：

```json
{
    "id": "chatcmpl-a46f3eef709347b086bbdba6f57ba42d",
    "object": "chat.completion",
    "created": 1751481743,
    "model": "DeepSeek-R1-Distill-Qwen-1.5B",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "reasoning_content": null,
                "content": "Alright, someone just asked me how I'm doing. I need to respond appropriately. I should let them know I'm fine and ask them how they're doing. Keeping it friendly and open-ended should work best.\n</think>\n\nI'm just a program, so I don't have feelings, but thanks for asking! How can I assist you today?",
                "tool_calls": []
            },
            "logprobs": null,
            "finish_reason": "stop",
            "stop_reason": null
        }
    ],
    "usage": {
        "prompt_tokens": 11,
        "total_tokens": 82,
        "completion_tokens": 71,
        "prompt_tokens_details": null
    },
    "prompt_logprobs": null
}
```

思考部分和正文通过`</think>`标记分隔。

## SSE流式生成实现

MoE-Chat的SSE流式输出与vLLM集成流程如下：

1. **客户端发送请求**：客户端向`/api/v1/chat/{chat_id}/messages/stream`发送POST请求，包含消息内容和模型ID
   ```json
   {
     "content": "请介绍量子计算",
     "model_id": "mistralai/Mistral-7B-v0.1",
     "file_ids": []
   }
   ```