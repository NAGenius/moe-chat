#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API依赖函数

用于FastAPI的依赖注入，如用户认证、权限检查等
"""

import uuid
from typing import Annotated

from app.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.utils.exceptions import ForbiddenException, UnauthorizedException
from app.utils.logger import get_logger
from app.utils.security import decode_token
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlmodel.ext.asyncio.session import AsyncSession

# 获取日志记录器
logger = get_logger(__name__)

# OAuth2 认证方案，设置auto_error=False以便我们可以自定义错误消息
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/login", auto_error=False
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    获取当前用户

    Args:
        token: JWT令牌
        db: 数据库会话

    Returns:
        User: 当前用户

    Raises:
        UnauthorizedException: 未授权异常
    """
    try:
        payload = decode_token(token)
        if payload is None:
            raise UnauthorizedException("无效的认证凭据")
        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedException("无效的认证凭据")
    except JWTError:
        raise UnauthorizedException("无效的认证凭据")

    user_repository = UserRepository(db)
    try:
        user = await user_repository.get_by_id(uuid.UUID(user_id))
    except ValueError:
        raise UnauthorizedException("无效的用户ID")

    if user is None:
        raise UnauthorizedException("用户不存在")

    return user


# 别名，保持向后兼容
get_current_active_user = get_current_user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    获取管理员用户

    Args:
        current_user: 当前用户

    Returns:
        User: 管理员用户

    Raises:
        HTTPException: 用户不是管理员
    """
    if not current_user.is_admin:
        raise ForbiddenException("需要管理员权限")
    return current_user
