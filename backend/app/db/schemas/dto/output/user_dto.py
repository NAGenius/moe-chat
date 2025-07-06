#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户服务层DTO输出模型
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserDTO(BaseModel):
    """用户信息DTO"""

    id: UUID
    username: str
    email: EmailStr
    is_active: bool
    full_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class UsersListDTO(BaseModel):
    """用户列表DTO"""

    users: List[UserDTO]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuthResultDTO(BaseModel):
    """认证结果DTO"""

    user_id: str
    username: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshResultDTO(BaseModel):
    """令牌刷新结果DTO"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterResultDTO(BaseModel):
    """注册结果DTO"""

    user_id: str
    username: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class PasswordResetResultDTO(BaseModel):
    """密码重置结果DTO"""

    success: bool
    message: str


class EmailVerificationResultDTO(BaseModel):
    """电子邮箱验证结果DTO"""

    success: bool
    message: str


class EmailVerificationCodeDTO(BaseModel):
    """电子邮箱验证码DTO"""

    email: str
    expires_in: int
