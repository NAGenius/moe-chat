#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户相关API响应模型
"""

from typing import Optional

from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """用户信息响应"""

    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, description="用户全名")
    role: str = Field(..., description="用户角色")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
