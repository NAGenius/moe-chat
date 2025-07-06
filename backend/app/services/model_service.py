#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型服务模块

处理与大语言模型的交互
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from app.config import settings
from app.db.database import get_db
from app.db.models.model import Model
from app.db.repositories.model import ModelRepository
from app.db.schemas.dto.output.model_dto import ModelOperationResultDTO
from app.services.cache_service import CacheService
from app.utils.exceptions import (
    GatewayTimeoutException,
    InternalServerErrorException,
    NotFoundException,
    ServiceUnavailableException,
)
from app.utils.logger import get_logger
from app.utils.redis_client import RedisClient, get_redis
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

# 获取日志记录器
logger = get_logger(__name__)


class ModelService:
    """模型服务客户端 - 适配vLLM的OpenAI兼容API"""

    def __init__(
        self, session: AsyncSession, redis_client: Optional[RedisClient] = None
    ):
        """
        初始化模型服务客户端

        Args:
            session: 数据库会话
            redis_client: Redis客户端，用于缓存
        """
        self.session = session
        try:
            self.model_repository: Optional[ModelRepository] = ModelRepository(session)
        except Exception as e:
            logger.error(f"初始化ModelRepository失败: {str(e)}")
            self.model_repository = None

        # 获取所有服务URL
        self.service_urls = settings.MODEL_SERVICE_URLS
        self.default_url = settings.DEFAULT_SERVICE_URL

        # 创建通用客户端
        self.timeout = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
        self.client = httpx.AsyncClient(timeout=self.timeout)

        logger.info(f"模型服务客户端初始化，可用服务数量: {len(self.service_urls)}")
        for url in self.service_urls:
            logger.info(f"服务URL: {url}")

        self.heartbeat_interval = 15  # 心跳检测间隔（秒）
        self.model_status: Dict[str, bool] = {}  # 存储每个模型的状态
        self._heartbeat_task: Optional[asyncio.Task[None]] = None  # 心跳检测任务

        # 初始化缓存服务
        if redis_client:
            self.cache_service = CacheService(redis_client)
            # 模型服务缓存已初始化

    async def start_heartbeat_task(self) -> None:
        """
        启动心跳检测任务
        """
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("模型心跳检测任务已启动")

    async def _heartbeat_loop(self) -> None:
        """
        心跳检测循环
        """
        try:
            while True:
                try:
                    await self._perform_heartbeat_check()
                except Exception as e:
                    logger.error(f"心跳检测周期执行错误: {str(e)}")

                # 等待下一次心跳检测
                await asyncio.sleep(self.heartbeat_interval)
        except asyncio.CancelledError:
            logger.info("模型心跳检测任务已取消")
        except Exception as e:
            logger.error(f"模型心跳检测异常: {str(e)}")
            # 重新启动心跳检测
            self._heartbeat_task = None
            await asyncio.sleep(5)  # 等待一段时间后重试
            await self.start_heartbeat_task()

    async def _perform_heartbeat_check(self) -> None:
        """
        执行一次心跳检测
        """
        from app.db.database import db_context

        async with db_context() as session:
            # 创建临时仓库
            temp_repo = ModelRepository(session)

            # 获取所有模型
            models = await temp_repo.get_all()

            # 检查每个模型的心跳
            for model in models:
                await self._check_single_model_heartbeat(model, temp_repo)

    async def _check_single_model_heartbeat(
        self, model: Model, temp_repo: ModelRepository
    ) -> None:
        """
        检查单个模型的心跳状态
        """
        # 获取模型对应的服务URL
        service_url = model.service_url or self.default_url

        # 检查模型是否存在于该服务
        is_available = await self._check_model_availability(model.id, service_url)

        # 如果状态发生变化，更新数据库
        if model.is_active != is_available:
            await self._update_model_status(model, is_available, temp_repo)

    async def _check_model_availability(self, model_id: str, service_url: str) -> bool:
        """
        检查模型在指定服务中的可用性
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service_url}/v1/models")
                if response.status_code == 200:
                    models_data = response.json().get("data", [])
                    for model_data in models_data:
                        if model_data.get("id") == model_id:
                            return True
            return False
        except Exception as e:
            logger.error(f"检查模型 {model_id} 心跳失败: {str(e)}")
            return False

    async def _update_model_status(
        self, model: Model, is_available: bool, temp_repo: ModelRepository
    ) -> None:
        """
        更新模型状态
        """
        model.is_active = is_available
        model.updated_at = datetime.now(UTC)
        await temp_repo.update(model)

        if is_available:
            logger.info(f"模型 {model.id} 恢复可用")
        else:
            logger.warning(f"模型 {model.id} 不可用")

    async def check_health(self, url: Optional[str] = None) -> bool:
        """
        检查模型服务健康状态

        Args:
            url: 服务URL，为None则检查默认服务

        Returns:
            bool: 是否健康
        """
        try:
            if url:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{url}/health")
                    return response.status_code == 200

            # 检查默认服务
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.default_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"模型服务健康检查失败: {str(e)}")
            return False

    async def get_models_from_service(
        self, url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        从模型服务获取可用模型列表

        Args:
            url: 服务URL，为None则从所有已配置的服务获取

        Returns:
            List[Dict[str, Any]]: 模型原始数据列表
        """
        results = []

        # 如果指定了URL，只查询该服务
        if url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(f"{url}/v1/models")
                    response.raise_for_status()
                    data = response.json()

                    models_data = data.get("data", [])
                    # 添加服务URL
                    for model in models_data:
                        model["service_url"] = url

                    results.extend(models_data)
            except Exception as e:
                logger.error(f"获取服务 {url} 模型列表失败: {str(e)}")

        else:
            # 查询所有已配置的服务
            for url in self.service_urls:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.get(f"{url}/v1/models")
                        response.raise_for_status()
                        data = response.json()

                        models_data = data.get("data", [])
                        # 添加服务URL
                        for model in models_data:
                            model["service_url"] = url

                        results.extend(models_data)
                except Exception as e:
                    logger.error(f"获取服务 {url} 模型列表失败: {str(e)}")

        return results

    async def generate(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        生成文本（非流式）

        Args:
            model_id: 模型ID
            messages: 消息列表
            temperature: 温度
            top_p: Top-p采样
            max_tokens: 最大生成token数
            stop: 停止序列

        Returns:
            Dict[str, Any]: 生成结果
        """
        try:
            # 获取模型对应的服务URL
            service_url = await self.get_model_service_url(model_id)

            payload = {
                "model": model_id,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "stream": False,
            }
            if max_tokens:
                payload["max_tokens"] = max_tokens
            if stop:
                payload["stop"] = stop

            response = await self.client.post(
                f"{service_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPError as e:
            logger.error(f"生成文本失败: {str(e)}")
            raise ServiceUnavailableException(f"模型服务不可用: {str(e)}")

    async def generate_stream(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        top_p: float = 1.0,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        生成文本（流式）并直接处理vLLM的响应格式

        Args:
            model_id: 模型ID
            messages: 消息列表
            temperature: 温度
            top_p: Top-p采样
            max_tokens: 最大生成token数
            stop: 停止序列

        Yields:
            str: 文本增量
        """
        try:
            # 准备请求负载
            payload = self._prepare_stream_payload(
                model_id, messages, temperature, top_p, max_tokens, stop
            )

            logger.info(f"开始流式生成，模型: {model_id}")

            # 获取模型对应的服务URL
            service_url = await self.get_model_service_url(model_id)
            # 模型服务URL已设置

            # 检查服务健康状态
            await self._check_service_health(service_url)

            # 执行流式请求
            async for content in self._execute_stream_request(service_url, payload):
                yield content

        except (
            ServiceUnavailableException,
            NotFoundException,
            InternalServerErrorException,
            GatewayTimeoutException,
        ):
            # 直接重新抛出自定义异常
            raise
        except Exception as e:
            logger.error(f"流式生成文本失败: {str(e)}", exc_info=True)
            raise InternalServerErrorException("生成文本时发生错误，请稍后再试")

    def _prepare_stream_payload(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        temperature: float,
        top_p: float,
        max_tokens: Optional[int],
        stop: Optional[List[str]],
    ) -> Dict[str, Any]:
        """
        准备流式请求的负载
        """
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = stop

        return payload

    async def _check_service_health(self, service_url: str) -> None:
        """
        检查服务健康状态
        """
        try:
            health_check = await self.check_health(service_url)
            if not health_check:
                logger.error("模型服务健康检查失败")
                raise ServiceUnavailableException("模型服务不可用，请稍后再试")
        except Exception as e:
            logger.error(f"模型服务健康检查异常: {str(e)}")
            raise ServiceUnavailableException(f"无法连接到模型服务: {str(e)}")

    async def _execute_stream_request(
        self, service_url: str, payload: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        执行流式请求并处理响应
        """
        try:
            async with self.client.stream(
                "POST",
                f"{service_url}/v1/chat/completions",
                json=payload,
                timeout=None,  # 流式请求不设置超时
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    content = self._process_stream_line(line)
                    if content:
                        yield content

        except httpx.ConnectError as e:
            logger.error(f"连接到模型服务失败: {str(e)}")
            raise ServiceUnavailableException(
                "无法连接到模型服务，请确保模型服务正在运行"
            )
        except httpx.ReadTimeout as e:
            logger.error(f"模型服务响应超时: {str(e)}")
            raise GatewayTimeoutException("模型服务响应超时，请稍后再试")
        except httpx.HTTPStatusError as e:
            self._handle_http_status_error(e)

    def _process_stream_line(self, line: str) -> Optional[str]:
        """
        处理流式响应的单行数据
        """
        if not line or line == "data: [DONE]":
            return None

        if line.startswith("data: "):
            line = line[6:]  # 去除"data: "前缀

        try:
            chunk_data = json.loads(line)
            # 提取增量内容
            if chunk_data.get("choices") and len(chunk_data["choices"]) > 0:
                choice = chunk_data["choices"][0]
                if "delta" in choice and "content" in choice["delta"]:
                    delta_content = choice["delta"]["content"]
                    if delta_content:
                        return str(delta_content)
        except json.JSONDecodeError as e:
            logger.error(f"解析流式响应失败: {str(e)}, 原始数据: {line}")

        return None

    def _handle_http_status_error(self, e: httpx.HTTPStatusError) -> None:
        """
        处理HTTP状态错误
        """
        status_code = e.response.status_code
        logger.error(f"模型服务返回错误状态码: {status_code}, 响应: {e.response.text}")

        if status_code == 404:
            raise NotFoundException("请求的模型不存在")
        elif status_code == 503:
            raise ServiceUnavailableException("模型服务暂时不可用，请稍后再试")
        else:
            raise InternalServerErrorException("模型服务出现错误，请稍后再试")

    async def check_model_heartbeat(self, model_id: str) -> bool:
        """
        检查模型服务心跳，通过获取所有模型列表来判断特定模型是否可用

        Args:
            model_id: 模型ID

        Returns:
            bool: 模型是否可用
        """
        try:
            # 获取模型对应的服务URL
            service_url = await self.get_model_service_url(model_id)

            # 从该服务获取模型列表
            models = await self.get_models_from_service(service_url)

            # 检查模型是否在列表中
            for model in models:
                if model.get("id") == model_id:
                    self.model_status[model_id] = True
                    return True

            # 如果模型不在列表中，则标记为不可用
            self.model_status[model_id] = False
            return False
        except Exception as e:
            logger.error(f"检查模型 {model_id} 心跳失败: {str(e)}")
            # 如果出现异常，不要更改之前的状态
            return self.model_status.get(model_id, False)

    async def sync_models_with_service(self) -> ModelOperationResultDTO:
        """从所有模型服务同步模型信息到数据库"""
        try:
            # 从所有模型服务获取模型列表
            service_models = await self.get_models_from_service()
            if not service_models:
                return ModelOperationResultDTO(
                    success=False, message="模型服务未返回有效数据", model_id="all"
                )

            # 处理模型同步
            sync_result = await self._process_model_sync(service_models)

            # 更新缓存
            await self._update_model_cache(sync_result["models"])

            return ModelOperationResultDTO(
                success=True,
                message=(
                    f"成功从模型服务同步数据: 更新{sync_result['updated_count']}个模型, "
                    f"新增{sync_result['added_count']}个模型"
                ),
                model_id="all",
            )
        except Exception as e:
            logger.error(f"同步模型数据异常: {str(e)}")
            return ModelOperationResultDTO(
                success=False, message=f"同步模型数据异常: {str(e)}", model_id="all"
            )

    async def _process_model_sync(
        self, service_models: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """处理模型同步逻辑"""
        updated_count = 0
        added_count = 0
        models = []

        for model_data in service_models:
            model_id = model_data.get("id")
            if not model_id:
                continue

            # 查找数据库中的模型
            if self.model_repository:
                model = await self.model_repository.get_by_id(model_id)
            else:
                model = None

            # 提取模型信息
            model_info = self._extract_model_info(model_data)

            if model:
                # 更新已有模型
                await self._update_existing_model(model, model_info)
                updated_count += 1
            else:
                # 创建新模型
                model = await self._create_new_model(model_id, model_info)
                added_count += 1

            models.append(model)

        return {
            "models": models,
            "updated_count": updated_count,
            "added_count": added_count,
        }

    def _extract_model_info(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """从服务响应中提取模型信息"""
        return {
            "context_length": model_data.get("max_model_len", 4096),
            "service_url": model_data.get("service_url", self.default_url),
        }

    async def _update_existing_model(
        self, model: Model, model_info: Dict[str, Any]
    ) -> None:
        """更新已有模型"""
        model.display_name = model.id
        model.description = f"由vLLM提供的{model.id}模型"
        model.max_context_tokens = model_info["context_length"]
        model.service_url = model_info["service_url"]
        model.updated_at = datetime.now(UTC)
        if self.model_repository:
            await self.model_repository.update(model)
        else:
            raise InternalServerErrorException("模型仓库未初始化")

    async def _create_new_model(
        self, model_id: str, model_info: Dict[str, Any]
    ) -> Model:
        """创建新模型"""
        new_model = Model(
            id=model_id,
            display_name=model_id,
            description=f"由vLLM提供的{model_id}模型",
            is_active=True,
            has_thinking=model_id.lower()
            in [m.lower() for m in settings.THINKING_MODELS],
            max_context_tokens=model_info["context_length"],
            service_url=model_info["service_url"],
            default_params={
                "temperature": 0.7,
                "top_p": 1.0,
            },
        )
        if self.model_repository:
            await self.model_repository.create(new_model)
        else:
            raise InternalServerErrorException("模型仓库未初始化")
        return new_model

    async def _update_model_cache(self, models: List[Model]) -> None:
        """更新模型缓存"""
        if hasattr(self, "cache_service") and self.cache_service:
            await self.cache_service.invalidate_all_models_cache()
            await self.cache_service.cache_all_models(models)
            # 已更新模型缓存

    async def get_models(self) -> List[Model]:
        """
        获取所有模型列表

        首先尝试从缓存获取，如果没有则从数据库获取并缓存

        Returns:
            List[Model]: 模型列表
        """
        try:
            # 尝试从缓存获取
            cached_models = await self._get_models_from_cache()
            if cached_models is not None:
                return cached_models

            # 缓存未命中，从数据库获取
            return await self._get_models_from_database()
        except Exception as e:
            logger.error(f"获取模型列表失败: {str(e)}")
            # 发生异常时，尝试直接从数据库获取
            return await self._fallback_get_models()

    async def _get_models_from_cache(self) -> Optional[List[Model]]:
        """
        从缓存获取模型列表
        """
        if not (hasattr(self, "cache_service") and self.cache_service):
            return None

        # 获取缓存的模型ID列表
        cached_model_ids = await self.cache_service.get_cached_all_model_ids()
        if not cached_model_ids:
            return None

        # 缓存命中，从缓存获取每个模型
        cached_models = []
        missing_ids = []

        for model_id in cached_model_ids:
            model = await self._get_single_cached_model(model_id)
            if model:
                cached_models.append(model)
            else:
                missing_ids.append(model_id)

        # 如果所有模型都命中缓存
        if not missing_ids:
            # 从缓存获取所有模型
            return cached_models

        return None

    async def _get_single_cached_model(self, model_id: str) -> Optional[Model]:
        """
        获取单个缓存的模型
        """
        cached_model = await self.cache_service.get_cached_model(model_id)
        if cached_model:
            # 需要将DTO转换为Model对象
            if self.model_repository:
                model = await self.model_repository.get_by_id(model_id)
                return model
            else:
                return None
        return None

    async def _get_models_from_database(self) -> List[Model]:
        """
        从数据库获取模型列表并缓存
        """
        if self.model_repository:
            models = await self.model_repository.get_all()
        else:
            models = []

        # 缓存模型
        if hasattr(self, "cache_service") and self.cache_service:
            await self.cache_service.cache_all_models(models)

        return models

    async def _fallback_get_models(self) -> List[Model]:
        """
        异常情况下的备用获取方法
        """
        try:
            if self.model_repository:
                return await self.model_repository.get_all()
            else:
                return []
        except Exception as inner_e:
            logger.error(f"从数据库获取模型列表失败: {str(inner_e)}")
            return []

    async def get_model_by_id(self, model_id: str) -> Optional[Model]:
        """
        根据ID获取模型

        Args:
            model_id: 模型ID

        Returns:
            Optional[Model]: 模型，如果不存在则为None
        """
        try:
            # 确保model_repository已初始化
            if self.model_repository is None:
                logger.warning("ModelRepository未初始化，无法获取模型")
                return None

            # 使用repository层获取模型
            model = await self.model_repository.get(id=model_id)
            return model
        except Exception as e:
            logger.error(f"获取模型失败: {str(e)}")
            return None

    async def get_model_service_url(self, model_id: str) -> str:
        """
        根据模型ID获取对应的服务URL

        Args:
            model_id: 模型ID

        Returns:
            str: 服务URL
        """
        try:
            if not self.model_repository:
                return self.default_url

            model = await self.model_repository.get_by_id(model_id)
            if model and model.service_url:
                return model.service_url

            return self.default_url
        except Exception as e:
            logger.error(f"获取模型服务URL失败: {str(e)}")
            return self.default_url

    def update_expert_stats(self, expert_stats: Dict[str, int]) -> None:
        """
        更新MoE专家激活数据

        Args:
            expert_stats: 专家激活统计，格式: {'专家ID': 激活次数}
        """
        if expert_stats and isinstance(expert_stats, dict):
            try:
                # 通过Redis发布专家激活数据，而不是直接更新可视化器
                from app.utils.redis_client import get_redis_sync

                redis_client = get_redis_sync()
                if redis_client is None:
                    logger.warning("Redis客户端未初始化，无法发布专家激活数据")
                    return

                # 将数据序列化为JSON
                data_json = json.dumps(expert_stats)

                # 发布到Redis频道
                redis_client.publish("moe:expert:activation", data_json)
                logger.info(f"已发布专家激活数据到Redis，专家数: {len(expert_stats)}")
            except Exception as e:
                # 仅记录错误，不中断流程
                logger.error(f"发布MoE专家激活数据失败: {str(e)}")


def get_model_service(
    session: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
) -> ModelService:
    """
    获取模型服务实例

    Args:
        session: 数据库会话
        redis_client: Redis客户端

    Returns:
        ModelService: 模型服务实例
    """
    return ModelService(session, redis_client)
