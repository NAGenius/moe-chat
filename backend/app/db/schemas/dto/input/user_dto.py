#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户服务层DTO输入模型
"""

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegisterDTO(BaseModel):
    """用户注册输入DTO"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="电子邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    full_name: Optional[str] = None
    verification_code: str = Field(
        ..., min_length=6, max_length=6, description="邮箱验证码"
    )

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        """验证用户名是否只包含字母、数字和下划线"""
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class UserLoginDTO(BaseModel):
    """用户登录输入DTO"""

    email: str = Field(..., description="电子邮箱")
    password: str = Field(..., description="密码")


class UserUpdateDTO(BaseModel):
    """用户更新输入DTO"""

    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="用户名"
    )
    email: Optional[EmailStr] = Field(None, description="电子邮箱")
    password: Optional[str] = Field(
        None, min_length=6, max_length=100, description="密码"
    )
    current_password: Optional[str] = Field(None, description="当前密码")
    full_name: Optional[str] = None
    system_prompt: Optional[str] = Field(None, description="系统提示词")


class PasswordResetRequestDTO(BaseModel):
    """密码重置请求DTO"""

    email: EmailStr = Field(..., description="电子邮箱")


class PasswordResetDTO(BaseModel):
    """密码重置DTO"""

    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密码")


class EmailVerificationDTO(BaseModel):
    """电子邮箱验证DTO"""

    token: str = Field(..., description="验证令牌")


class EmailVerificationRequestDTO(BaseModel):
    """电子邮箱验证请求DTO"""

    email: EmailStr = Field(..., description="电子邮箱")
