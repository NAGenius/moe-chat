#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户相关API请求模型
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserUpdateRequest(BaseModel):
    """用户信息更新请求"""

    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="用户名"
    )
    full_name: Optional[str] = Field(None, description="用户全名")
    system_prompt: Optional[str] = Field(None, description="系统提示词")

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_]+$", v):
                raise ValueError("用户名只能包含字母、数字和下划线")
        return v


class PasswordUpdateRequest(BaseModel):
    """密码更新请求"""

    new_password: str = Field(..., min_length=6, description="新密码")
    verification_code: str = Field(
        ..., min_length=6, max_length=6, description="验证码"
    )

    @field_validator("verification_code")
    @classmethod
    def verification_code_must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("验证码必须为数字")
        return v
