# MoE-Chat

MoE-Chat是一个基于大型混合专家模型（Mixture of Experts）的聊天应用，支持在边缘设备上部署和使用多种MoE模型，如DeepSeekMoE、Qwen1.5-MoE等。

## 项目特点

- **多模型支持**：支持多种MoE模型，包括DeepSeekMoE 16B Chat、Qwen1.5-MoE-A2.7B、OLMoE-1B-7B-0924等
- **高性能推理**：使用vLLM高性能推理引擎，提供OpenAI兼容API
- **流式生成**：支持流式文本生成，实时显示模型回复
- **优雅的界面**：简洁现代的用户界面，支持深色/浅色主题
- **多用户支持**：用户认证系统，支持不同权限级别
- **对话管理**：保存和管理对话历史
- **文件上传**：支持上传图片和PDF等文件（≤2MB）
- **安全可靠**：JWT认证，数据库和缓存安全

## 项目架构

MoE-Chat采用前后端分离的架构设计：

1. **前端**：Next.js + TypeScript + Tailwind CSS
2. **后端**：FastAPI + PostgreSQL + Redis
3. **模型服务**：vLLM OpenAI兼容API服务器

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- CUDA兼容GPU（用于vLLM）

### 安装步骤

1. 克隆仓库：

```bash
git clone https://github.com/yourusername/moe-chat.git
cd moe-chat
```

2. 设置环境变量：

```bash
# 后端环境变量
cd backend
cp .env.example .env
# 编辑 backend/.env 文件设置配置项

# 前端环境变量
cd ../frontend
cp .env.example .env.local
# 编辑 frontend/.env.local 文件设置配置项
```

3. 启动数据库和Redis（使用Docker）：

```bash
# 返回项目根目录
cd ..
docker-compose up -d
```

4. 初始化数据库：

```bash
cd backend
# 安装依赖
pip install -r requirements.txt
# 或使用 Poetry
poetry install

# 运行数据库迁移
alembic upgrade head
```

5. 启动后端：

```bash
# 使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用 Poetry
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. 启动前端：

```bash
cd ../frontend
npm install
# 或使用 pnpm
pnpm install

# 启动开发服务器
npm run dev
# 或使用 pnpm
pnpm dev
```

7. 访问应用：

打开浏览器访问 http://localhost:3000

## 模型服务

项目支持外部模型服务，通过配置环境变量连接到兼容OpenAI API的模型服务：

- **API兼容性**：支持OpenAI兼容的API接口
- **灵活配置**：通过环境变量配置模型服务地址和API密钥
- **多模型支持**：支持配置多个不同的模型服务
- **流式响应**：支持流式和非流式文本生成

### 配置示例

在 `backend/.env` 文件中配置模型服务：

```bash
# 模型服务配置
MODEL_SERVICE_URL=http://localhost:8000
MODEL_SERVICE_API_KEY=your_api_key_here
DEFAULT_MODEL=your_model_name
```

### 使用示例

```bash
# 通过后端API调用模型服务
curl http://localhost:8000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_jwt_token" \
  -d '{
    "model": "your_model_name",
    "messages": [{"role": "user", "content": "你好，请介绍一下自己"}],
    "stream": false
  }'
```

## 后端API

后端提供RESTful API，支持用户认证、聊天管理、模型访问等功能：

- **用户认证**：注册、登录、刷新令牌、密码重置
- **聊天管理**：创建、查询、更新、删除聊天会话
- **消息处理**：发送消息、获取历史消息、流式响应
- **文件管理**：文件上传、下载、删除
- **用户管理**：用户信息查询和更新
- **系统监控**：健康检查、系统状态

### API文档

启动后端服务后，可以访问以下地址查看完整的API文档：

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Docker部署

项目提供了Docker Compose配置，可以快速启动数据库和Redis服务：

```bash
docker-compose up -d
```

## 数据库连接测试

可以使用以下命令测试数据库连接：

```bash
cd backend
python -c "from app.db.database import test_connection; test_connection()"
```

## 项目结构

```
MoE-Chat/
├── backend/                 # 后端服务
│   ├── app/                # 应用代码
│   │   ├── api/           # API路由
│   │   ├── core/          # 核心配置
│   │   ├── db/            # 数据库相关
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   └── utils/         # 工具函数
│   ├── alembic/           # 数据库迁移
│   ├── .env.example       # 环境变量示例
│   └── requirements.txt   # Python依赖
├── frontend/               # 前端应用
│   ├── src/               # 源代码
│   │   ├── app/          # Next.js应用
│   │   ├── components/   # React组件
│   │   ├── lib/          # 工具库
│   │   └── types/        # TypeScript类型
│   ├── .env.example      # 环境变量示例
│   └── package.json      # Node.js依赖
├── docs/                  # 项目文档
├── docker-compose.yml     # Docker配置
└── README.md             # 项目说明
```

## 开发工具

项目使用了多种开发工具来确保代码质量：

- **后端**：
  - Poetry: Python依赖管理
  - Black: 代码格式化
  - Ruff: 代码检查
  - mypy: 类型检查
  - Alembic: 数据库迁移

- **前端**：
  - ESLint: 代码检查
  - Prettier: 代码格式化
  - TypeScript: 类型检查
  - Tailwind CSS: 样式框架

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request来改进项目。在提交代码前，请确保：

1. 代码通过所有检查（格式化、类型检查等）
2. 添加适当的测试
3. 更新相关文档

## 支持

如果您在使用过程中遇到问题，可以：

1. 查看项目文档
2. 搜索已有的Issue
3. 创建新的Issue描述问题
``` 
</rewritten_file>