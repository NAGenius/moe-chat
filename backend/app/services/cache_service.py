#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
缓存服务模块

提供数据缓存和管理功能
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TypeVar

from app.db.models.model import Model
from app.db.models.user import User
from app.db.schemas.dto.output.model_dto import ModelDTO
from app.db.schemas.dto.output.user_dto import UserDTO
from app.utils.logger import get_logger
from app.utils.redis_client import RedisClient, get_redis
from fastapi import Depends
from pydantic import BaseModel

# 获取日志记录器
logger = get_logger(__name__)

# 缓存TTL默认值（秒）
DEFAULT_CACHE_TTL = 3600  # 1小时
USER_CACHE_TTL = 1800  # 30分钟
MODEL_CACHE_TTL = 3600  # 1小时
CONTEXT_CACHE_TTL = 1800  # 30分钟
CONTEXT_METADATA_TTL = 3600  # 1小时

# 定义泛型类型变量
T = TypeVar("T", bound=BaseModel)


class CacheService:
    """缓存服务类"""

    def __init__(self, redis_client: RedisClient):
        """
        初始化缓存服务

        Args:
            redis_client: Redis客户端
        """
        self.redis = redis_client
        self.logger = get_logger("app.services.cache")

    async def get_cached_user(self, user_id: str) -> Optional[UserDTO]:
        """
        从缓存获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Optional[UserDTO]: 用户信息，如果缓存中不存在则返回None
        """
        cache_key = f"user:{user_id}"
        cached_data = await self.redis.get(cache_key)

        if not cached_data:
            return None

        try:
            user_dict = json.loads(cached_data)
            return UserDTO.model_validate(user_dict)
        except Exception as e:
            self.logger.error(f"解析缓存的用户数据失败: {str(e)}")
            return None

    async def cache_user(self, user: User) -> None:
        """
        缓存用户信息

        Args:
            user: 用户模型实例
        """
        cache_key = f"user:{user.id}"

        # 转换为DTO以简化存储的数据
        user_dto = UserDTO.model_validate(user)
        user_json = user_dto.model_dump_json()

        await self.redis.set(cache_key, user_json, expire=USER_CACHE_TTL)
        # 用户信息已缓存

    async def invalidate_user_cache(self, user_id: str) -> None:
        """
        使用户缓存失效

        Args:
            user_id: 用户ID
        """
        cache_key = f"user:{user_id}"
        await self.redis.delete(cache_key)
        # 用户缓存已失效

    async def get_cached_model(self, model_id: str) -> Optional[ModelDTO]:
        """
        从缓存获取模型信息

        Args:
            model_id: 模型ID

        Returns:
            Optional[ModelDTO]: 模型信息，如果缓存中不存在则返回None
        """
        cache_key = f"model:{model_id}"
        cached_data = await self.redis.get(cache_key)

        if not cached_data:
            return None

        try:
            model_dict = json.loads(cached_data)
            return ModelDTO.model_validate(model_dict)
        except Exception as e:
            self.logger.error(f"解析缓存的模型数据失败: {str(e)}")
            return None

    async def cache_model(self, model: Model) -> None:
        """
        缓存模型信息

        Args:
            model: 模型实例
        """
        cache_key = f"model:{model.id}"

        try:
            # 将Model对象转换为字典，然后再转换为DTO
            model_dict = {
                "id": model.id,
                "display_name": model.display_name,
                "description": model.description,
                "is_active": model.is_active,
                "max_context_tokens": model.max_context_tokens,
                "has_thinking": model.has_thinking,
                "default_params": model.default_params,
                "created_at": model.created_at,
                "updated_at": model.updated_at,
            }

            # 转换为DTO以简化存储的数据
            model_dto = ModelDTO.model_validate(model_dict)
            model_json = model_dto.model_dump_json()

            await self.redis.set(cache_key, model_json, expire=MODEL_CACHE_TTL)
            # 模型信息已缓存
        except Exception as e:
            self.logger.error(f"缓存模型信息失败: {str(e)}")
            # 失败时不抛出异常，允许程序继续运行

    async def invalidate_model_cache(self, model_id: str) -> None:
        """
        使模型缓存失效

        Args:
            model_id: 模型ID
        """
        cache_key = f"model:{model_id}"
        await self.redis.delete(cache_key)
        # 模型缓存已失效

    async def cache_all_models(self, models: List[Model]) -> None:
        """
        缓存所有模型信息

        Args:
            models: 模型列表
        """
        try:
            # 缓存模型列表的ID
            model_ids = [str(model.id) for model in models]
            cache_key = "models:all"
            await self.redis.set(
                cache_key, json.dumps(model_ids), expire=MODEL_CACHE_TTL
            )

            # 单独缓存每个模型
            for model in models:
                await self.cache_model(model)

            # 所有模型信息已缓存
        except Exception as e:
            self.logger.error(f"缓存所有模型信息失败: {str(e)}")
            # 失败时不抛出异常，允许程序继续运行

    async def get_cached_all_model_ids(self) -> Optional[List[str]]:
        """
        从缓存获取所有模型ID

        Returns:
            Optional[List[str]]: 模型ID列表，如果缓存中不存在则返回None
        """
        cache_key = "models:all"
        cached_data = await self.redis.get(cache_key)

        if not cached_data:
            return None

        try:
            data = json.loads(cached_data)
            if isinstance(data, list) and all(isinstance(item, str) for item in data):
                return data
            return None
        except Exception as e:
            self.logger.error(f"解析缓存的模型ID列表失败: {str(e)}")
            return None

    async def invalidate_all_models_cache(self) -> None:
        """
        使所有模型缓存失效
        """
        # 获取所有模型ID
        model_ids = await self.get_cached_all_model_ids()
        if model_ids:
            # 删除每个模型的缓存
            for model_id in model_ids:
                await self.invalidate_model_cache(model_id)

        # 删除模型列表的缓存
        await self.redis.delete("models:all")
        # 所有模型缓存已失效

    def _generate_context_hash(self, messages: List[Dict[str, str]]) -> str:
        """
        生成消息上下文的哈希值

        Args:
            messages: 消息列表

        Returns:
            str: 上下文哈希值
        """
        # 将消息列表转换为字符串并生成哈希
        context_str = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(context_str.encode("utf-8")).hexdigest()

    async def get_cached_context(
        self, chat_id: str, messages: List[Dict[str, str]]
    ) -> Optional[List[Dict[str, str]]]:
        """
        从缓存获取聊天上下文

        Args:
            chat_id: 聊天ID
            messages: 当前消息列表（用于生成缓存键）

        Returns:
            Optional[List[Dict[str, str]]]: 缓存的上下文，如果不存在则返回None
        """
        context_hash = self._generate_context_hash(messages)
        cache_key = f"context:{chat_id}:{context_hash}"

        cached_data = await self.redis.get(cache_key)
        if not cached_data:
            return None

        try:
            data = json.loads(cached_data)
            if isinstance(data, list):
                return data
            return None
        except Exception as e:
            self.logger.error(f"解析缓存的上下文数据失败: {str(e)}")
            return None

    async def cache_context(
        self,
        chat_id: str,
        messages: List[Dict[str, str]],
        processed_context: List[Dict[str, str]],
    ) -> None:
        """
        缓存聊天上下文

        Args:
            chat_id: 聊天ID
            messages: 原始消息列表
            processed_context: 处理后的上下文
        """
        try:
            context_hash = self._generate_context_hash(messages)
            cache_key = f"context:{chat_id}:{context_hash}"

            context_json = json.dumps(processed_context, ensure_ascii=False)
            await self.redis.set(cache_key, context_json, expire=CONTEXT_CACHE_TTL)

            # 同时缓存元数据，用于快速查找
            metadata_key = f"context_meta:{chat_id}"
            metadata = {
                "last_hash": context_hash,
                "message_count": len(messages),
                "context_count": len(processed_context),
                "cached_at": json.dumps(datetime.now().isoformat()),
            }
            await self.redis.set(
                metadata_key, json.dumps(metadata), expire=CONTEXT_METADATA_TTL
            )

            # 上下文已缓存
        except Exception as e:
            self.logger.error(f"缓存上下文失败: {str(e)}")
            # 失败时不抛出异常，允许程序继续运行

    async def get_context_metadata(self, chat_id: str) -> Optional[Dict[str, Any]]:
        """
        获取上下文缓存元数据

        Args:
            chat_id: 聊天ID

        Returns:
            Optional[Dict[str, Any]]: 元数据，如果不存在则返回None
        """
        metadata_key = f"context_meta:{chat_id}"
        cached_data = await self.redis.get(metadata_key)

        if not cached_data:
            return None

        try:
            data = json.loads(cached_data)
            if isinstance(data, dict):
                return data
            return None
        except Exception as e:
            self.logger.error(f"解析上下文元数据失败: {str(e)}")
            return None

    async def invalidate_context_cache(self, chat_id: str) -> None:
        """
        使聊天上下文缓存失效

        Args:
            chat_id: 聊天ID
        """
        try:
            # 获取元数据以找到所有相关的缓存键
            metadata = await self.get_context_metadata(chat_id)

            # 删除具体的上下文缓存
            if metadata and "last_hash" in metadata:
                context_key = f"context:{chat_id}:{metadata['last_hash']}"
                await self.redis.delete(context_key)

            # 删除元数据
            metadata_key = f"context_meta:{chat_id}"
            await self.redis.delete(metadata_key)

            # 使用模式匹配删除所有相关的上下文缓存
            pattern = f"context:{chat_id}:*"
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)

            # 聊天上下文缓存已失效
        except Exception as e:
            self.logger.error(f"使上下文缓存失效失败: {str(e)}")

    async def cache_truncated_context(
        self,
        chat_id: str,
        model_id: str,
        max_tokens: int,
        truncated_context: List[Dict[str, str]],
    ) -> None:
        """
        缓存截断后的上下文

        Args:
            chat_id: 聊天ID
            model_id: 模型ID
            max_tokens: 最大token数
            truncated_context: 截断后的上下文
        """
        try:
            cache_key = f"truncated_context:{chat_id}:{model_id}:{max_tokens}"
            context_json = json.dumps(truncated_context, ensure_ascii=False)

            await self.redis.set(cache_key, context_json, expire=CONTEXT_CACHE_TTL)

            # 截断上下文已缓存
        except Exception as e:
            self.logger.error(f"缓存截断上下文失败: {str(e)}")

    async def get_cached_truncated_context(
        self, chat_id: str, model_id: str, max_tokens: int
    ) -> Optional[List[Dict[str, str]]]:
        """
        获取缓存的截断上下文

        Args:
            chat_id: 聊天ID
            model_id: 模型ID
            max_tokens: 最大token数

        Returns:
            Optional[List[Dict[str, str]]]: 缓存的截断上下文，如果不存在则返回None
        """
        cache_key = f"truncated_context:{chat_id}:{model_id}:{max_tokens}"
        cached_data = await self.redis.get(cache_key)

        if not cached_data:
            return None

        try:
            data = json.loads(cached_data)
            if isinstance(data, list):
                return data
            return None
        except Exception as e:
            self.logger.error(f"解析缓存的截断上下文失败: {str(e)}")
            return None


def get_cache_service(redis_client: RedisClient = Depends(get_redis)) -> CacheService:
    """
    获取缓存服务实例

    Args:
        redis_client: Redis客户端

    Returns:
        CacheService: 缓存服务实例
    """
    return CacheService(redis_client)
