#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天仓库模块

处理聊天会话的数据库操作
"""

import uuid
from datetime import UTC, datetime
from typing import List, Optional, Tuple

from app.db.models.chat import Chat, ChatCreate, ChatUpdate
from app.db.repositories.base import BaseRepository
from sqlalchemy import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession


class ChatRepository(BaseRepository[Chat]):
    """聊天仓库类"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Chat)

    async def create_chat(self, chat_data: ChatCreate) -> Chat:
        """
        创建新的聊天会话

        Args:
            chat_data: 聊天创建数据

        Returns:
            Chat: 创建的聊天会话
        """
        chat = Chat(user_id=chat_data.user_id, title=chat_data.title)

        # 手动添加到会话并提交
        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)

        return chat

    async def update_chat(
        self, chat_id: uuid.UUID, chat_update: ChatUpdate
    ) -> Optional[Chat]:
        """
        更新聊天会话

        Args:
            chat_id: 聊天ID
            chat_update: 更新数据

        Returns:
            Optional[Chat]: 更新后的聊天会话，如果不存在则返回None
        """
        chat = await self.get(id=chat_id)
        if not chat:
            return None

        # 更新字段
        update_data = chat_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(chat, key, value)

        # 如果没有明确设置更新时间，则自动更新
        if "updated_at" not in update_data:
            chat.updated_at = datetime.now(UTC)

        # 保存更新
        return await self.update(chat)

    async def get_by_id(self, chat_id: uuid.UUID) -> Optional[Chat]:
        """
        通过ID获取聊天会话

        Args:
            chat_id: 聊天ID

        Returns:
            Optional[Chat]: 聊天会话，如果不存在则返回None
        """
        return await self.get(id=chat_id)

    async def list_by_user(
        self, user_id: uuid.UUID, limit: int = 10, offset: int = 0
    ) -> Tuple[List[Chat], int]:
        """
        获取用户的聊天会话列表

        Args:
            user_id: 用户ID
            limit: 返回的最大记录数
            offset: 偏移量

        Returns:
            Tuple[List[Chat], int]: 聊天会话列表和总数
        """
        # 查询总数
        total = await self.count(user_id=user_id)

        # 查询列表
        query = (
            select(Chat)
            .where(Chat.user_id == user_id)  # type: ignore
            .order_by(desc(Chat.updated_at))  # type: ignore
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        chats = list(result.scalars().all())

        return chats, total

    async def get_by_user_and_id(
        self, user_id: uuid.UUID, chat_id: uuid.UUID
    ) -> Optional[Chat]:
        """
        获取用户的特定聊天会话

        Args:
            user_id: 用户ID
            chat_id: 聊天ID

        Returns:
            Optional[Chat]: 聊天会话，如果不存在或不属于该用户则返回None
        """
        return await self.get(id=chat_id, user_id=user_id)

    async def delete_by_user_and_id(
        self, user_id: uuid.UUID, chat_id: uuid.UUID
    ) -> bool:
        """
        删除用户的特定聊天会话

        Args:
            user_id: 用户ID
            chat_id: 聊天ID

        Returns:
            bool: 是否成功删除
        """
        # 先检查聊天是否存在且属于该用户
        chat = await self.get_by_user_and_id(user_id, chat_id)
        if not chat:
            return False

        # 删除聊天
        await self.session.delete(chat)
        await self.session.commit()
        return True
