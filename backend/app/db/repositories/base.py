#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础仓库模块

提供通用的数据库操作
"""

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, delete, func, select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    基础仓库类

    提供通用的CRUD操作
    """

    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        初始化仓库

        Args:
            session: 数据库会话
            model: 模型类
        """
        self.model = model
        self.session = session

    async def get(self, **filters: Any) -> Optional[T]:
        """
        根据指定条件获取单个记录

        Args:
            **filters: 过滤条件，键值对形式

        Returns:
            Optional[T]: 记录对象，如果不存在则为None
        """
        query = select(self.model)

        # 添加过滤条件
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(getattr(self.model, key) == value)

            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, limit: int = 100, offset: int = 0, **filters: Any) -> List[T]:
        """
        获取记录列表

        Args:
            limit: 返回的最大记录数
            offset: 偏移量
            **filters: 过滤条件，键值对形式

        Returns:
            List[T]: 记录列表
        """
        query = select(self.model)

        # 添加过滤条件
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(getattr(self.model, key) == value)

            query = query.where(and_(*conditions))

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        """
        获取记录总数

        Args:
            **filters: 过滤条件，键值对形式

        Returns:
            int: 记录总数
        """
        query = select(func.count()).select_from(self.model)

        # 添加过滤条件
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(getattr(self.model, key) == value)

            query = query.where(and_(*conditions))

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def create(self, obj_in: SQLModel) -> T:
        """
        创建对象

        Args:
            obj_in: 输入对象

        Returns:
            T: 创建的对象
        """
        db_obj = self.model.model_validate(obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: T) -> T:
        """
        更新对象

        Args:
            db_obj: 数据库对象

        Returns:
            T: 更新后的对象
        """
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, **filters: Any) -> int:
        """
        删除对象

        Args:
            **filters: 过滤条件，键值对形式

        Returns:
            int: 删除的记录数
        """
        # 构建过滤条件
        conditions = []
        for key, value in filters.items():
            conditions.append(getattr(self.model, key) == value)

        # 构建删除语句
        statement = delete(self.model).where(and_(*conditions))

        # 执行删除操作
        result = await self.session.execute(statement)
        await self.session.commit()

        return getattr(result, "rowcount", 0) or 0
