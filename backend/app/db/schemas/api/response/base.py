#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API响应基础模型
"""

from typing import Any, Dict, Generic, Optional, Type, TypeVar

from fastapi import status
from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    """API响应基础模型"""

    code: int = Field(..., description="状态码")
    message: str = Field(..., description="描述信息")
    data: Optional[T] = Field(None, description="响应数据")

    class Config:
        json_encoders: Dict[Type[Any], Any] = {
            # 自定义JSON编码器
        }

    def dict(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """重写dict方法，当data为None时不包含data字段"""
        result = super().dict(*args, **kwargs)
        if result.get("data") is None:
            result.pop("data", None)
        return result

    def json(self, *args: Any, **kwargs: Any) -> str:
        """重写json方法，当data为None时不包含data字段"""
        kwargs["exclude_none"] = kwargs.get("exclude_none", False) or self.data is None
        return super().json(*args, **kwargs)


class SimpleResponse(BaseModel):
    """不包含data字段的简单响应模型"""

    code: int = Field(..., description="状态码")
    message: str = Field(..., description="描述信息")


def success_response(
    code: int = status.HTTP_200_OK, message: str = "请求成功", data: Any = None
) -> Dict[str, Any]:
    """
    生成成功响应

    Args:
        code: 状态码，默认为200
        message: 描述信息，默认为"请求成功"
        data: 响应数据，默认为None

    Returns:
        Dict[str, Any]: 响应字典
    """
    response = {"code": code, "message": message}
    if data is not None:
        response["data"] = data
    return response


def error_response(
    code: int = status.HTTP_400_BAD_REQUEST, message: str = "请求错误"
) -> Dict[str, Any]:
    """
    生成错误响应

    Args:
        code: 状态码，默认为400
        message: 错误信息，默认为"请求错误"

    Returns:
        Dict[str, Any]: 响应字典
    """
    return {"code": code, "message": message}
