#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据结构模块

包含以下子模块:
- api: API请求和响应模型
- dto: 数据传输对象
"""

# API模型
from app.db.schemas.api.request.auth import (
    LoginRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
    TokenRefreshRequest,
)
from app.db.schemas.api.response.auth import LoginResponse, TokenResponse
from app.db.schemas.api.response.base import (
    ResponseBase,
    error_response,
    success_response,
)

# DTO模型
from app.db.schemas.dto.input.user_dto import UserLoginDTO, UserRegisterDTO
from app.db.schemas.dto.output.user_dto import UserDTO
