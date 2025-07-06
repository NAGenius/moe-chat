#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户模型定义
使用SQLModel简化SQLAlchemy操作
"""

import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.db.models.chat import Chat
    from app.db.models.file import File


class UserRole(str, Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"


# 基础模型
class UserBase(SQLModel):
    """用户基础模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")
    full_name: Optional[str] = Field(default=None, description="展示名字")
    is_active: bool = Field(default=True, description="是否禁用")
    role: UserRole = Field(default=UserRole.USER, description="用户角色")
    system_prompt: Optional[str] = Field(
        default="你是一个有用的助手", description="系统提示词"
    )


# 数据库表模型
class User(UserBase, table=True):
    """用户数据库模型"""

    __tablename__ = "users"  # type: ignore

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, primary_key=True, index=True, description="用户ID"
    )
    hashed_password: str = Field(description="加密后的密码")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="更新时间",
    )
    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True)),
        description="最后登录时间",
    )

    chats: List["Chat"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    files: List["File"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"

    @property
    def is_admin(self) -> bool:
        """判断用户是否为管理员"""
        return self.role == UserRole.ADMIN


# 操作模型
class UserCreate(UserBase):
    """用户创建模型"""

    password: str = Field(..., min_length=6, max_length=100, description="密码")


class UserUpdate(SQLModel):
    """用户更新模型"""

    username: Optional[str] = Field(
        None, min_length=3, max_length=50, description="用户名"
    )
    email: Optional[str] = Field(None, description="邮箱")
    full_name: Optional[str] = Field(None, description="展示名字")
    is_active: Optional[bool] = Field(None, description="是否禁用")
    role: Optional[UserRole] = Field(None, description="用户角色")
    password: Optional[str] = Field(
        None, min_length=6, max_length=100, description="密码"
    )


class UserRead(UserBase):
    """用户读取模型"""

    id: uuid.UUID = Field(..., description="用户ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")
