#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户相关API端点
"""

from app.api.deps import get_current_user
from app.db.models.user import User
from app.db.schemas.api.request.user import PasswordUpdateRequest, UserUpdateRequest
from app.db.schemas.api.response.base import (
    SimpleResponse,
    success_response,
)
from app.db.schemas.api.response.user import UserResponse
from app.db.schemas.dto.input.user_dto import UserUpdateDTO
from app.services.user_service import UserService, get_user_service
from app.services.verification_service import (
    VerificationService,
    get_verification_service,
)
from app.utils.exceptions import BadRequestException, InternalServerErrorException
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    获取当前登录用户的详细信息。

    返回:
        - 用户信息
    """
    # 转换为API响应
    response = UserResponse(
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        system_prompt=current_user.system_prompt,
    )

    return success_response(data=response.dict())


@router.put("/me", summary="更新用户信息", response_model=SimpleResponse)
async def update_user_info(
    request: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
) -> SimpleResponse:
    """
    更新当前用户的信息。

    参数:
        - request: 请求体
            - username: 用户名（可选）
            - full_name: 用户全名/显示名称（可选）
            - system_prompt: 系统提示词（可选）

    返回:
        - 操作结果
    """
    # 转换为DTO
    update_dto = UserUpdateDTO(
        username=request.username,
        email=None,
        password=None,
        current_password=None,
        full_name=request.full_name,
        system_prompt=request.system_prompt,
    )

    # 更新用户信息
    success = await user_service.update_user(
        current_user.id, user_update_dto=update_dto
    )
    if not success:
        raise InternalServerErrorException("更新用户信息失败")

    return SimpleResponse(code=200, message="更新成功")


@router.put("/me/password", summary="更新用户密码", response_model=SimpleResponse)
async def update_password(
    request: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
    verification_service: VerificationService = Depends(get_verification_service),
) -> SimpleResponse:
    """
    更新当前用户的密码，需要邮箱验证码验证。

    参数:
        - request: 请求体
            - new_password: 新密码（至少6个字符）
            - verification_code: 邮箱验证码（6位数字）

    返回:
        - 操作结果
    """
    # 验证验证码
    verification_result = await verification_service.verify_code(
        current_user.email, request.verification_code
    )
    if not verification_result.success:
        raise BadRequestException("验证码无效或已过期")

    # 更新密码
    success = await user_service.update_user(
        current_user.id, password=request.new_password
    )
    if not success:
        raise InternalServerErrorException("更新密码失败")

    return SimpleResponse(code=200, message="更新成功")
