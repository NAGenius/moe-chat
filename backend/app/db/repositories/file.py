#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件仓库模块

处理文件的数据库操作
"""

import uuid
from datetime import datetime
from typing import List, Optional

from app.db.models.file import File, FileCreate
from app.db.repositories.base import BaseRepository
from sqlalchemy import and_, desc, select
from sqlmodel.ext.asyncio.session import AsyncSession


class FileRepository(BaseRepository[File]):
    """文件仓库类"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, File)

    async def get_by_id(self, file_id: uuid.UUID) -> Optional[File]:
        """
        通过ID获取文件

        Args:
            file_id: 文件ID

        Returns:
            Optional[File]: 文件对象，如果不存在则为None
        """
        return await self.get(id=file_id)

    async def get_by_id_and_user(
        self, file_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[File]:
        """
        通过ID和用户ID获取文件

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            Optional[File]: 文件对象，如果不存在则为None
        """
        statement = select(File).where(
            and_(File.id == file_id, File.user_id == user_id)  # type: ignore
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_file(self, file_data: FileCreate) -> File:
        """
        创建文件记录

        Args:
            file_data: 文件创建数据

        Returns:
            File: 创建的文件记录
        """
        file = File(
            filename=file_data.filename,
            file_path=file_data.file_path,
            file_type=file_data.file_type,
            file_size=file_data.file_size,
            user_id=file_data.user_id,
            message_id=file_data.message_id,
        )
        self.session.add(file)
        await self.session.commit()
        await self.session.refresh(file)
        return file

    async def get_by_user(
        self, user_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> List[File]:
        """
        获取用户的文件列表

        Args:
            user_id: 用户ID
            limit: 返回的最大记录数
            offset: 偏移量

        Returns:
            List[File]: 文件列表
        """
        return await self.list(limit=limit, offset=offset, user_id=user_id)

    async def get_by_message(self, message_id: uuid.UUID) -> List[File]:
        """
        获取消息的文件列表

        Args:
            message_id: 消息ID

        Returns:
            List[File]: 文件列表
        """
        return await self.list(limit=100, message_id=message_id)

    async def delete_file(self, file_id: uuid.UUID) -> bool:
        """
        删除文件记录

        Args:
            file_id: 文件ID

        Returns:
            bool: 是否成功删除
        """
        deleted_count = await self.delete(id=file_id)
        return deleted_count > 0

    async def get_orphaned_files(self, cutoff_time: datetime) -> List[File]:
        """
        获取未关联消息且早于指定时间的文件

        Args:
            cutoff_time: 截止时间

        Returns:
            List[File]: 未关联文件列表
        """
        statement = (
            select(File)
            .where(
                and_(
                    File.message_id.is_(None),  # type: ignore
                    File.created_at < cutoff_time,  # type: ignore
                )
            )
            .order_by(desc(File.created_at))  # type: ignore
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())
