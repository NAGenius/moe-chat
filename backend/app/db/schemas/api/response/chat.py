#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天相关API响应模型
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.db.models.message import MessageStatus
from pydantic import BaseModel, Field


class ChatResponse(BaseModel):
    """聊天会话信息响应"""

    id: UUID = Field(..., description="聊天会话ID")
    title: str = Field(..., description="会话标题")


class ChatListItemResponse(BaseModel):
    """聊天列表项响应"""

    chat_id: str = Field(..., description="聊天会话ID")
    title: str = Field(..., description="会话标题")
    updated_at: datetime = Field(..., description="更新时间")


class ChatListResponse(BaseModel):
    """聊天列表响应"""

    chats: List[ChatListItemResponse] = Field(..., description="聊天会话列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")


class MessageResponse(BaseModel):
    """消息响应"""

    id: UUID = Field(..., description="消息ID")
    role: str = Field(..., description="角色：system, user, assistant")
    content: str = Field(..., description="消息内容")
    model_id: Optional[str] = Field(None, description="使用的模型ID")
    created_at: datetime = Field(..., description="创建时间")
    status: MessageStatus = Field(
        ..., description="消息状态：completed, error, pending"
    )
    position: int = Field(..., description="消息在对话中的位置序号")


class MessageListResponse(BaseModel):
    """消息列表响应"""

    messages: List[MessageResponse] = Field(..., description="消息列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")


class ChatCreateResponse(BaseModel):
    """创建聊天响应"""

    chat_id: str = Field(..., description="聊天会话ID")


class MessageCreateResponse(BaseModel):
    """创建消息响应"""

    content: Optional[str] = Field(None, description="助手回复内容（非流式模式）")
