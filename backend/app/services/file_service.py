#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件服务模块

处理文件上传、删除和定时清理
"""

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional, Tuple

from app.config import settings
from app.db.database import init_db_engine
from app.db.models.file import File, FileCreate
from app.db.repositories.file import FileRepository
from app.utils.exceptions import NotFoundException
from app.utils.logger import get_logger
from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

# 获取日志记录器
logger = get_logger(__name__)


class FileService:
    """文件服务类"""

    def __init__(self, session: AsyncSession):
        """
        初始化文件服务

        Args:
            session: 数据库会话
        """
        self.session = session
        self.file_repository = FileRepository(session)
        self.cleanup_interval = settings.FILE_CLEANUP_INTERVAL  # 从配置读取
        self.file_ttl = settings.FILE_TTL  # 从配置读取
        self._cleanup_task: Optional[asyncio.Task] = None

    async def upload_file(
        self, file: UploadFile, user_id: uuid.UUID, max_size: int = 2 * 1024 * 1024
    ) -> Tuple[File, bytes]:
        """
        上传文件

        Args:
            file: 上传的文件对象
            user_id: 用户ID
            max_size: 最大文件大小（默认2MB）

        Returns:
            Tuple[File, bytes]: 文件记录和文件内容

        Raises:
            BadRequestException: 文件大小超过限制
        """
        # 读取文件内容
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # 重置文件指针

        # 检查文件大小
        if file_size > max_size:
            raise ValueError(f"文件大小超过限制 ({file_size} > {max_size})")

        # 确保上传目录存在
        upload_dir = os.path.join(settings.UPLOAD_DIR, str(user_id))
        os.makedirs(upload_dir, exist_ok=True)

        # 生成唯一文件名
        file_id = uuid.uuid4()
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        file_path = os.path.join(upload_dir, f"{file_id}{file_ext}")

        # 保存文件
        with open(file_path, "wb") as f:
            f.write(content)

        # 创建文件数据模型
        file_data = FileCreate(
            filename=file.filename or "unknown",
            file_path=file_path,
            file_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            user_id=user_id,
        )

        # 创建文件记录
        file_db = await self.file_repository.create_file(file_data)
        return file_db, content

    async def get_file_by_id(self, file_id: uuid.UUID, user_id: uuid.UUID) -> File:
        """
        获取文件信息

        Args:
            file_id: 文件ID
            user_id: 用户ID

        Returns:
            File: 文件对象

        Raises:
            NotFoundException: 文件不存在
        """
        file = await self.file_repository.get_by_id_and_user(file_id, user_id)
        if not file:
            raise NotFoundException("文件不存在")
        return file

    async def verify_file_exists(self, file_path: str) -> bool:
        """
        验证文件是否存在

        Args:
            file_path: 文件路径

        Returns:
            bool: 文件是否存在
        """
        return os.path.exists(file_path)

    async def start_cleanup_task(self) -> None:
        """
        启动文件清理任务
        """
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("文件清理任务已启动")

    async def _cleanup_loop(self) -> None:
        """
        文件清理循环
        """
        try:
            while True:
                try:
                    # 为每次清理创建新的会话，避免使用已关闭的会话
                    db_engine = await init_db_engine()
                    async with AsyncSession(bind=db_engine) as session:
                        # 创建临时仓库
                        temp_repo = FileRepository(session)

                        # 执行清理
                        deleted_count = await self._cleanup_orphaned_files(temp_repo)
                        if deleted_count > 0:
                            logger.info(f"成功清理 {deleted_count} 个未关联的文件")
                except Exception as e:
                    logger.error(f"文件清理周期执行错误: {str(e)}")

                # 等待下一次清理
                await asyncio.sleep(self.cleanup_interval)
        except asyncio.CancelledError:
            logger.info("文件清理任务已取消")
        except Exception as e:
            logger.error(f"文件清理任务异常: {str(e)}")
            # 重新启动清理任务
            self._cleanup_task = None
            await asyncio.sleep(5)  # 等待一段时间后重试
            await self.start_cleanup_task()

    async def _cleanup_orphaned_files(self, repo: FileRepository) -> int:
        """
        清理未关联消息且超过TTL的文件

        Args:
            repo: 文件仓库实例

        Returns:
            int: 删除的文件数量
        """
        # 计算截止时间
        cutoff_time = datetime.now(UTC) - timedelta(seconds=self.file_ttl)

        # 获取需要清理的文件
        orphaned_files = await repo.get_orphaned_files(cutoff_time)

        delete_count = 0
        # 删除文件和记录
        for file_obj in orphaned_files:
            try:
                # 删除物理文件
                file_path = file_obj.file_path
                if os.path.exists(file_path):
                    os.remove(file_path)

                # 删除数据库记录
                await repo.delete_file(file_obj.id)
                delete_count += 1
            except Exception as e:
                logger.error(f"删除文件 {file_obj.id} 失败: {str(e)}")

        return delete_count

    async def stop_cleanup_task(self) -> None:
        """
        停止文件清理任务
        """
        if self._cleanup_task and not self._cleanup_task.done():
            logger.info("取消文件清理任务")
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
