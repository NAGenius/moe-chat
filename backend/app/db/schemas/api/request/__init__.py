#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API请求模型包
"""

# 身份认证相关请求
from app.db.schemas.api.request.auth import (
    LoginRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
    TokenRefreshRequest,
)

# 聊天相关请求
from app.db.schemas.api.request.chat import (
    ChatCreateRequest,
    ChatUpdateRequest,
    MessageCreateRequest,
)

# 用户相关请求
from app.db.schemas.api.request.user import (
    PasswordUpdateRequest,
    UserUpdateRequest,
)

__all__ = [
    "SendVerificationCodeRequest",
    "RegisterRequest",
    "LoginRequest",
    "TokenRefreshRequest",
    "ChatCreateRequest",
    "ChatUpdateRequest",
    "MessageCreateRequest",
    "UserUpdateRequest",
    "PasswordUpdateRequest",
]
