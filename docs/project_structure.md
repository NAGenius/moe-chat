# MoE-Chat 项目结构文档

## 项目概览

```
MoE-Chat/
├── frontend/                    # 前端项目 (Next.js)
├── backend/                     # 后端项目 (FastAPI)
├── docs/                        # 项目文档
├── docker-compose.yml           # Docker编排配置
├── init.sql                     # 数据库初始化脚本
├── show_moe.py                  # MoE可视化核心模块
├── moe_visualizer_service.py    # MoE可视化服务
├── vllm-monitoring/             # vLLM监控相关
├── uploads/                     # 文件上传目录
├── logs/                        # 日志文件目录
├── .gitignore                   # Git忽略文件配置
└── README.md                    # 项目说明
```

## 前端项目结构

```
frontend/
├── src/
│   ├── app/                     # Next.js App Router 页面
│   │   ├── chat/               # 聊天页面
│   │   │   └── page.tsx
│   │   ├── login/              # 登录页面
│   │   │   └── page.tsx
│   │   ├── register/           # 注册页面
│   │   │   └── page.tsx
│   │   ├── layout.tsx          # 根布局组件
│   │   ├── page.tsx            # 首页
│   │   └── globals.css         # 全局样式
│   ├── components/             # React 组件
│   │   ├── chat/              # 聊天相关组件
│   │   │   ├── chat-interface.tsx    # 聊天界面主组件
│   │   │   ├── chat-sidebar.tsx      # 聊天侧边栏
│   │   │   ├── message-item.tsx      # 消息项组件
│   │   │   ├── message-list.tsx      # 消息列表
│   │   │   ├── model-selector.tsx    # 模型选择器
│   │   │   └── welcome-screen.tsx    # 欢迎屏幕
│   │   ├── providers/         # 上下文提供者
│   │   │   ├── auth-provider.tsx     # 认证提供者
│   │   │   ├── query-provider.tsx    # 查询提供者
│   │   │   └── theme-provider.tsx    # 主题提供者
│   │   └── ui/                # UI 基础组件 (shadcn/ui)
│   │       ├── button.tsx
│   │       ├── input.tsx
│   │       ├── textarea.tsx
│   │       ├── dialog.tsx
│   │       ├── dropdown-menu.tsx
│   │       ├── toast.tsx
│   │       └── ...
│   ├── hooks/                 # 自定义 Hooks
│   │   ├── use-toast.ts
│   │   └── ...
│   ├── lib/                   # 工具函数
│   │   ├── utils.ts
│   │   └── ...
│   ├── services/              # API 服务
│   │   ├── auth.ts           # 认证服务
│   │   ├── chat.ts           # 聊天服务
│   │   ├── file.ts           # 文件服务
│   │   ├── user.ts           # 用户服务
│   │   └── model.ts          # 模型服务
│   ├── store/                # 状态管理 (Zustand)
│   │   ├── auth.ts           # 认证状态
│   │   └── chat.ts           # 聊天状态
│   └── utils/                # 工具函数
├── public/                   # 静态资源
├── .env.local               # 本地环境变量（不提交到版本控制）
├── .env.example             # 环境变量示例文件
├── package.json             # 依赖配置
├── next.config.js           # Next.js 配置
├── tailwind.config.js       # Tailwind CSS 配置
├── tsconfig.json            # TypeScript 配置
├── .eslintrc.json          # ESLint 配置
├── .prettierrc             # Prettier 配置
└── README.md               # 前端说明文档
```

## 后端项目结构

```
backend/
├── app/                        # 应用核心代码
│   ├── api/                   # API 路由层
│   │   └── v1/               # API v1 版本
│   │       ├── endpoints/    # API 端点
│   │       │   ├── auth.py          # 认证相关API
│   │       │   ├── chats.py         # 聊天相关API
│   │       │   ├── files.py         # 文件相关API
│   │       │   ├── health.py        # 健康检查API
│   │       │   ├── models.py        # 模型相关API
│   │       │   └── users.py         # 用户相关API
│   │       └── router.py     # 路由注册
│   ├── core/                 # 核心功能
│   │   ├── celery_app.py     # Celery 应用配置
│   │   └── ...
│   ├── db/                   # 数据库相关
│   │   ├── models/           # 数据库模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py              # 用户模型
│   │   │   ├── chat.py              # 聊天模型
│   │   │   ├── message.py           # 消息模型
│   │   │   ├── model.py             # 模型信息模型
│   │   │   └── file.py              # 文件模型
│   │   ├── repositories/     # 数据访问层
│   │   │   ├── base.py              # 基础仓库
│   │   │   ├── user.py              # 用户仓库
│   │   │   ├── chat.py              # 聊天仓库
│   │   │   ├── message.py           # 消息仓库
│   │   │   ├── model.py             # 模型仓库
│   │   │   └── file.py              # 文件仓库
│   │   ├── schemas/          # 数据传输对象
│   │   │   ├── api/                 # API 模式
│   │   │   │   ├── request/         # 请求模式
│   │   │   │   └── response/        # 响应模式
│   │   │   └── dto/                 # 数据传输对象
│   │   └── database.py       # 数据库连接配置
│   ├── middleware/           # 中间件
│   │   ├── cors.py           # CORS 中间件
│   │   ├── errors.py         # 错误处理中间件
│   │   ├── logging.py        # 日志中间件
│   │   └── rate_limit.py     # 限流中间件
│   ├── services/             # 业务逻辑层
│   │   ├── auth_service.py   # 认证服务
│   │   ├── chat_service.py   # 聊天服务
│   │   ├── file_service.py   # 文件服务
│   │   ├── model_service.py  # 模型服务
│   │   └── user_service.py   # 用户服务
│   ├── tasks/                # 异步任务
│   │   ├── file_tasks.py     # 文件清理任务
│   │   └── ...
│   ├── templates/            # 邮件模板
│   ├── utils/                # 工具函数
│   │   ├── auth.py           # 认证工具
│   │   ├── email.py          # 邮件工具
│   │   ├── exceptions.py     # 异常定义
│   │   ├── logger.py         # 日志工具
│   │   └── redis_client.py   # Redis 客户端
│   ├── config.py             # 应用配置
│   └── main.py               # 应用入口
├── alembic/                  # 数据库迁移
│   ├── versions/             # 迁移版本
│   ├── env.py               # 迁移环境配置
│   └── script.py.mako       # 迁移脚本模板
├── logs/                     # 日志文件
├── uploads/                  # 上传文件存储
├── .env                      # 环境变量配置（敏感信息，不提交到版本控制）
├── .env.example             # 环境变量示例文件
├── alembic.ini              # Alembic 配置
├── celery_worker.py         # Celery 工作进程
├── pyproject.toml           # Python 项目配置（Poetry）
├── requirements.txt         # Python 依赖列表
└── README.md                # 后端说明文档
```

## 文档结构

```
docs/
├── api.md                   # API 接口文档
├── database_design.md       # 数据库设计文档
├── frontend.md              # 前端开发文档
├── presentation_guide.md    # 演示指南文档
├── presentation_slides.md   # 演示幻灯片文档
├── project.md               # 项目总体文档
├── project_structure.md     # 项目结构文档 (本文档)
├── tech_stack.md            # 技术栈文档
└── vllm.md                  # vLLM 部署文档
```

## MoE可视化模块

### 核心文件

- **`show_moe.py`** - MoE专家激活可视化核心模块
  - `MoEExpertVisualizer` 类：可视化器主类
  - `MoEInterface` 类：外部调用接口
  - 实时热力图显示
  - 专家激活统计

- **`moe_visualizer_service.py`** - 独立可视化服务
  - Redis 消息订阅
  - 实时数据更新
  - 可视化界面管理

### 集成点

- **后端集成**：
  - `backend/app/api/v1/endpoints/chats.py` - 非流式消息处理
  - `backend/app/services/model_service.py` - 专家数据发布

## 配置文件说明

### 前端配置

- **`package.json`** - 依赖管理和脚本配置
- **`next.config.js`** - Next.js 框架配置
- **`tailwind.config.js`** - Tailwind CSS 样式配置
- **`tsconfig.json`** - TypeScript 编译配置
- **`.eslintrc.json`** - 代码质量检查配置
- **`.prettierrc`** - 代码格式化配置
- **`.env.local`** - 本地环境变量（不提交到版本控制）
- **`.env.example`** - 环境变量示例文件

### 后端配置

- **`pyproject.toml`** - Python 项目和依赖配置（Poetry）
- **`requirements.txt`** - Python 依赖列表
- **`.env`** - 环境变量配置（敏感信息，不提交到版本控制）
- **`.env.example`** - 环境变量示例文件
- **`alembic.ini`** - 数据库迁移配置

### 部署配置

- **`docker-compose.yml`** - 多容器编排配置
- **`init.sql`** - 数据库初始化脚本

## 数据流向

### 用户认证流程
```
前端登录页面 → 后端认证API → 数据库验证 → JWT令牌 → 前端状态管理
```

### 聊天对话流程
```
前端聊天界面 → 后端聊天API → vLLM模型服务 → 流式响应 → 前端实时显示
```

### MoE可视化流程
```
vLLM模型响应 → 后端专家数据提取 → Redis发布 → 可视化服务订阅 → 实时图表更新
```

## 开发规范

### 前端规范
- 使用 TypeScript 进行类型安全开发
- 遵循 ESLint + Prettier 代码规范
- 组件采用函数式组件 + Hooks
- 状态管理使用 Zustand
- 样式使用 Tailwind CSS

### 后端规范
- 遵循 Python PEP 8 代码规范
- 使用 black + isort 进行代码格式化
- 采用分层架构设计
- 异步编程优先
- 完整的类型注解

### 数据库规范
- 使用 UUID 作为主键
- 统一的时间戳字段（created_at, updated_at）
- 适当的索引设计
- 外键约束和级联删除
- 数据迁移版本控制

## 部署架构

### 开发环境
```
Docker Compose:
├── PostgreSQL (端口 5432)
├── Redis (端口 6379)
├── 后端服务 (端口 8000)
├── 前端服务 (端口 3000)
└── MoE可视化服务 (独立进程)
```

### 生产环境建议
```
负载均衡器 → 前端静态资源 (CDN)
            ↓
         后端API集群
            ↓
    数据库主从 + Redis集群
            ↓
        vLLM模型服务集群
```