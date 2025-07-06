#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型相关API端点
"""

from app.db.schemas.api.response.base import ResponseBase
from app.db.schemas.api.response.model import ModelListResponse, ModelResponse
from app.services.model_service import ModelService, get_model_service
from fastapi import APIRouter, Depends, status

router = APIRouter()


@router.get("", response_model=ResponseBase[ModelListResponse])
async def get_models(
    model_service: ModelService = Depends(get_model_service),
) -> ResponseBase[ModelListResponse]:
    """获取模型列表"""
    models = await model_service.get_models()

    # 将模型列表转换为响应格式，只包含活跃的模型
    model_items = [
        ModelResponse(
            id=model.id,
            display_name=model.display_name,
            description=model.description,
            is_active=model.is_active,
            has_thinking=model.has_thinking,
            max_context_tokens=model.max_context_tokens,
        )
        for model in models
        if model.is_active
    ]

    return ResponseBase[ModelListResponse](
        code=status.HTTP_200_OK,
        message="请求成功",
        data=ModelListResponse(models=model_items),
    )
