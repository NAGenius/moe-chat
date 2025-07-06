# MoE-Chat 技术栈文档

## 前端技术栈

### 核心框架
- **Next.js 14** (App Router) - React全栈框架，支持SSR/SSG
- **TypeScript 5+** - 类型安全的JavaScript超集
- **React 18** - 现代化UI框架，支持并发特性

### UI组件库 & 样式
- **shadcn/ui** - 基于Radix UI的现代化组件库
- **Radix UI** - 无样式、可访问的组件基础
- **Tailwind CSS 3+** - 原子化CSS框架
- **Lucide React** - 现代化图标库
- **Framer Motion** - 高性能动画库
- **next-themes** - 主题切换支持
- **tailwindcss-animate** - Tailwind动画扩展

### 状态管理 & 数据获取
- **Zustand 4+** - 轻量级状态管理库
- **TanStack Query (React Query) 5+** - 强大的服务端状态管理
- **Socket.io-client 4+** - 实时WebSocket通信
- **Axios** - HTTP客户端库

### 表单处理 & 验证
- **React Hook Form** - 高性能表单库
- **Zod** - TypeScript优先的模式验证
- **@hookform/resolvers** - 表单验证解析器

### 内容渲染
- **React Markdown** - Markdown内容渲染
- **React Syntax Highlighter** - 代码语法高亮
- **KaTeX** - 数学公式渲染引擎
- **remark-gfm** - GitHub风格Markdown支持
- **remark-math** - 数学公式解析
- **rehype-katex** - KaTeX渲染插件

### 开发工具链
- **pnpm** - 高效的包管理器
- **ESLint + Prettier** - 代码质量和格式化
- **Husky + lint-staged** - Git提交钩子
- **TypeScript ESLint** - TypeScript代码检查
- **PostCSS + Autoprefixer** - CSS后处理

## 后端技术栈

### 核心框架
- **FastAPI 0.110+** - 现代化Python Web框架
- **Python 3.12** - 最新Python版本
- **Uvicorn** - ASGI服务器
- **Pydantic 2+** - 数据验证和序列化

### 数据库 & ORM
- **PostgreSQL 17** - 主数据库，支持pgvector扩展
- **SQLModel** - 基于SQLAlchemy 2.0的现代ORM
- **SQLAlchemy 2.0** - Python SQL工具包
- **Asyncpg** - 异步PostgreSQL驱动
- **Alembic** - 数据库迁移工具

### 缓存 & 消息队列
- **Redis 7+** - 内存数据库，用于缓存和消息队列
- **Celery 5+** - 分布式任务队列
- **Flower** - Celery监控工具

### 认证 & 安全
- **python-jose** - JWT令牌处理
- **passlib + bcrypt** - 密码哈希
- **python-multipart** - 文件上传支持
- **email-validator** - 邮箱验证

### 日志 & 监控
- **Loguru** - 现代化日志库
- **Pydantic Settings** - 配置管理

### HTTP客户端 & WebSocket
- **httpx** - 异步HTTP客户端
- **websockets** - WebSocket支持

### 开发工具
- **Poetry** - Python依赖管理和打包
- **pytest + pytest-asyncio** - 测试框架
- **Black** - 代码格式化
- **Ruff** - 快速Python代码检查器
- **mypy** - 静态类型检查
- **pre-commit** - Git提交前检查

## 模型服务技术栈

### 推理引擎
- **vLLM** - 高性能LLM推理引擎
- **OpenAI API兼容** - 标准化API接口

### 支持的模型类型
- **MoE模型** - 混合专家模型支持
- **DeepSeek系列** - DeepSeekMoE 16B Chat等
- **Qwen系列** - Qwen1.5-MoE-A2.7B等
- **OLMoE系列** - OLMoE-1B-7B-0924等

## 基础设施 & 部署

### 容器化
- **Docker** - 容器化部署
- **Docker Compose** - 多容器编排

### 数据库扩展
- **pgvector** - PostgreSQL向量扩展

### 开发环境
- **Poetry** - Python依赖管理和打包（后端）
- **pip** - Python包安装器（备选）
- **pnpm** - Node.js包管理器（前端）
- **npm** - Node.js包管理器（备选）

## 特色功能技术实现

### MoE专家激活可视化
- **matplotlib + tkinter** - 实时可视化界面
- **Redis Pub/Sub** - 实时数据传输
- **专家激活数据采集** - 从vLLM响应中提取

### 实时通信
- **WebSocket** - 双向实时通信
- **流式响应** - 支持流式文本生成
- **断线重连** - 自动重连机制

### 文件处理
- **多格式支持** - 图片、PDF等文件上传
- **文件清理** - 定时清理未关联文件
- **大小限制** - 文件大小控制

## 字体选择

### 数学公式字体
- **Computer Modern** - LaTeX默认数学字体
- **Latin Modern Math** - 现代化数学字体
- **STIX Two Math** - 高质量数学字体

### 代码字体
- **JetBrains Mono** - 现代等宽字体
- **Fira Code** - 支持连字的代码字体
- **Source Code Pro** - Adobe开源代码字体
- **Cascadia Code** - Microsoft开发的代码字体