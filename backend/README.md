# MoE-Chat 后端

基于FastAPI的MoE-Chat后端服务，支持多种混合专家模型(Mixture of Experts)接入。

## 功能

- 用户认证与授权
- 聊天会话管理
- WebSocket实时通信
- 多模型支持
- 健康检查API

## 安装

```bash
# 使用uv安装（推荐）
uv venv
uv pip install -e .

# 或使用pip安装
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .
```

## 配置

复制环境变量示例文件并修改：

```bash
cp .env.example .env
```

### 数据库配置

在`.env`文件中设置数据库URL：

```
DATABASE_URL=postgresql+asyncpg://用户名:密码@主机:端口/数据库名
```

### Redis配置 

在`.env`文件中设置Redis URL：

```
REDIS_URL=redis://用户名:密码@主机:端口/数据库号
```

## 数据库初始化

首次运行前需要创建数据库并应用迁移：

```bash
# 创建PostgreSQL数据库（如果不存在）
python -m scripts.create_database

# 应用数据库迁移
alembic upgrade head
```

## 运行

```bash
# 开发模式
uvicorn app.main:app --reload

# 生产模式
uvicorn app.main:app
```

## 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "描述"

# 应用最新迁移
alembic upgrade head
```

## 测试数据库连接

```bash
python -m app.db.test_connection
``` 