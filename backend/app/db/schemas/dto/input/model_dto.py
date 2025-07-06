#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型服务层DTO输入模型
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ModelCreateDTO(BaseModel):
    """模型创建输入DTO"""

    id: str = Field(..., description="模型ID")
    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    is_active: bool = Field(True, description="是否激活")
    max_context_tokens: int = Field(4096, description="最大上下文token数")
    has_thinking: bool = Field(False, description="是否支持思考过程")
    default_params: Optional[Dict[str, Any]] = Field(None, description="默认参数")


class ModelUpdateDTO(BaseModel):
    """模型更新输入DTO"""

    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    max_context_tokens: Optional[int] = Field(None, description="最大上下文token数")
    has_thinking: Optional[bool] = Field(None, description="是否支持思考过程")
    default_params: Optional[Dict[str, Any]] = Field(None, description="默认参数")


class ModelQueryDTO(BaseModel):
    """模型查询输入DTO"""

    include_inactive: bool = Field(False, description="是否包含未激活的模型")
