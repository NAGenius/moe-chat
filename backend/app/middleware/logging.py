#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志中间件

记录请求和响应信息
"""

import time
import uuid
from typing import Any, Callable

from app.utils.logger import get_logger
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# 获取logger实例
logger = get_logger("api.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    日志中间件

    记录请求和响应的详细信息，并支持请求跟踪
    """

    def __init__(self, app: ASGIApp):
        """
        初始化中间件

        Args:
            app: ASGI应用
        """
        super().__init__(app)
        self.logger = get_logger("api.request")

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        """
        处理请求

        Args:
            request: 请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 响应对象
        """
        # 生成唯一请求ID
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # 创建请求上下文
        context = await self._create_request_context(request, request_id)
        request_logger = self.logger.bind(**context)

        # 记录请求开始
        self._log_request_start(request_logger, request)

        # 处理请求
        try:
            request.state.request_id = request_id
            response = await call_next(request)

            # 记录成功响应
            self._log_successful_response(
                request_logger, response, start_time, request_id
            )
            return response
        except Exception as e:
            # 记录异常响应
            self._log_error_response(request_logger, e, start_time)
            raise

    async def _create_request_context(
        self, request: Request, request_id: str
    ) -> dict[str, Any]:
        """创建请求上下文信息"""
        query_params: dict[str, str] = dict(request.query_params)
        client_host = request.client.host if request.client else "unknown"

        context: dict[str, Any] = {
            "request_id": request_id,
            "client": client_host,
        }

        # 添加查询参数
        if query_params:
            context["query_params"] = query_params

        # 添加请求体（如果适用）
        if await self._should_log_request_body(request):
            request_body = await self._get_filtered_request_body(request)
            if request_body:
                context["request_body"] = request_body

        return context

    async def _should_log_request_body(self, request: Request) -> bool:
        """判断是否应该记录请求体"""
        return (
            request.method in ["POST", "PUT", "PATCH"]
            and request.headers.get("content-type") == "application/json"
        )

    async def _get_filtered_request_body(
        self, request: Request
    ) -> dict[str, Any] | None:
        """获取过滤敏感信息后的请求体"""
        try:
            request_body = await request.json()
            if isinstance(request_body, dict):
                filtered_body = request_body.copy()
                for sensitive_field in [
                    "password",
                    "token",
                    "refresh_token",
                    "access_token",
                ]:
                    if sensitive_field in filtered_body:
                        filtered_body[sensitive_field] = "******"
                return filtered_body
        except Exception:
            pass
        return None

    def _log_request_start(self, request_logger: Any, request: Request) -> None:
        """记录请求开始"""
        path = request.url.path
        method = request.method
        api_endpoint = path.split("/api/v1/")[-1] if "/api/v1/" in path else path
        request_logger.info(f"┌── {method} /{api_endpoint}")

    def _log_successful_response(
        self,
        request_logger: Any,
        response: Response,
        start_time: float,
        request_id: str,
    ) -> None:
        """记录成功响应"""
        process_time = time.time() - start_time
        process_time_ms = int(process_time * 1000)

        response_info = {
            "status_code": response.status_code,
            "process_time": f"{process_time:.3f}s",
        }

        status_symbol = "✓" if 200 <= response.status_code < 300 else "✗"
        log_message = (
            f"└── {status_symbol} {response.status_code} ({process_time_ms}ms)"
        )

        # 根据状态码选择日志级别
        if 200 <= response.status_code < 400:
            request_logger.bind(**response_info).info(log_message)
        elif 400 <= response.status_code < 500:
            request_logger.bind(**response_info).warning(log_message)
        else:
            request_logger.bind(**response_info).error(log_message)

        # 添加响应头
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        response.headers["X-Request-ID"] = request_id

    def _log_error_response(
        self, request_logger: Any, error: Exception, start_time: float
    ) -> None:
        """记录异常响应"""
        process_time = time.time() - start_time
        process_time_ms = int(process_time * 1000)

        request_logger.bind(
            error=str(error), process_time=f"{process_time:.3f}s"
        ).error(f"└── ✗ 异常 ({process_time_ms}ms): {str(error)}")


def setup_logging_middleware(app: FastAPI) -> None:
    """
    设置日志中间件

    Args:
        app: FastAPI应用实例
    """
    app.add_middleware(LoggingMiddleware)
    logger.info("日志中间件已设置")
