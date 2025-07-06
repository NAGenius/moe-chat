#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API模型包
"""

# 请求模型
from app.db.schemas.api.request.auth import (
    LoginRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
    TokenRefreshRequest,
)
from app.db.schemas.api.request.chat import (
    ChatCreateRequest,
    ChatUpdateRequest,
    MessageCreateRequest,
)
from app.db.schemas.api.request.user import PasswordUpdateRequest, UserUpdateRequest
from app.db.schemas.api.response.auth import TokenResponse

# 响应模型
from app.db.schemas.api.response.base import ResponseBase
from app.db.schemas.api.response.chat import (
    ChatCreateResponse,
    ChatListResponse,
    ChatResponse,
    MessageCreateResponse,
    MessageListResponse,
)
from app.db.schemas.api.response.file import FileResponse, FileUploadResponse
from app.db.schemas.api.response.model import ModelListResponse, ModelResponse
from app.db.schemas.api.response.user import UserResponse
