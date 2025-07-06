#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据传输对象包

包含服务层使用的输入输出DTO
"""

# 导入常用的输入DTO
from app.db.schemas.dto.input.user_dto import (
    EmailVerificationRequestDTO,
    UserLoginDTO,
    UserRegisterDTO,
    UserUpdateDTO,
)

# 导入常用的输出DTO
from app.db.schemas.dto.output.user_dto import (
    AuthResultDTO,
    EmailVerificationCodeDTO,
    RegisterResultDTO,
    TokenRefreshResultDTO,
    UserDTO,
)
