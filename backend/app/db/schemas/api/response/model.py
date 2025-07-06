#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型相关API响应模型
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelResponse(BaseModel):
    """模型信息响应"""

    id: str = Field(..., description="模型ID")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    is_active: bool = Field(..., description="是否可用")
    has_thinking: bool = Field(..., description="是否支持思考过程")
    max_context_tokens: Optional[int] = Field(None, description="最大上下文长度")


class ModelListResponse(BaseModel):
    """模型列表响应"""

    models: List[ModelResponse] = Field(..., description="模型列表")
