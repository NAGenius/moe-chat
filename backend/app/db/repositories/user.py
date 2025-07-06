#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户仓储类

提供用户相关的数据库操作
"""

import uuid
from datetime import UTC, datetime
from typing import List, Optional

from app.db.models.user import User, UserCreate, UserUpdate
from app.db.repositories.base import BaseRepository
from sqlmodel.ext.asyncio.session import AsyncSession


class UserRepository(BaseRepository[User]):
    """用户仓储类"""

    def __init__(self, session: AsyncSession):
        """
        初始化用户仓储

        Args:
            session: 数据库会话
        """
        super().__init__(session, User)

    async def create_user(self, user_data: UserCreate, hashed_password: str) -> User:
        """
        创建用户

        Args:
            user_data: 用户创建数据
            hashed_password: 已哈希的密码

        Returns:
            User: 创建的用户
        """
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            role=user_data.role,
        )
        return await self.create(user)

    async def update_user(
        self, user_id: uuid.UUID, user_data: UserUpdate
    ) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            user_data: 用户更新数据

        Returns:
            Optional[User]: 更新后的用户，如果不存在则返回None
        """
        user = await self.get(id=user_id)
        if not user:
            return None

        # 更新字段
        update_data = user_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        # 更新时间
        user.updated_at = datetime.now(UTC)

        return await self.update(user)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        通过邮箱获取用户

        Args:
            email: 用户邮箱

        Returns:
            Optional[User]: 查询到的用户，如果不存在则返回None
        """
        return await self.get(email=email)

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        通过用户名获取用户

        Args:
            username: 用户名

        Returns:
            Optional[User]: 查询到的用户，如果不存在则返回None
        """
        return await self.get(username=username)

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """
        通过用户ID获取用户

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 查询到的用户，如果不存在则返回None
        """
        return await self.get(id=user_id)

    async def get_active_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        获取活跃用户列表

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            List[User]: 活跃用户列表
        """
        return await self.list(limit=limit, offset=skip, is_active=True)

    async def update_last_login(self, user_id: uuid.UUID) -> Optional[User]:
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID

        Returns:
            Optional[User]: 更新后的用户，如果不存在则返回None
        """
        user = await self.get(id=user_id)
        if not user:
            return None

        user.last_login_at = datetime.now(UTC)
        return await self.update(user)

    async def check_username_email_exists(self, username: str, email: str) -> None:
        """
        检查用户名和邮箱是否已存在

        Args:
            username: 用户名
            email: 邮箱

        Raises:
            ValueError: 如果用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        existing_user = await self.get_by_username(username)
        if existing_user:
            raise ValueError("用户名已被使用")

        # 检查邮箱是否已存在
        if email:
            existing_email = await self.get_by_email(email)
            if existing_email:
                raise ValueError("邮箱已被使用")
