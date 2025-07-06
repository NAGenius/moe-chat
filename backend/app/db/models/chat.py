#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天会话模型定义
使用SQLModel简化SQLAlchemy操作
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, List, Optional

from app.db.models.user import User
from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    # from app.db.models.model import Model
    from app.db.models.message import Message


# 基础模型
class ChatBase(SQLModel):
    """聊天会话基础模型"""

    title: str = Field(..., max_length=255, description="会话标题")


# 数据库表模型
class Chat(ChatBase, table=True):
    """聊天会话数据库模型"""

    __tablename__ = "chats"  # type: ignore

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True, description="会话ID"
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id")), description="用户ID"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC)),
        description="最后更新时间",
    )

    user: User = Relationship(back_populates="chats")
    messages: List["Message"] = Relationship(
        back_populates="chat",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "Message.created_at",
        },
    )

    __table_args__ = (
        Index("ix_chats_user_id", "user_id"),
        Index("ix_chats_updated_at", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Chat {self.title}>"

    @property
    def message_count(self) -> int:
        """获取会话消息数量"""
        return len(self.messages) if self.messages else 0

    @property
    def last_message(self) -> Optional["Message"]:
        """获取最后一条消息"""
        if self.messages:
            return max(self.messages, key=lambda m: m.created_at)
        return None


# 操作模型
class ChatCreate(ChatBase):
    """聊天会话创建模型"""

    user_id: uuid.UUID = Field(..., description="用户ID")


class ChatUpdate(SQLModel):
    """聊天会话更新模型"""

    title: Optional[str] = Field(None, max_length=255, description="会话标题")


class ChatRead(ChatBase):
    """聊天会话读取模型"""

    id: uuid.UUID = Field(..., description="会话ID")
    user_id: uuid.UUID = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="最后更新时间")
    message_count: int = Field(0, description="消息数量")
