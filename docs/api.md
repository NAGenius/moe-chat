# MoE-Chat API 文档

## 基础说明

### 请求 URL 格式
所有 API 请求的 URL 格式为：`/api/v1/{endpoint}`

### 响应格式
API响应遵循以下格式规则：

1. 成功响应（无数据返回）:
```json
{
  "code": 200,   // 状态码
  "message": "请求成功"  // 描述信息
}
```

2. 成功响应（有数据返回）:
```json
{
  "code": 200,   // 状态码
  "message": "请求成功",  // 描述信息
  "data": { ... }  // 实际数据
}
```

3. 错误响应:
```json
{
  "code": 400,   // 错误状态码
  "message": "错误描述"  // 错误信息
}
```

### 状态码说明
- 200: 请求成功
- 400: 请求参数错误
- 401: 未授权
- 403: 禁止访问
- 404: 资源不存在
- 409: 资源冲突
- 500: 服务器内部错误

## 认证 API

### 发送验证码
**POST** `/api/v1/auth/send-verification-code`

向指定邮箱发送验证码，用于邮箱验证。

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| email | string | 是 | 邮箱地址 |

**请求示例**
```json
{
  "email": "user@example.com"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功"
}
```

**错误响应**

- 发送频率限制:
```json
{
  "code": 400,
  "message": "请求过于频繁，请稍后再试"
}
```

### 用户注册
**POST** `/api/v1/auth/register`

使用邮箱验证码注册新用户，并自动登录，返回用户信息和访问令牌。

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| email | string | 是 | 邮箱地址 |
| username | string | 是 | 用户名（3-50个字符，仅允许字母、数字和下划线） |
| password | string | 是 | 密码（至少6个字符） |
| verification_code | string | 是 | 邮箱验证码（6位数字） |
| full_name | string | 是 | 用户全名/展示名称 |

**请求示例**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "verification_code": "123456",
  "full_name": "张三"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**错误响应**

- 验证码无效或过期:
```json
{
  "code": 400,
  "message": "验证码无效或已过期"
}
```

- 用户名或邮箱已存在:
```json
{
  "code": 409,
  "message": "用户名或邮箱已被使用"
}
```

- 参数验证失败:
```json
{
  "code": 400,
  "message": "请求参数错误"
}
```

### 用户登录
**POST** `/api/v1/auth/login`

使用邮箱和密码登录，返回用户信息和访问令牌。

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| email | string | 是 | 邮箱地址 |
| password | string | 是 | 密码 |

**请求示例**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**错误响应**

- 登录失败:
```json
{
  "code": 401,
  "message": "邮箱或密码错误"
}
```

### 刷新令牌
**POST** `/api/v1/auth/refresh`

使用刷新令牌获取新的访问令牌。

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| refresh_token | string | 是 | 刷新令牌 |

**请求示例**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer"
  }
}
```

**错误响应**

- 令牌无效:
```json
{
  "code": 401,
  "message": "无效的刷新令牌"
}
```

## 用户 API

### 获取当前用户信息
**GET** `/api/v1/user/me`

获取当前登录用户的详细信息。

**请求头**
```
Authorization: Bearer {access_token}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "username": "username",
    "email": "user@example.com",
    "full_name": "张三",
    "role": "user",
    "system_prompt": "你是一个有用的助手"
  }
}
```

**错误响应**

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 更新用户信息
**PUT** `/api/v1/user/me`

更新当前用户的信息。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| username | string | 否 | 用户名（3-50个字符，仅允许字母、数字和下划线） |
| full_name | string | 否 | 用户全名/显示名称 |
| system_prompt | string | 否 | 系统提示词 |

**请求示例**
```json
{
  "username": "sky",
  "full_name": "新名字",
  "system_prompt": "你是一个专业的程序员助手"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功"
}
```

**错误响应**

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

- 用户名已存在:
```json
{
  "code": 409,
  "message": "用户名已被使用"
}
```

- 参数验证失败:
```json
{
  "code": 400,
  "message": "用户名只能包含字母、数字和下划线"
}
```

- 内部错误:
```json
{
  "code": 500,
  "message": "更新用户信息失败"
}
```

### 更新用户密码
**PUT** `/api/v1/user/me/password`

更新当前用户的密码，需要邮箱验证码验证。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| new_password | string | 是 | 新密码（至少6个字符） |
| verification_code | string | 是 | 邮箱验证码（6位数字） |

**请求示例**
```json
{
  "new_password": "newpassword123",
  "verification_code": "123456"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功"
}
```

**错误响应**

- 验证码无效:
```json
{
  "code": 400,
  "message": "验证码无效或已过期"
}
```

- 密码格式无效:
```json
{
  "code": 422,
  "message": "新密码长度必须至少为6个字符"
}
```

- 验证码格式无效:
```json
{
  "code": 422,
  "message": "验证码必须为6位数字"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

- 内部错误:
```json
{
  "code": 500,
  "message": "更新密码失败"
}
```

## 模型 API

### 获取模型列表
**GET** `/api/v1/model`

获取所有可用的模型列表。

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "models": [
      {
        "id": "Mistral-7B-v0.1",
        "display_name": "Mistral-7B",
        "description": "Mistral AI的7B参数大语言模型",
        "is_active": true,
        "has_thinking": true,
        "max_context_tokens": 32768
      },
      {
        "id": "Llama-2-13b-chat-hf",
        "display_name": "Llama-2-13b",
        "description": "Meta的Llama 2聊天模型",
        "is_active": true,
        "has_thinking": true,
        "max_context_tokens": 4096
      }
    ]
  }
}
```

**注意**: 不需要认证令牌即可访问此接口。

## 聊天会话 API

### 流式生成模式说明

本系统支持两种消息生成模式：

1. **流式生成模式**：实时返回生成内容，用户可以看到逐字生成的过程
   - 使用 `/api/v1/chat/{chat_id}/messages/stream` 接口
   - 返回 SSE (Server-Sent Events) 格式的流式数据
   - 适合需要实时反馈的场景

2. **非流式生成模式**：等待完整生成后一次性返回结果
   - 使用 `/api/v1/chat/{chat_id}/messages` 接口
   - 返回完整的 JSON 响应
   - 适合需要完整结果的场景

用户可以在聊天界面中通过"流式生成"开关来选择使用哪种模式。

### 创建聊天会话
**POST** `/api/v1/chat`

创建一个新的聊天会话。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| title | string | 是 | 会话标题 |

**请求示例**
```json
{
  "title": "新的会话"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "chat_id": "uuid字符串"
  }
}
```

**错误响应**

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 获取聊天会话列表
**GET** `/api/v1/chat`

获取当前用户的所有聊天会话列表。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| page | integer | 否 | 分页页码，默认为1 |
| limit | integer | 否 | 每页数量，默认为20，最大100 |

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "chats": [
      {
        "id": "uuid字符串1",
        "title": "会话标题1",
        "updated_at": "2023-01-01T14:30:00Z"
      },
      {
        "id": "uuid字符串2",
        "title": "会话标题2",
        "updated_at": "2023-01-02T11:20:00Z"
      }
    ],
    "total": 5,
    "page": 1,
    "limit": 20
  }
}
```

**错误响应**

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 获取聊天会话详情
**GET** `/api/v1/chat/{chat_id}`

获取指定聊天会话的详细信息。

**请求头**
```
Authorization: Bearer {access_token}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "id": "uuid字符串",
    "title": "会话标题"
  }
}
```

**错误响应**

- 会话不存在:
```json
{
  "code": 404,
  "message": "聊天会话不存在"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 更新聊天会话
**PUT** `/api/v1/chat/{chat_id}`

更新指定聊天会话的信息。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| title | string | 是 | 会话标题 |

**请求示例**
```json
{
  "title": "修改后的标题"
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功"
}
```

**错误响应**

- 会话不存在:
```json
{
  "code": 404,
  "message": "聊天会话不存在"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 删除聊天会话
**DELETE** `/api/v1/chat/{chat_id}`

删除指定的聊天会话。

**请求头**
```
Authorization: Bearer {access_token}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功"
}
```

**错误响应**

- 会话不存在:
```json
{
  "code": 404,
  "message": "聊天会话不存在"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

## 消息 API

### 获取聊天消息
**GET** `/api/v1/chat/{chat_id}/messages`

获取指定聊天会话的消息列表。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| page | integer | 否 | 分页页码，默认为1 |
| limit | integer | 否 | 每页数量，默认为50，最大100 |

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "messages": [
      {
        "id": "uuid字符串1",
        "role": "user",
        "content": "你好！",
        "status": "completed",
        "model_id": null,
        "position": 1,
        "created_at": "2023-01-01T12:01:00Z"
      },
      {
        "id": "uuid字符串2",
        "role": "assistant",
        "content": "你好！我能帮你什么忙吗？",
        "status": "completed",
        "model_id": "mistralai/Mistral-7B-v0.1",
        "position": 2,
        "created_at": "2023-01-01T12:01:05Z"
      }
    ],
    "total": 2,
    "page": 1,
    "limit": 50
  }
}
```

**错误响应**

- 会话不存在:
```json
{
  "code": 404,
  "message": "聊天会话不存在"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 发送消息（非流式）
**POST** `/api/v1/chat/{chat_id}/messages`

在指定聊天会话中发送新消息，并等待模型完整响应后返回。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| content | string | 是 | 消息内容 |
| model_id | string | 是 | 使用的模型ID |
| file_ids | array | 否 | 附件文件ID数组 |

**请求示例**
```json
{
  "content": "我需要帮助解决一个问题",
  "model_id": "mistralai/Mistral-7B-v0.1",
  "file_ids": ["uuid文件1", "uuid文件2"]
}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "content": "这是模型生成的完整回复内容"
  }
}
```

**错误响应**

- 会话不存在:
```json
{
  "code": 404,
  "message": "聊天会话不存在"
}
```

- 模型不可用:
```json
{
  "code": 400,
  "message": "请求的模型当前不可用"
}
```

- 模型不存在:
```json
{
  "code": 404,
  "message": "请求的模型不存在或不可用"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 流式消息响应
**POST** `/api/v1/chat/{chat_id}/messages/stream`

在指定聊天会话中发送新消息并以SSE格式流式返回模型响应，格式与OpenAI API兼容。

**请求头**
```
Authorization: Bearer {access_token}
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| content | string | 是 | 消息内容 |
| model_id | string | 是 | 使用的模型ID |
| file_ids | array | 否 | 附件文件ID数组 |

**请求示例**
```json
{
  "content": "我需要帮助解决一个问题",
  "model_id": "mistralai/Mistral-7B-v0.1",
  "file_ids": ["uuid文件1", "uuid文件2"]
}
```

**响应格式**
响应为Server-Sent Events (SSE)格式，兼容OpenAI流式API格式，包含以下事件:

1. 开始生成响应:
```
data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1706195805,"model":"mistralai/Mistral-7B-v0.1","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}
```

2. 内容增量:
```
data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1706195805,"model":"mistralai/Mistral-7B-v0.1","choices":[{"index":0,"delta":{"content":"文本"},"finish_reason":null}]}
```

3. 生成完成:
```
data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1706195805,"model":"mistralai/Mistral-7B-v0.1","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}
data: [DONE]
```

4. 错误响应:
```
data: {"id":"chatcmpl-123abc","object":"chat.completion.chunk","created":1706195805,"model":"mistralai/Mistral-7B-v0.1","choices":[{"index":0,"delta":{"content":"错误: 模型生成失败"},"finish_reason":"error"}],"error":{"message":"模型生成失败","type":"generation_failed","code":500}}
data: [DONE]
```

**错误响应**

- 会话不存在:
```json
{
  "code": 404,
  "message": "聊天会话不存在"
}
```

- 模型不可用:
```json
{
  "code": 400,
  "message": "请求的模型当前不可用"
}
```

- 模型不存在:
```json
{
  "code": 404,
  "message": "请求的模型不存在或不可用"
}
```

## 文件 API

### 上传文件
**POST** `/api/v1/file`

上传文件用于聊天。

**请求头**
```
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**请求参数**

| 参数名 | 类型 | 必需 | 描述 |
| ------ | ---- | ---- | ---- |
| file | file | 是 | 要上传的文件（≤2MB） |

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "file_id": "uuid字符串",
    "filename": "example.pdf",
    "file_type": "application/pdf"
  }
}
```

**错误响应**

- 文件过大:
```json
{
  "code": 400,
  "message": "文件大小超过限制 (2097153 > 2097152)"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 获取文件信息
**GET** `/api/v1/file/{file_id}`

获取已上传文件的信息。

**请求头**
```
Authorization: Bearer {access_token}
```

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "file_id": "uuid字符串",
    "filename": "example.pdf",
    "file_type": "application/pdf",
    "download_url": "/api/v1/file/uuid字符串/download",
    "file_size": 1048576
  }
}
```

**错误响应**

- 文件不存在:
```json
{
  "code": 404,
  "message": "文件不存在"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

### 下载文件
**GET** `/api/v1/file/{file_id}/download`

下载已上传的文件。

**请求头**
```
Authorization: Bearer {access_token}
```

**响应**

二进制文件内容，同时返回以下响应头：
```
Content-Type: {文件的MIME类型}
Content-Disposition: attachment; filename={文件名}
```

**错误响应**

- 文件不存在:
```json
{
  "code": 404,
  "message": "文件不存在"
}
```

- 未授权:
```json
{
  "code": 401,
  "message": "未授权访问"
}
```

## 健康检查 API

### 服务健康状态
**GET** `/api/v1/health`

检查服务的健康状态，包括数据库和Redis连接。

**成功响应**
```json
{
  "code": 200,
  "message": "请求成功",
  "data": {
    "status": "正常",
    "database": "正常",
    "redis": "正常",
    "version": "0.1.0"
  }
}
```

**错误响应**
```json
{
  "code": 503,
  "message": "请求成功",
  "data": {
    "status": "异常",
    "database": "正常",
    "redis": "异常",
    "version": "0.1.0"
  }
}
```

HTTP状态码将在服务异常时返回503，但响应体依然按照标准格式返回。