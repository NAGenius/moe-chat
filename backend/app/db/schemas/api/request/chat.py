#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天相关API请求模型
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ChatCreateRequest(BaseModel):
    """聊天会话创建请求"""

    title: str = Field(..., description="会话标题")


class ChatUpdateRequest(BaseModel):
    """聊天会话更新请求"""

    title: str = Field(..., description="会话标题")


class MessageCreateRequest(BaseModel):
    """消息创建请求"""

    content: str = Field(..., description="消息内容")
    model_id: str = Field(..., description="使用的模型ID")
    file_ids: Optional[List[UUID]] = Field(default=None, description="附件文件ID数组")
