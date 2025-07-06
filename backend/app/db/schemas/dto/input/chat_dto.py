#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天相关输入DTO
"""

import uuid
from typing import List, Optional

from app.db.models.message import MessageRole, MessageStatus
from pydantic import BaseModel, Field


class ChatCreateDTO(BaseModel):
    """聊天会话创建DTO"""

    user_id: uuid.UUID = Field(..., description="用户ID")
    title: str = Field(..., description="会话标题")


class ChatUpdateDTO(BaseModel):
    """聊天会话更新DTO"""

    title: Optional[str] = Field(None, description="会话标题")


class ChatQueryDTO(BaseModel):
    """聊天会话查询DTO"""

    user_id: uuid.UUID = Field(..., description="用户ID")
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(20, ge=1, le=100, description="每页数量")


class MessageCreateDTO(BaseModel):
    """消息创建DTO"""

    user_id: uuid.UUID = Field(..., description="用户ID")
    chat_id: uuid.UUID = Field(..., description="聊天会话ID")
    role: MessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    status: MessageStatus = Field(
        default=MessageStatus.COMPLETED, description="消息状态"
    )
    model_id: Optional[str] = Field(default=None, description="使用的模型ID")
    file_ids: Optional[List[uuid.UUID]] = Field(
        default=None, description="附件文件ID数组"
    )


class MessageQueryDTO(BaseModel):
    """消息查询DTO"""

    user_id: uuid.UUID = Field(..., description="用户ID")
    chat_id: uuid.UUID = Field(..., description="聊天会话ID")
    page: int = Field(1, ge=1, description="页码")
    limit: int = Field(50, ge=1, le=100, description="每页数量")
