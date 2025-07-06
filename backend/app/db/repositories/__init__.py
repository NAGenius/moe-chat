#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
仓储模块导出
"""

from app.db.repositories.chat import ChatRepository
from app.db.repositories.message import MessageRepository
from app.db.repositories.model import ModelRepository
from app.db.repositories.user import UserRepository
from sqlmodel.ext.asyncio.session import AsyncSession


# 提供获取仓储实例的函数
def get_user_repository(session: AsyncSession) -> UserRepository:
    """获取用户仓储实例"""
    return UserRepository(session)


def get_chat_repository(session: AsyncSession) -> ChatRepository:
    """获取聊天仓储实例"""
    return ChatRepository(session)


def get_message_repository(session: AsyncSession) -> MessageRepository:
    """获取消息仓储实例"""
    return MessageRepository(session)


def get_model_repository(session: AsyncSession) -> ModelRepository:
    """获取模型仓储实例"""
    return ModelRepository(session)


__all__ = [
    "get_user_repository",
    "get_chat_repository",
    "get_message_repository",
    "get_model_repository",
]
