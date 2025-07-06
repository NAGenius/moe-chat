#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
认证相关的API端点

包括登录、注册、刷新令牌、发送验证码
"""

from typing import Any, Dict

from app.db.schemas.api.request.auth import (
    LoginRequest,
    RegisterRequest,
    SendVerificationCodeRequest,
    TokenRefreshRequest,
)
from app.db.schemas.api.response.auth import LoginResponse, TokenResponse
from app.db.schemas.api.response.base import (
    ResponseBase,
    SimpleResponse,
    success_response,
)
from app.db.schemas.dto.input.user_dto import UserLoginDTO, UserRegisterDTO
from app.services.auth_service import AuthService, get_auth_service
from app.services.verification_service import (
    VerificationService,
    get_verification_service,
)
from app.utils.exceptions import (
    BadRequestException,
    InternalServerErrorException,
    UnauthorizedException,
)
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, status

router = APIRouter()
logger = get_logger(__name__)


@router.post("/login", response_model=ResponseBase[LoginResponse])
async def login_user(
    login_data: LoginRequest, auth_service: AuthService = Depends(get_auth_service)
) -> Dict[str, Any]:
    """
    用户登录

    使用邮箱和密码登录，返回用户信息和访问令牌
    """
    # 转换为DTO
    login_dto = UserLoginDTO(
        email=login_data.email,
        password=login_data.password,
    )

    # 验证用户凭据
    result = await auth_service.authenticate(login_dto)
    if not result:
        raise UnauthorizedException("邮箱或密码错误")

    # 转换为API响应模型
    login_response = LoginResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )

    logger.info(f"用户登录成功: {login_data.email}")
    return success_response(message="登录成功", data=login_response)


@router.post("/refresh", response_model=ResponseBase[TokenResponse])
async def refresh_token(
    request: TokenRefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> ResponseBase[TokenResponse]:
    """刷新访问令牌"""
    tokens = await auth_service.refresh_token(request.refresh_token)
    if not tokens:
        raise UnauthorizedException("无效的刷新令牌")

    # 创建TokenResponse对象
    token_response = TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
    )

    return ResponseBase[TokenResponse](
        code=status.HTTP_200_OK,
        message="请求成功",
        data=token_response,
    )


@router.post("/register", response_model=ResponseBase[LoginResponse])
async def register_user(
    user_data: RegisterRequest,
    verification_service: VerificationService = Depends(get_verification_service),
    auth_service: AuthService = Depends(get_auth_service),
) -> Dict[str, Any]:
    """
    用户注册

    使用邮箱验证码注册新用户，并自动登录返回令牌
    """
    try:
        # 转换为DTO
        user_register_dto = UserRegisterDTO(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name,
            verification_code=user_data.verification_code,
        )

        # 先验证用户名和邮箱是否已存在（通过尝试注册的方式）
        # 注意：这里只验证用户名和邮箱，不真正注册，因为后面还需要验证验证码
        try:
            # 检查用户名和邮箱是否已存在
            await auth_service.user_repo.check_username_email_exists(
                user_register_dto.username, user_register_dto.email
            )
        except ValueError as e:
            error_message = str(e)
            # 将错误消息转换为更通用的形式
            if "用户名" in error_message:
                error_message = "用户名已被使用"
            elif "邮箱" in error_message:
                error_message = "邮箱已被使用"

            logger.error(f"用户注册验证错误: {error_message}")
            raise BadRequestException(error_message)

        # 验证用户名和邮箱通过后，再验证验证码
        verification_result = await verification_service.verify_code(
            email=user_data.email, code=user_data.verification_code
        )

        if not verification_result.success:
            logger.warning(f"验证码无效: {user_data.email}")
            raise BadRequestException("验证码无效或已过期")

        # 所有验证通过，注册用户
        register_result = await auth_service.register_user(user_register_dto)

        # 转换为API响应模型
        login_response = LoginResponse(
            access_token=register_result.access_token,
            refresh_token=register_result.refresh_token,
            token_type=register_result.token_type,
        )

        logger.info(f"用户注册成功: {user_data.username}")

        return success_response(message="注册成功", data=login_response)
    except BadRequestException as e:
        # 直接重新抛出 BadRequestException
        raise e
    except Exception as e:
        logger.error(f"用户注册过程中发生未知错误: {str(e)}")
        raise InternalServerErrorException("服务器内部错误")


@router.post("/send-verification-code", response_model=SimpleResponse)
async def send_verification_code(
    request: SendVerificationCodeRequest,
    verification_service: VerificationService = Depends(get_verification_service),
) -> Dict[str, Any]:
    """
    发送邮箱验证码

    向指定邮箱发送验证码，用于邮箱验证（注册或修改密码）
    """
    # 发送验证码
    success, _, error = await verification_service.send_verification_code(
        email=request.email
    )

    if not success:
        logger.error(f"发送验证码失败: {error}")
        raise BadRequestException(error or "发送验证码失败")

    # 返回响应，不包含data字段
    return success_response(message="验证码发送成功")
