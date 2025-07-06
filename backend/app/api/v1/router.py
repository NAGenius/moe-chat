#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API路由注册

注册所有API端点
"""

from app.api.v1.endpoints import auth, chats, files, health, models, users
from fastapi import APIRouter

# 创建API路由
api_router = APIRouter()

# 注册认证路由
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["认证"],
)

# 注册用户路由
api_router.include_router(
    users.router,
    prefix="/user",
    tags=["用户"],
)

# 注册模型路由
api_router.include_router(
    models.router,
    prefix="/model",
    tags=["模型"],
)

# 注册聊天路由
api_router.include_router(
    chats.router,
    prefix="/chat",
    tags=["聊天"],
)

# 注册文件路由
api_router.include_router(
    files.router,
    prefix="/file",
    tags=["文件"],
)

# 注册健康检查路由
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["健康检查"],
)
