#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型仓库模块

处理模型配置的数据库操作
"""

from datetime import UTC, datetime
from typing import List, Optional

from app.db.models.model import Model, ModelCreate, ModelUpdate
from app.db.repositories.base import BaseRepository
from sqlmodel.ext.asyncio.session import AsyncSession


class ModelRepository(BaseRepository[Model]):
    """模型仓库类"""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Model)

    async def get_all(self) -> List[Model]:
        """
        获取所有模型

        Returns:
            List[Model]: 模型列表
        """
        return await self.list(limit=1000)

    async def get_active_models(self) -> List[Model]:
        """
        获取所有激活的模型

        Returns:
            List[Model]: 激活的模型列表
        """
        return await self.list(limit=1000, is_active=True)

    async def create_model(self, model_data: ModelCreate) -> Model:
        """
        创建模型

        Args:
            model_data: 模型创建数据

        Returns:
            Model: 创建的模型
        """
        db_model = Model(
            id=model_data.id,
            display_name=model_data.display_name,
            description=model_data.description,
            is_active=model_data.is_active,
            max_context_tokens=model_data.max_context_tokens,
            has_thinking=model_data.has_thinking,
            default_params=model_data.default_params,
        )
        return await self.create(db_model)

    async def update_model(
        self, model_id: str, model_update: ModelUpdate
    ) -> Optional[Model]:
        """
        更新模型

        Args:
            model_id: 模型ID
            model_update: 模型更新数据

        Returns:
            Optional[Model]: 更新后的模型，如果不存在则为None
        """
        db_model = await self.get(id=model_id)
        if not db_model:
            return None

        # 更新字段
        update_data = model_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_model, key, value)

        # 更新时间
        db_model.updated_at = datetime.now(UTC)

        return await self.update(db_model)

    async def delete_model(self, model_id: str) -> bool:
        """
        删除模型

        Args:
            model_id: 模型ID

        Returns:
            bool: 是否成功删除
        """
        deleted_count = await self.delete(id=model_id)
        return deleted_count > 0

    async def get_by_id(self, model_id: str) -> Optional[Model]:
        """
        通过ID获取模型

        Args:
            model_id: 模型ID

        Returns:
            Optional[Model]: 模型，如果不存在则返回None
        """
        return await self.get(id=model_id)
