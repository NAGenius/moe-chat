#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
限流中间件

实现API请求速率限制
"""

import time
from typing import Awaitable, Callable, Dict, Tuple

from app.config import settings
from app.utils.exceptions import APIException
from app.utils.logger import get_logger
from fastapi import FastAPI, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# 获取日志记录器
logger = get_logger("app.middleware.rate_limit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件

    基于客户端IP地址实现请求速率限制
    """

    def __init__(self, app: ASGIApp):
        """
        初始化中间件

        Args:
            app: ASGI应用
        """
        super().__init__(app)
        self.logger = get_logger("app.middleware.rate_limit")
        self.rate_limit = settings.RATE_LIMIT_REQUESTS  # 每分钟允许的请求数
        self.window_size = 60  # 时间窗口大小，单位为秒
        self.clients: Dict[str, Tuple[int, float]] = {}  # 客户端请求计数器

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象

        Raises:
            HTTPException: 请求超出速率限制
        """
        # 获取客户端IP
        client_ip = request.client.host if request.client else "unknown"

        # 检查是否需要限流
        if request.url.path.startswith(settings.API_PREFIX):
            # 当前时间
            now = time.time()

            # 获取客户端请求计数和上次请求时间
            count, window_start = self.clients.get(client_ip, (0, now))

            # 检查是否需要重置时间窗口
            if now - window_start > self.window_size:
                # 重置计数器和窗口开始时间
                count = 0
                window_start = now

            # 增加请求计数
            count += 1

            # 更新客户端请求信息
            self.clients[client_ip] = (count, window_start)

            # 检查是否超出速率限制
            if count > self.rate_limit:
                self.logger.warning(
                    f"请求限流: {client_ip} 超出速率限制 "
                    f"({count}/{self.rate_limit} 请求/分钟)"
                )

                # 返回429状态码
                raise APIException(
                    code=status.HTTP_429_TOO_MANY_REQUESTS,
                    message="请求过于频繁，请稍后再试",
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        # 处理请求
        response = await call_next(request)
        return response


def setup_rate_limit_middleware(
    app: FastAPI,
) -> None:
    """
    设置限流中间件

    Args:
        app: ASGI应用实例
    """
    app.add_middleware(
        RateLimitMiddleware,
    )
    logger.info(f"限流中间件已设置，限制: {settings.RATE_LIMIT_REQUESTS} 请求/分钟")
