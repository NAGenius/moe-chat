#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天服务层DTO输出模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.db.models.message import MessageStatus
from pydantic import BaseModel


class MessageDTO(BaseModel):
    """消息DTO，符合API文档中的定义"""

    id: UUID
    role: str
    content: str
    model_id: Optional[str] = None
    created_at: datetime
    status: MessageStatus
    position: int = 0
    # 下面的字段不在API文档中，但在内部服务中使用
    chat_id: Optional[UUID] = None
    updated_at: Optional[datetime] = None
    model_params: Optional[Dict[str, Any]] = None


class ChatDTO(BaseModel):
    """聊天DTO"""

    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_message: Optional[MessageDTO] = None


class ChatListItemDTO(BaseModel):
    """聊天列表项DTO，符合API文档的格式"""

    id: UUID
    title: str
    updated_at: datetime


class ChatListDTO(BaseModel):
    """聊天列表DTO"""

    chats: List[ChatListItemDTO]
    total: int
    page: int
    limit: int


class MessageListDTO(BaseModel):
    """消息列表DTO"""

    messages: List[MessageDTO]
    total: int
    page: int
    limit: int


class ChatDetailDTO(BaseModel):
    """聊天详情DTO"""

    id: UUID
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
