#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
消息模型定义
使用SQLModel简化SQLAlchemy操作
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from app.db.models.chat import Chat
from sqlalchemy import Column, DateTime, ForeignKey, Index
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.file import File
    from app.db.models.model import Model


class MessageRole(str, Enum):
    """消息角色枚举"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class MessageStatus(str, Enum):
    """消息状态枚举"""

    COMPLETED = "completed"
    ERROR = "error"
    PENDING = "pending"


# 基础模型
class MessageBase(SQLModel):
    """消息基础模型"""

    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    status: MessageStatus = Field(
        default=MessageStatus.COMPLETED, description="消息状态"
    )
    model_id: Optional[str] = Field(default=None, description="使用模型ID")


# 数据库表模型
class Message(MessageBase, table=True):
    """消息数据库模型"""

    __tablename__ = "messages"  # type: ignore

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True, description="消息ID"
    )
    chat_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("chats.id")), description="聊天会话ID"
    )
    position: int = Field(default=0, description="消息在对话中的位置序号")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC)),
        description="更新时间",
    )
    model_id: Optional[str] = Field(
        default=None,
        sa_column=Column(ForeignKey("models.id")),
        description="使用模型ID",
    )

    chat: Chat = Relationship(back_populates="messages")
    files: List["File"] = Relationship(
        back_populates="message",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    model: Optional["Model"] = Relationship()

    __table_args__ = (Index("ix_messages_chat_id", "chat_id"),)

    def __repr__(self) -> str:
        return f"<Message {self.id} ({self.role})>"


# 操作模型
class MessageCreate(MessageBase):
    """消息创建模型"""

    chat_id: uuid.UUID = Field(..., description="聊天会话ID")


class MessageUpdate(SQLModel):
    """消息更新模型"""

    content: Optional[str] = Field(None, description="消息内容")
    status: Optional[MessageStatus] = Field(None, description="消息状态")


class MessageRead(MessageBase):
    """消息读取模型"""

    id: uuid.UUID = Field(..., description="消息ID")
    chat_id: uuid.UUID = Field(..., description="聊天会话ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
