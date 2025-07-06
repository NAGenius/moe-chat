#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
错误处理中间件

处理所有API异常并返回标准格式响应
"""

from typing import Awaitable, Callable

from app.db.schemas.api.response.base import error_response
from app.utils.exceptions import APIException
from app.utils.logger import get_logger
from fastapi import Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import SQLAlchemyError

# 获取日志记录器
logger = get_logger(__name__)


async def error_handler_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """
    错误处理中间件，捕获所有未处理异常并返回统一格式的错误响应

    Args:
        request: 请求对象
        call_next: 下一个中间件或路由处理函数

    Returns:
        响应对象
    """
    try:
        return await call_next(request)
    except Exception as e:
        # 记录异常信息
        logger.exception(f"Unhandled exception: {str(e)}")

        # 返回统一格式的错误响应
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="服务器内部错误"
            ),
        )


async def api_exception_handler(request: Request, exc: Exception) -> Response:
    """
    处理自定义API异常

    Args:
        request: 请求对象
        exc: 自定义API异常

    Returns:
        统一格式的JSON错误响应
    """
    if not isinstance(exc, APIException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="服务器内部错误"
            ),
        )

    # 记录异常日志
    if exc.status_code >= 500:
        # 服务器错误记录更详细的日志
        logger.error(f"服务器错误: {exc.code} - {exc.message}")
        # 对于500错误，统一返回"服务器内部错误"
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code=exc.code, message="服务器内部错误"),
        )
    else:
        # 客户端错误只记录警告
        logger.warning(f"API异常: {exc.code} - {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(code=exc.code, message=exc.message),
        )


async def http_exception_handler(request: Request, exc: Exception) -> Response:
    """
    处理FastAPI的HTTPException

    Args:
        request: 请求对象
        exc: HTTP异常

    Returns:
        统一格式的JSON错误响应
    """
    if not isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="服务器内部错误"
            ),
        )

    # 记录HTTP异常
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")

    # 返回符合API文档格式的错误响应
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(code=exc.status_code, message=exc.detail),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> Response:
    """
    处理请求验证错误

    Args:
        request: 请求对象
        exc: 验证错误异常

    Returns:
        统一格式的JSON错误响应
    """
    if not isinstance(exc, RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="服务器内部错误"
            ),
        )

    # 记录详细的验证错误信息，但返回简化的错误消息给客户端
    error_details = []
    for error in exc.errors():
        error_details.append(
            {
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", ""),
            }
        )

    # 记录详细错误信息到日志，但不返回给客户端
    logger.warning(f"请求参数验证错误: {error_details}")

    # 返回符合API文档格式的统一错误响应
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response(
            code=status.HTTP_400_BAD_REQUEST, message="请求参数错误"
        ),
    )


async def sqlalchemy_exception_handler(request: Request, exc: Exception) -> Response:
    """
    处理SQLAlchemy异常

    Args:
        request: 请求对象
        exc: SQLAlchemy异常

    Returns:
        统一格式的JSON错误响应
    """
    if not isinstance(exc, SQLAlchemyError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="服务器内部错误"
            ),
        )

    # 记录数据库错误
    logger.error(f"Database error: {str(exc)}")

    # 返回符合API文档格式的错误响应
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR, message="数据库操作错误"
        ),
    )
