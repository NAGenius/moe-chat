#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
认证相关API请求模型
"""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class SendVerificationCodeRequest(BaseModel):
    """发送验证码请求"""

    email: EmailStr = Field(..., description="邮箱地址")


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr = Field(..., description="邮箱地址")
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    verification_code: str = Field(
        ..., min_length=6, max_length=6, description="验证码"
    )
    full_name: str = Field(..., description="用户全名")

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """验证用户名是否只包含字母、数字和下划线"""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class LoginRequest(BaseModel):
    """登录请求"""

    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., description="密码")


class TokenRefreshRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")
