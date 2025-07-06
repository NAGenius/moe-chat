#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件相关后台任务

包含文件清理、处理等后台任务
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta

from app.config import settings
from app.core.celery_app import celery_app
from app.db.database import init_db_engine
from app.db.repositories.file import FileRepository
from app.utils.logger import get_logger
from celery import Task  # type: ignore
from sqlmodel.ext.asyncio.session import AsyncSession

# 获取日志记录器
logger = get_logger("app.tasks.file")


@celery_app.task(
    name="app.tasks.file_tasks.cleanup_orphaned_files",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1分钟后重试
)
def cleanup_orphaned_files(self: Task) -> int:
    """
    清理未关联消息且超过TTL的文件

    使用异步事件循环来执行数据库操作
    """
    try:
        # 运行异步清理函数
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # 如果没有事件循环，创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(_async_cleanup_orphaned_files())
    except Exception as exc:
        logger.error(f"文件清理任务异常: {str(exc)}")
        self.retry(exc=exc)
        return 0  # 如果重试失败，返回0


async def _async_cleanup_orphaned_files() -> int:
    """
    异步执行文件清理操作

    Returns:
        int: 删除的文件数量
    """
    # 计算截止时间
    cutoff_time = datetime.now(UTC) - timedelta(seconds=settings.FILE_TTL)

    # 初始化数据库引擎和会话
    db_engine = await init_db_engine()
    deleted_count = 0

    try:
        async with AsyncSession(bind=db_engine) as session:
            # 创建仓库
            repo = FileRepository(session)

            # 获取需要清理的文件
            orphaned_files = await repo.get_orphaned_files(cutoff_time)

            # 删除文件和记录
            for file_obj in orphaned_files:
                try:
                    # 删除物理文件
                    file_path = file_obj.file_path
                    if os.path.exists(file_path):
                        os.remove(file_path)

                    # 删除数据库记录
                    await repo.delete_file(file_obj.id)
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除文件 {file_obj.id} 失败: {str(e)}")

            # 记录结果
            if deleted_count > 0:
                logger.info(f"成功清理 {deleted_count} 个未关联的文件")

            return deleted_count
    except Exception as e:
        logger.error(f"文件清理任务执行错误: {str(e)}")
        raise
    finally:
        await db_engine.dispose()
