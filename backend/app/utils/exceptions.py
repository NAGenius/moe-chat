#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自定义异常模块

定义与API文档错误码对应的异常类
"""

from typing import Optional

from fastapi import status


class APIException(Exception):
    """API异常基类"""

    def __init__(
        self,
        code: int = status.HTTP_400_BAD_REQUEST,
        message: str = "请求错误",
        status_code: Optional[int] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code if status_code is not None else code
        super().__init__(self.message)


class BadRequestException(APIException):
    """400 请求参数错误"""

    def __init__(self, message: str = "请求参数错误"):
        super().__init__(code=status.HTTP_400_BAD_REQUEST, message=message)


class UnauthorizedException(APIException):
    """401 未授权"""

    def __init__(self, message: str = "未授权"):
        super().__init__(code=status.HTTP_401_UNAUTHORIZED, message=message)


class ForbiddenException(APIException):
    """403 禁止访问"""

    def __init__(self, message: str = "禁止访问"):
        super().__init__(code=status.HTTP_403_FORBIDDEN, message=message)


class NotFoundException(APIException):
    """404 资源不存在"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=status.HTTP_404_NOT_FOUND, message=message)


class ConflictException(APIException):
    """409 资源冲突"""

    def __init__(self, message: str = "资源冲突"):
        super().__init__(code=status.HTTP_409_CONFLICT, message=message)


class InternalServerErrorException(APIException):
    """500 服务器内部错误"""

    def __init__(self, message: str = "服务器内部错误"):
        super().__init__(code=status.HTTP_500_INTERNAL_SERVER_ERROR, message=message)


class ServiceUnavailableException(APIException):
    """503 服务不可用"""

    def __init__(self, message: str = "服务暂时不可用，请稍后再试"):
        super().__init__(
            code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class GatewayTimeoutException(APIException):
    """504 网关超时"""

    def __init__(self, message: str = "网关超时"):
        super().__init__(
            code=status.HTTP_504_GATEWAY_TIMEOUT,
            message=message,
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )
