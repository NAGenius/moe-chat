#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库连接和会话管理

提供数据库连接、会话管理和初始化功能
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from app.config import settings
from app.utils.exceptions import (
    APIException,
    InternalServerErrorException,
    ServiceUnavailableException,
)
from app.utils.logger import get_logger
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

logger = get_logger("app.db")

# 定义基类供Alembic使用
Base = SQLModel

# 重连尝试次数
MAX_RETRY_COUNT = 3
# 重连间隔（秒）
RETRY_INTERVAL = 1.0

# 创建异步引擎
engine: Optional[AsyncEngine] = None


async def init_db_engine() -> AsyncEngine:
    """
    初始化数据库引擎，包含重连机制

    Returns:
        AsyncEngine: SQLAlchemy异步引擎
    """
    global engine

    if engine is None:
        retry_count = 0
        while retry_count < MAX_RETRY_COUNT:
            try:
                db_logger = logger.bind(component="engine")
                # 创建异步引擎
                engine = create_async_engine(
                    str(settings.SQLALCHEMY_DATABASE_URI),
                    echo=settings.DEBUG,  # 根据DEBUG模式决定是否显示SQL
                    future=True,
                    pool_pre_ping=True,  # 连接池健康检查
                    pool_size=5,  # 连接池大小（减少以避免连接泄漏）
                    max_overflow=10,  # 最大溢出连接数（减少）
                    pool_timeout=30,  # 连接池超时时间
                    pool_recycle=1800,  # 连接回收时间（30分钟）
                    pool_reset_on_return="commit",  # 连接返回时重置状态
                    connect_args={
                        "server_settings": {"timezone": "UTC"}
                    },  # 设置时区为UTC
                )

                # 测试连接 - 使用 text() 来创建可执行的 SQL 语句
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))

                db_logger.success("数据库连接成功")
                break
            except (OperationalError, DBAPIError) as e:
                retry_count += 1
                if retry_count >= MAX_RETRY_COUNT:
                    logger.error(f"数据库连接失败，已达到最大重试次数: {str(e)}")
                    raise ServiceUnavailableException("数据库服务不可用，请联系管理员")
                logger.warning(
                    f"数据库连接失败，尝试重连 ({retry_count}/{MAX_RETRY_COUNT}): {str(e)}"
                )
                await asyncio.sleep(RETRY_INTERVAL)
            except Exception as e:
                logger.exception(f"数据库初始化异常: {str(e)}")
                raise InternalServerErrorException("数据库初始化异常，请联系管理员")

    if engine is None:
        raise InternalServerErrorException("数据库引擎初始化失败")
    return engine


# 初始化异步会话工厂
async def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取异步会话工厂"""
    db_engine = await init_db_engine()
    return async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=True,  # 启用自动刷新以确保数据一致性
    )


async def init_db() -> None:
    """
    初始化数据库

    创建所有表（如果不存在）
    """
    try:
        db_engine = await init_db_engine()
        async with db_engine.begin() as conn:
            # 创建所有表
            await conn.run_sync(SQLModel.metadata.create_all)

        logger.success("数据库表初始化成功")
    except SQLAlchemyError as e:
        logger.exception(f"数据库表初始化失败: {str(e)}")
        raise InternalServerErrorException("数据库初始化失败，请联系管理员")


async def close_db() -> None:
    """
    关闭数据库连接

    应用关闭时清理数据库资源
    """
    global engine
    if engine:
        # 关闭所有连接
        await engine.dispose()
        logger.info("数据库连接已关闭")
        engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话

    用作FastAPI依赖项，自动管理会话的生命周期

    Yields:
        AsyncSession: 异步数据库会话
    """
    # 获取会话工厂
    session_factory = await get_async_session_factory()

    # 使用会话工厂创建会话
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"数据库会话异常: {str(e)}", exc_info=True)
            await session.rollback()
            raise
        finally:
            # 会话会在async with块结束时自动关闭
            pass


@asynccontextmanager
async def db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    获取异步数据库会话，用于上下文管理器

    使用方式:
    ```
    async with db_context() as session:
        # 使用会话
        ...
    ```

    Yields:
        AsyncSession: 异步数据库会话
    """
    current_task = asyncio.current_task()
    session_id = current_task.get_name() if current_task else "unknown"
    db_logger = logger.bind(session_id=session_id)

    session_factory = await get_async_session_factory()
    async with session_factory() as session:
        # 数据库会话已创建
        try:
            yield session
            # 如果没有异常发生，提交事务
            await session.commit()
            # 数据库事务已提交
        except APIException:
            # 发生API异常时回滚事务，但保持原始异常
            await session.rollback()
            db_logger.info("业务异常触发事务回滚")
            raise  # 重新抛出原始API异常
        except Exception as e:
            # 发生异常时回滚事务
            await session.rollback()
            db_logger.error(f"数据库操作异常，已回滚: {str(e)}")
            # 如果是API异常，保持原始状态码
            if isinstance(e, APIException):
                raise
            # 其他异常重新抛出
            raise
        finally:
            await session.close()
            # 数据库会话已关闭


# 为兼容性提供的别名
get_async_session = db_context
