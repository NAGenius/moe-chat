#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件模型定义
使用SQLModel简化SQLAlchemy操作
"""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.user import User


# 基础模型
class FileBase(SQLModel):
    """文件基础模型"""

    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小（字节）")


# 数据库表模型
class File(FileBase, table=True):
    """文件数据库模型"""

    __tablename__ = "files"  # type: ignore

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True, description="文件ID"
    )
    file_path: str = Field(description="存储路径")
    user_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("users.id")), description="上传用户ID"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="上传时间",
    )
    message_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column(ForeignKey("messages.id")),
        description="关联消息ID",
    )

    user: "User" = Relationship(back_populates="files")
    message: Optional["Message"] = Relationship(back_populates="files")

    def __repr__(self) -> str:
        return f"<File {self.filename}>"


# 操作模型
class FileCreate(FileBase):
    """文件创建模型"""

    file_path: str = Field(..., description="存储路径")
    user_id: uuid.UUID = Field(..., description="上传用户ID")
    message_id: Optional[uuid.UUID] = Field(default=None, description="关联消息ID")


class FileUpdate(SQLModel):
    """文件更新模型"""

    filename: Optional[str] = Field(None, description="文件名")
    message_id: Optional[uuid.UUID] = Field(None, description="关联消息ID")


class FileRead(FileBase):
    """文件读取模型"""

    id: uuid.UUID = Field(..., description="文件ID")
    file_path: str = Field(..., description="存储路径")
    user_id: uuid.UUID = Field(..., description="上传用户ID")
    created_at: datetime = Field(..., description="上传时间")
    message_id: Optional[uuid.UUID] = Field(None, description="关联消息ID")
