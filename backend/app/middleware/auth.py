#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
认证中间件模块

处理请求认证和用户信息提取
"""

from typing import Awaitable, Callable, Optional

from app.db.database import get_async_session
from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.utils.logger import get_logger
from app.utils.security import verify_token
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    认证中间件

    从请求中提取认证信息并验证用户身份
    """

    def __init__(self, app: ASGIApp):
        """
        初始化认证中间件

        Args:
            app: ASGI应用实例
        """
        super().__init__(app)
        self.api_prefix = "/api"
        self.exclude_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/api/v1/model",
            "/health",
            "/",
        ]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        处理请求和响应

        Args:
            request: 请求对象
            call_next: 下一个处理函数

        Returns:
            Response: 响应对象
        """
        # 对于不需要认证的路径，直接处理
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # 提取认证信息
        user = await self._extract_user(request)

        # 将用户信息存储在请求状态中
        request.state.user = user

        # 处理请求
        return await call_next(request)

    def _should_skip_auth(self, path: str) -> bool:
        """
        检查是否应该跳过认证

        Args:
            path: 请求路径

        Returns:
            bool: 是否跳过认证
        """
        # 非API请求不需要认证
        if not path.startswith(self.api_prefix):
            return True

        # 检查排除路径
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True

        return False

    async def _extract_user(self, request: Request) -> Optional[User]:
        """
        从请求中提取用户信息

        Args:
            request: 请求对象

        Returns:
            Optional[User]: 用户对象，如果未认证则为None
        """
        # 从请求头中获取认证令牌
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None

        # 解析认证令牌
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None

        token = parts[1]

        # 验证令牌
        user_id = verify_token(token)
        if not user_id:
            return None

        try:
            # 获取用户信息
            async with get_async_session() as session:
                user_repo = UserRepository(session)
                # 使用正确的get方法，接受UUID
                user = await user_repo.get(db=session, id=user_id)

                if user and user.is_active:
                    return user

                return None

        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return None


def setup_auth_middleware(app: FastAPI) -> None:
    """
    设置认证中间件

    Args:
        app: FastAPI应用实例
    """
    app.add_middleware(AuthMiddleware)
    logger.info("认证中间件已设置")
