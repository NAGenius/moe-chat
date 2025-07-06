#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API响应模型包
"""

from app.db.schemas.api.response.auth import LoginResponse, TokenResponse
from app.db.schemas.api.response.base import (
    ResponseBase,
    error_response,
    success_response,
)
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

__all__ = [
    "success_response",
    "error_response",
    "ResponseBase",
    "TokenResponse",
    "LoginResponse",
    "UserResponse",
    "ModelResponse",
    "ModelListResponse",
    "ChatResponse",
    "ChatListResponse",
    "MessageListResponse",
    "ChatCreateResponse",
    "MessageCreateResponse",
    "FileResponse",
    "FileUploadResponse",
]
