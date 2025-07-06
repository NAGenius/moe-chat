# MoE-Chat 数据库设计文档

本文档描述了MoE-Chat项目的数据库设计，包括表结构、关系和字段定义，同时提供了基于项目需求的优化建议。

## 当前数据库结构

MoE-Chat使用PostgreSQL作为主数据库，Redis作为缓存和消息队列。数据库采用SQLModel（基于SQLAlchemy和Pydantic）进行ORM映射。

### 数据表设计

目前数据库包含以下主要表：

#### 1. users表

存储用户信息，包括认证和权限数据。

| 字段名 | 类型 | 约束 | 描述 |
| ----- | ---- | ---- | ---- |
| id | UUID | 主键 | 用户唯一标识 |
| username | VARCHAR | 唯一，索引 | 用户名 |
| email | VARCHAR | 唯一，索引 | 电子邮箱 |
| hashed_password | VARCHAR | 非空 | 加密后的密码 |
| full_name | VARCHAR | 可空或者默认名字 | 用户全名、展示名字 |
| is_active | BOOLEAN | 默认TRUE | 是否活跃、禁用的操作、软删除 |
| role | ENUM | 非空 | 用户角色：admin, user |
| system_prompt | TEXT | 可空，默认"你是一个有用的助手" | 与大模型对话的系统提示词 |
| created_at | TIMESTAMP | 非空 | 账户创建时间 |
| updated_at | TIMESTAMP | 非空 | 账户更新时间 |
| last_login_at | TIMESTAMP | 可空 | 最后登录时间 |

#### 2. models表

存储模型配置信息。应该从vllm模型服务端获取相应内容

| 字段名 | 类型 | 约束 | 描述 |
| ----- | ---- | ---- | ---- |
| id | VARCHAR | 主键 | 模型配置唯一标识，例如mistralai/Mistral-7B-v0.1，供应商/模型名 |
| display_name | VARCHAR | 非空 | 显示名称，默认和模型名一致 |
| description | TEXT | 可空 | 模型描述 |
| is_active | BOOLEAN | 默认TRUE | 是否可用 |
| max_context_tokens | INTEGER | 默认4096 | 最大上下文长度 |
| has_thinking | BOOLEAN | 默认FALSE | 是否支持思考过程 |
| default_params | JSON | 可空 | 默认参数，如温度这些 |
| service_url | VARCHAR | 可空 | 模型服务URL，为空则使用默认URL |
| created_at | TIMESTAMP | 非空 | 创建时间 |
| updated_at | TIMESTAMP | 非空 | 更新时间 |

#### 3. chats表

存储用户的聊天会话信息。

| 字段名 | 类型 | 约束 | 描述 |
| ----- | ---- | ---- | ---- |
| id | UUID | 主键 | 会话唯一标识 |
| user_id | UUID | 外键 | 关联用户ID |
| title | VARCHAR | 非空 | 会话标题 |
| created_at | TIMESTAMP | 非空 | 创建时间 |
| updated_at | TIMESTAMP | 非空 | 更新时间 |

#### 4. messages表

存储聊天消息内容。

| 字段名 | 类型 | 约束 | 描述 |
| ----- | ---- | ---- | ---- |
| id | UUID | 主键 | 消息唯一标识 |
| chat_id | UUID | 外键 | 关联的聊天会话ID |
| role | ENUM | 非空 | 角色：system, user, assistant |
| content | TEXT | 非空 | 消息内容 |
| status | ENUM | 非空 | 状态：completed, error, pending |
| position | INTEGER | 非空，默认0 | 消息在对话中的位置序号 |
| model_id | VARCHAR | 外键，可空 | 使用的模型ID |
| created_at | TIMESTAMP | 非空 | 创建时间 |
| updated_at | TIMESTAMP | 非空 | 更新时间 |

#### 5. files表

存储用户上传的文件信息：

| 字段名 | 类型 | 约束 | 描述 |
| ----- | ---- | ---- | ---- |
| id | UUID | 主键 | 文件唯一标识 |
| user_id | UUID | 外键 | 用户ID |
| filename | VARCHAR | 非空 | 文件名 |
| file_path | VARCHAR | 非空 | 存储路径 |
| file_type | VARCHAR | 非空 | 文件类型 |
| file_size | INTEGER | 非空 | 文件大小 |
| created_at | TIMESTAMP | 非空 | 上传时间 |
| message_id | UUID | 外键，可空 | 关联消息ID |

### 表关系

1. **用户-聊天会话**：一对多关系，一个用户可拥有多个聊天会话
2. **聊天会话-消息**：一对多关系，一个会话包含多条消息
3. **用户-文件**：一对多关系，一个用户可以上传多个文件
4. **消息-文件**：一对多关系，一条消息可以包含多个文件
5. **模型-消息**：一对多关系，一个模型可以关联多条消息