#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型服务层DTO输出模型
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ModelDTO(BaseModel):
    """模型DTO"""

    id: str
    display_name: str
    description: Optional[str] = None
    is_active: bool
    max_context_tokens: int
    has_thinking: bool
    default_params: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ModelsListDTO(BaseModel):
    """模型列表DTO"""

    models: List[ModelDTO]
    total: int


class ModelOperationResultDTO(BaseModel):
    """模型操作结果DTO"""

    success: bool
    message: str
    model_id: str
