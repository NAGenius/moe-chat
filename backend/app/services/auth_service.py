#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
认证服务

处理用户认证、注册、令牌刷新等功能
"""

import uuid
from datetime import UTC, datetime
from typing import Optional

from app.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.schemas.dto.input.user_dto import UserLoginDTO, UserRegisterDTO
from app.db.schemas.dto.output.user_dto import (
    AuthResultDTO,
    RegisterResultDTO,
    TokenRefreshResultDTO,
    UserDTO,
)
from app.utils.exceptions import ForbiddenException, UnauthorizedException
from app.utils.logger import get_logger
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from fastapi import Depends
from jose import JWTError, jwt
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger(__name__)


class AuthService:
    """认证服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def authenticate(self, login_dto: UserLoginDTO) -> Optional[AuthResultDTO]:
        """
        验证用户凭据并返回认证结果

        Args:
            login_dto: 登录数据DTO

        Returns:
            Optional[AuthResultDTO]: 如果认证成功，返回认证结果；否则返回None
        """
        # 尝试通过用户名查找用户
        user = await self.user_repo.get_by_username(login_dto.email)

        # 如果未找到，尝试通过邮箱查找
        if not user:
            user = await self.user_repo.get_by_email(login_dto.email)

        if not user:
            logger.warning(f"登录失败：用户名或邮箱 '{login_dto.email}' 不存在")
            return None

        # 验证密码
        if not verify_password(login_dto.password, user.hashed_password):
            logger.warning(f"登录失败：用户 '{user.username}' 密码错误")
            return None

        # 更新最后登录时间
        user.last_login_at = datetime.now(UTC)
        await self.user_repo.update(user)

        # 生成访问令牌和刷新令牌
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # 返回符合API文档的认证结果DTO
        return AuthResultDTO(
            user_id=str(user.id),
            username=user.username,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def register_user(self, user_dto: UserRegisterDTO) -> RegisterResultDTO:
        """
        注册新用户

        Args:
            user_dto: 用户注册数据DTO

        Returns:
            RegisterResultDTO: 注册结果DTO

        Raises:
            ValueError: 如果用户名或邮箱已存在
        """
        # 检查用户名和邮箱逻辑已移至repository层，这里不再进行检查

        # 创建用户
        hashed_password = get_password_hash(user_dto.password)

        # 创建User模型对象而不是字典
        new_user = User(
            username=user_dto.username,
            email=user_dto.email,
            hashed_password=hashed_password,
            full_name=user_dto.full_name,
        )

        # 使用模型对象创建用户
        user = await self.user_repo.create(new_user)

        # 生成访问令牌和刷新令牌
        access_token = create_access_token(data={"sub": str(user.id)})
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        # 返回符合API文档的注册结果DTO
        return RegisterResultDTO(
            user_id=str(user.id),
            username=user.username,
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_token(
        self, refresh_token: str
    ) -> Optional[TokenRefreshResultDTO]:
        """
        使用刷新令牌获取新的访问令牌

        Args:
            refresh_token: 刷新令牌

        Returns:
            Optional[TokenRefreshResultDTO]: 如果刷新成功，返回刷新令牌结果DTO；否则返回None
        """
        try:
            # 解码刷新令牌
            payload = jwt.decode(
                refresh_token,
                settings.JWT_REFRESH_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )

            # 检查令牌类型
            if payload.get("type") != "refresh":
                logger.warning("刷新令牌类型无效")
                return None

            user_id = payload.get("sub")
            if user_id is None:
                logger.warning("刷新令牌中无用户ID")
                return None

            # 检查用户是否存在
            user = await self.user_repo.get_by_id(uuid.UUID(user_id))
            if not user or not user.is_active:
                logger.warning(f"用户 ID {user_id} 不存在或未激活")
                return None

            # 生成新的令牌
            access_token = create_access_token(data={"sub": str(user.id)})
            new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

            # 返回符合API文档的刷新令牌结果DTO
            return TokenRefreshResultDTO(
                access_token=access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
            )

        except JWTError:
            logger.warning("刷新令牌无效")
            return None

    def _convert_to_user_dto(self, user: User) -> UserDTO:
        """
        将用户模型转换为DTO

        Args:
            user: 用户模型

        Returns:
            UserDTO: 用户DTO
        """
        return UserDTO(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            full_name=user.full_name,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        )


# 依赖函数
async def get_current_user(token: str, db: AsyncSession = Depends(get_db)) -> User:
    """
    获取当前用户

    Args:
        token: JWT令牌
        db: 数据库会话

    Returns:
        User: 当前用户

    Raises:
        HTTPException: 如果令牌无效或用户不存在
    """
    credentials_exception = UnauthorizedException("无效的认证凭据")

    try:
        # 解码JWT令牌
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")
        if user_id is None or not isinstance(user_id, str):
            raise credentials_exception

        # 检查令牌类型
        token_type = payload.get("type")
        if token_type != "access":
            raise UnauthorizedException("需要访问令牌")
    except JWTError:
        raise credentials_exception

    # 查询用户
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(uuid.UUID(user_id))

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise ForbiddenException("用户已被禁用")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    获取当前活跃用户

    Args:
        current_user: 当前用户

    Returns:
        User: 当前活跃用户

    Raises:
        HTTPException: 用户不活跃
    """
    if not current_user.is_active:
        logger.warning(f"用户 {current_user.username} 已被禁用")
        raise ForbiddenException("用户已被禁用")
    return current_user


def get_auth_service(
    session: AsyncSession = Depends(get_db),
) -> AuthService:
    """
    获取认证服务实例

    Args:
        session: 数据库会话

    Returns:
        AuthService: 认证服务实例
    """
    return AuthService(session)
