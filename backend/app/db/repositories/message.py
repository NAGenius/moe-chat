#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
消息仓库模块

处理聊天消息的数据库操作
"""

import uuid
from datetime import datetime

try:
    from datetime import UTC
except ImportError:
    # Python < 3.11 compatibility
    from datetime import timezone

    UTC = timezone.utc
from typing import List, Optional, Tuple

from app.db.models.message import Message, MessageCreate, MessageUpdate
from app.db.repositories.base import BaseRepository
from sqlalchemy import desc, func, select
from sqlmodel.ext.asyncio.session import AsyncSession


class MessageRepository(BaseRepository[Message]):
    """消息仓库"""

    def __init__(self, session: AsyncSession):
        """
        初始化消息仓库

        Args:
            session: 数据库会话
        """
        super().__init__(session, Message)

    async def create_message(self, message_create: MessageCreate) -> Message:
        """
        创建消息

        Args:
            message_create: 消息创建模型

        Returns:
            Message: 创建的消息
        """
        message = Message.model_validate(message_create)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def update_message(
        self, message_id: uuid.UUID, message_update: MessageUpdate
    ) -> Optional[Message]:
        """
        更新消息

        Args:
            message_id: 消息ID
            message_update: 消息更新模型

        Returns:
            Optional[Message]: 更新后的消息，如果消息不存在则为None
        """
        # 获取消息
        message = await self.get_by_id(message_id)
        if not message:
            return None

        # 更新消息
        update_data = message_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(message, key, value)

        message.updated_at = datetime.now(UTC)
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def list_by_chat(
        self,
        chat_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        before_id: Optional[uuid.UUID] = None,
    ) -> List[Message]:
        """
        获取聊天的消息列表

        Args:
            chat_id: 聊天ID
            limit: 返回的最大记录数
            offset: 偏移量，用于分页
            before_id: 获取此ID之前的消息

        Returns:
            List[Message]: 消息列表
        """
        query = select(Message).where(Message.chat_id == chat_id)  # type: ignore

        # 如果指定了before_id，则获取该ID之前的消息
        if before_id:
            # 先获取before_id消息的创建时间
            before_message = await self.get_by_id(before_id)
            if before_message:
                query = query.where(
                    Message.created_at < before_message.created_at  # type: ignore
                )

        # 按创建时间降序排序，并添加分页
        query = (
            query.order_by(desc(Message.created_at))  # type: ignore
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_chat_and_id(
        self, chat_id: uuid.UUID, message_id: uuid.UUID
    ) -> Optional[Message]:
        """
        获取聊天中的特定消息

        Args:
            chat_id: 聊天ID
            message_id: 消息ID

        Returns:
            Optional[Message]: 消息对象，如果不存在则为None
        """
        return await self.get(chat_id=chat_id, id=message_id)

    async def get_latest_by_chat(self, chat_id: uuid.UUID) -> Optional[Message]:
        """
        获取聊天的最新消息

        Args:
            chat_id: 聊天ID

        Returns:
            Optional[Message]: 最新消息，如果不存在则为None
        """
        query = (
            select(Message)
            .where(Message.chat_id == chat_id)  # type: ignore
            .order_by(desc(Message.created_at))  # type: ignore
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_children(self, parent_id: uuid.UUID) -> List[Message]:
        """
        获取父消息的所有子消息

        Args:
            parent_id: 父消息ID

        Returns:
            List[Message]: 子消息列表
        """
        return await self.list(limit=1000, parent_id=parent_id)

    async def count_by_chat(self, chat_id: uuid.UUID) -> int:
        """
        统计指定聊天的消息数量

        Args:
            chat_id: 聊天ID

        Returns:
            int: 消息数量
        """
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.chat_id == chat_id)  # type: ignore
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def list_by_chat_with_count(
        self, chat_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> Tuple[List[Message], int]:
        """
        获取指定聊天的消息列表及总数

        Args:
            chat_id: 聊天ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            Tuple[List[Message], int]: 消息列表和总数
        """
        # 查询总数
        count_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.chat_id == chat_id)  # type: ignore
        )
        result = await self.session.execute(count_stmt)
        total_count = result.scalar() or 0

        # 查询消息列表，按position升序排序
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)  # type: ignore
            .order_by(Message.position)  # type: ignore
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = result.scalars().all()

        return list(messages), total_count

    async def get_recent_messages(
        self, chat_id: uuid.UUID, limit: int = 10
    ) -> List[Message]:
        """
        获取指定聊天的最近消息

        Args:
            chat_id: 聊天ID
            limit: 限制数量

        Returns:
            List[Message]: 消息列表
        """
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)  # type: ignore
            .order_by(desc(Message.position))  # type: ignore
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        messages = result.scalars().all()
        return list(reversed(messages))

    async def get_last_message(self, chat_id: uuid.UUID) -> Optional[Message]:
        """
        获取指定聊天的最后一条消息

        Args:
            chat_id: 聊天ID

        Returns:
            Optional[Message]: 最后一条消息，如果不存在则为None
        """
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)  # type: ignore
            .order_by(desc(Message.position))  # type: ignore
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, message_id: uuid.UUID) -> Optional[Message]:
        """
        根据ID获取消息

        Args:
            message_id: 消息ID

        Returns:
            Optional[Message]: 消息，如果不存在则为None
        """
        stmt = select(Message).where(Message.id == message_id)  # type: ignore
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
