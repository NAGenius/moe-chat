#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户服务模块

处理用户管理和个人资料相关功能
"""

import uuid
from typing import Optional

from app.db.database import get_db
from app.db.models.user import User
from app.db.repositories.user import UserRepository
from app.db.schemas.dto.input.user_dto import UserUpdateDTO
from app.db.schemas.dto.output.user_dto import UserDTO
from app.services.cache_service import CacheService
from app.utils.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from app.utils.logger import get_logger
from app.utils.redis_client import RedisClient, get_redis
from app.utils.security import get_password_hash
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

# 获取日志记录器
logger = get_logger(__name__)


class UserService:
    """用户服务类"""

    def __init__(
        self, session: AsyncSession, redis_client: Optional[RedisClient] = None
    ):
        """
        初始化用户服务

        Args:
            session: 数据库会话
            redis_client: Redis客户端，用于缓存
        """
        self.session = session
        self.user_repo = UserRepository(session)
        self.cache_service = CacheService(redis_client) if redis_client else None

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        """
        根据ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            User: 用户对象

        Raises:
            HTTPException: 如果用户不存在
        """
        # 先尝试从缓存获取
        if self.cache_service:
            cached_user = await self.cache_service.get_cached_user(str(user_id))
            if cached_user:
                # 从缓存中获取用户
                # 需要从数据库获取完整用户对象
                user = await self.user_repo.get_by_id(user_id)
                if not user:
                    logger.warning(f"用户不存在: {user_id}")
                    raise NotFoundException("用户不存在")
                return user

        # 缓存未命中，从数据库获取
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"用户不存在: {user_id}")
            raise NotFoundException("用户不存在")

        # 缓存用户信息
        if self.cache_service:
            await self.cache_service.cache_user(user)

        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        user_update_dto: Optional[UserUpdateDTO] = None,
    ) -> bool:
        """
        更新用户信息，通用方法

        Args:
            user_id: 用户ID
            username: 新的用户名（可选）
            full_name: 新的用户全名/显示名称（可选）
            system_prompt: 新的系统提示词（可选）
            email: 新的邮箱（可选）
            password: 新的密码（可选）
            user_update_dto: 用户更新DTO（可选，优先级高于单独参数）

        Returns:
            bool: 是否更新成功

        Raises:
            HTTPException: 如果用户名或邮箱已被其他用户使用
        """
        # 处理DTO参数
        update_params = self._process_update_params(
            user_update_dto, username, full_name, system_prompt, email, password
        )

        # 获取用户
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"更新用户信息失败: 用户 ID {user_id} 不存在")
            return False

        # 验证和更新用户信息
        await self._validate_and_update_user(user, user_id, **update_params)

        # 保存更新
        await self.user_repo.update(user)
        logger.info(f"用户 ID {user_id} 信息更新成功")

        # 使缓存失效
        if self.cache_service:
            await self.cache_service.invalidate_user_cache(str(user_id))

        return True

    def _process_update_params(
        self,
        user_update_dto: Optional[UserUpdateDTO],
        username: Optional[str],
        full_name: Optional[str],
        system_prompt: Optional[str],
        email: Optional[str],
        password: Optional[str],
    ) -> dict:
        """处理更新参数"""
        if user_update_dto:
            update_data = user_update_dto.model_dump(exclude_unset=True)
            return {
                "username": update_data.get("username", username),
                "full_name": update_data.get("full_name", full_name),
                "system_prompt": update_data.get("system_prompt", system_prompt),
                "email": update_data.get("email", email),
                "password": update_data.get("password", password),
            }
        return {
            "username": username,
            "full_name": full_name,
            "system_prompt": system_prompt,
            "email": email,
            "password": password,
        }

    async def _validate_and_update_user(
        self,
        user: User,
        user_id: uuid.UUID,
        username: Optional[str],
        full_name: Optional[str],
        system_prompt: Optional[str],
        email: Optional[str],
        password: Optional[str],
    ) -> None:
        """验证并更新用户信息"""
        # 检查用户名
        if username and username != user.username:
            await self._validate_username(username, user_id)
            user.username = username

        # 检查邮箱
        if email and email != user.email:
            await self._validate_email(email, user_id)
            user.email = email

        # 更新其他字段
        if full_name is not None:
            user.full_name = full_name
        if system_prompt is not None:
            user.system_prompt = system_prompt
        if password:
            user.hashed_password = get_password_hash(password)

    async def _validate_username(self, username: str, user_id: uuid.UUID) -> None:
        """验证用户名是否可用"""
        existing_user = await self.user_repo.get_by_username(username)
        if existing_user and existing_user.id != user_id:
            logger.warning(f"更新用户失败: 用户名 {username} 已存在")
            raise ConflictException("用户名已被使用")

    async def _validate_email(self, email: str, user_id: uuid.UUID) -> None:
        """验证邮箱是否可用"""
        existing_email = await self.user_repo.get_by_email(email)
        if existing_email and existing_email.id != user_id:
            logger.warning(f"更新用户失败: 邮箱 {email} 已存在")
            raise BadRequestException("邮箱已被使用")

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        """
        删除用户

        Args:
            user_id: 用户ID

        Returns:
            bool: 是否删除成功
        """
        result = await self.user_repo.delete(id=user_id)
        success = result > 0
        if success:
            logger.info(f"用户 ID {user_id} 删除成功")
            # 使缓存失效
            if self.cache_service:
                await self.cache_service.invalidate_user_cache(str(user_id))
        else:
            logger.warning(f"删除用户失败: 用户 ID {user_id} 不存在")
        return success

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


async def get_user_service(
    session: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
) -> UserService:
    """
    获取用户服务实例

    Args:
        session: 数据库会话
        redis_client: Redis客户端

    Returns:
        UserService: 用户服务实例
    """
    return UserService(session, redis_client)
