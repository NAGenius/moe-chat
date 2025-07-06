#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Redis客户端模块

提供Redis连接和操作，包含自动重连机制和错误处理
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, cast

import redis.asyncio as redis
from app.config import settings
from app.utils.exceptions import (
    InternalServerErrorException,
    ServiceUnavailableException,
)
from app.utils.logger import get_logger
from fastapi import Depends

logger = get_logger("app.redis")

# Redis连接池
_redis_pool: Optional[redis.ConnectionPool] = None
# 重连尝试次数与间隔从配置中读取
MAX_RETRY_COUNT = settings.REDIS_MAX_RETRY_COUNT
RETRY_INTERVAL = settings.REDIS_RETRY_INTERVAL


async def init_redis_pool() -> redis.ConnectionPool:
    """
    初始化Redis连接池，带重试机制

    Returns:
        redis.ConnectionPool: Redis连接池
    """
    global _redis_pool

    if _redis_pool is None:
        redis_logger = logger.bind(component="connection_pool")
        retry_count = 0
        while retry_count < MAX_RETRY_COUNT:
            try:
                # 创建Redis连接池 - 使用settings中的配置
                _redis_pool = redis.ConnectionPool.from_url(
                    url=settings.REDIS_URL,
                    decode_responses=True,  # 自动将字节解码为字符串
                    max_connections=settings.REDIS_MAX_CONNECTIONS,
                    socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                    socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                    socket_keepalive=True,  # 保持连接
                    health_check_interval=settings.REDIS_HEALTH_CHECK_INTERVAL,
                )

                # 测试连接
                test_client = redis.Redis(connection_pool=_redis_pool)
                await test_client.ping()
                await test_client.close()

                redis_url = settings.REDIS_URL.split("@")[-1]
                redis_logger.success(f"Redis连接池初始化成功: {redis_url}")
                break
            except (redis.ConnectionError, redis.RedisError) as e:
                retry_count += 1
                if retry_count >= MAX_RETRY_COUNT:
                    redis_logger.error(f"Redis连接失败，已达到最大重试次数: {str(e)}")
                    raise ServiceUnavailableException("Redis服务不可用，请联系管理员")
                redis_logger.warning(
                    f"Redis连接失败，尝试重连 ({retry_count}/{MAX_RETRY_COUNT}): {str(e)}"
                )
                await asyncio.sleep(RETRY_INTERVAL)
            except Exception as e:
                redis_logger.exception(f"Redis连接池初始化异常: {str(e)}")
                raise InternalServerErrorException("Redis初始化异常，请联系管理员")

    if _redis_pool is None:
        raise InternalServerErrorException("Redis连接池初始化失败")
    return _redis_pool


async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    获取Redis客户端

    用作FastAPI依赖项，自动管理客户端的生命周期

    Yields:
        redis.Redis: Redis客户端
    """
    pool = await init_redis_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.close()


async def close_redis_pool() -> None:
    """
    关闭Redis连接池

    应用关闭时清理Redis资源
    """
    global _redis_pool

    if _redis_pool:
        await _redis_pool.disconnect()
        logger.info("Redis连接池已关闭")
        _redis_pool = None


class RedisClient:
    """Redis客户端类，提供各种Redis操作的封装"""

    def __init__(self, redis_client: redis.Redis):
        """
        初始化Redis客户端

        Args:
            redis_client: Redis客户端
        """
        self.redis = redis_client
        self.logger = get_logger("app.redis.client")
        self.key_prefix = settings.REDIS_KEY_PREFIX

    def _get_key(self, key: str) -> str:
        """
        获取带前缀的键名

        Args:
            key: 原始键名

        Returns:
            str: 带前缀的键名
        """
        return f"{self.key_prefix}{key}"

    async def ping(self) -> bool:
        """
        测试Redis连接

        Returns:
            bool: 连接是否正常
        """
        try:
            ping_result = self.redis.ping()
            if hasattr(ping_result, "__await__"):
                return cast(bool, await ping_result)
            else:
                return cast(bool, ping_result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis ping失败: {str(e)}")
            return False

    async def get(self, key: str) -> Optional[str]:
        """
        获取键值

        Args:
            key: 键名

        Returns:
            Optional[str]: 键值，如果不存在则为None
        """
        try:
            prefixed_key = self._get_key(key)
            get_result = self.redis.get(prefixed_key)
            if hasattr(get_result, "__await__"):
                value = cast(Optional[str], await get_result)
            else:
                value = cast(Optional[str], get_result)
            # Redis获取键值
            return value
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis获取键值失败 [{key}]: {str(e)}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        设置键值

        Args:
            key: 键名
            value: 键值
            expire: 过期时间（秒）
            nx: 仅在键不存在时设置
            xx: 仅在键已存在时设置

        Returns:
            bool: 是否设置成功
        """
        try:
            prefixed_key = self._get_key(key)
            kwargs = self._build_set_kwargs(expire, nx, xx)

            self._log_set_operation(prefixed_key, expire)

            result = await self._execute_set_operation(prefixed_key, value, kwargs)

            if result and expire is not None:
                await self._verify_ttl(prefixed_key)

            return result
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis设置键值失败 [{key}]: {str(e)}")
            return False
        except Exception as e:
            self.logger.exception(f"Redis设置键值时发生未知异常 [{key}]: {str(e)}")
            return False

    def _build_set_kwargs(
        self, expire: Optional[int], nx: bool, xx: bool
    ) -> Dict[str, Any]:
        """构建 set 操作的参数"""
        kwargs: Dict[str, Any] = {}
        if expire is not None:
            kwargs["ex"] = expire
        if nx:
            kwargs["nx"] = True
        if xx:
            kwargs["xx"] = True
        return kwargs

    def _log_set_operation(self, prefixed_key: str, expire: Optional[int]) -> None:
        """记录 set 操作日志"""
        # Redis设置键值

    async def _execute_set_operation(
        self, prefixed_key: str, value: str, kwargs: Dict[str, Any]
    ) -> bool:
        """执行 set 操作"""
        set_result = self.redis.set(prefixed_key, value, **kwargs)
        if hasattr(set_result, "__await__"):
            return cast(bool, await set_result)
        else:
            return cast(bool, set_result)

    async def _verify_ttl(self, prefixed_key: str) -> None:
        """验证 TTL 设置"""
        ttl_result = self.redis.ttl(prefixed_key)
        if hasattr(ttl_result, "__await__"):
            ttl = cast(int, await ttl_result)
        else:
            ttl = cast(int, ttl_result)

        if ttl <= 0:
            self.logger.warning(
                f"Redis键值设置成功但TTL异常: {prefixed_key}, TTL={ttl}"
            )
        else:
            # Redis键值设置成功
            pass

    async def delete(self, key: str) -> int:
        """
        删除键

        Args:
            key: 键名

        Returns:
            int: 删除的键数量
        """
        try:
            prefixed_key = self._get_key(key)
            result = self.redis.delete(prefixed_key)
            if hasattr(result, "__await__"):
                final_result = cast(int, await result)
            else:
                final_result = cast(int, result)
            # Redis删除键
            return final_result
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis删除键失败 [{key}]: {str(e)}")
            return 0

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            bool: 键是否存在
        """
        try:
            prefixed_key = self._get_key(key)
            result = self.redis.exists(prefixed_key)
            if hasattr(result, "__await__"):
                return cast(bool, await result) > 0
            else:
                return cast(bool, result) > 0
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis检查键存在失败 [{key}]: {str(e)}")
            return False

    async def keys(self, pattern: str = "*") -> List[str]:
        """
        获取匹配模式的键列表

        Args:
            pattern: 匹配模式，默认为"*"（所有键）

        Returns:
            List[str]: 匹配的键列表（已去除前缀）
        """
        try:
            # 添加前缀到模式
            prefixed_pattern = self._get_key(pattern)
            result = self.redis.keys(prefixed_pattern)
            if hasattr(result, "__await__"):
                keys = cast(List[str], await result)
            else:
                keys = cast(List[str], result)

            # 去除前缀返回原始键名
            prefix_len = len(self.key_prefix)
            return [key[prefix_len:] for key in keys if key.startswith(self.key_prefix)]
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis获取键列表失败 [{pattern}]: {str(e)}")
            return []

    async def ttl(self, key: str) -> int:
        """
        获取键的剩余生存时间

        Args:
            key: 键名

        Returns:
            int: 剩余生存时间（秒），-1表示永久，-2表示不存在
        """
        try:
            prefixed_key = self._get_key(key)
            result = self.redis.ttl(prefixed_key)
            if hasattr(result, "__await__"):
                return cast(int, await result)
            else:
                return cast(int, result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis获取键剩余生存时间失败 [{key}]: {str(e)}")
            return -2

    async def expire(self, key: str, seconds: int) -> bool:
        """
        设置键过期时间

        Args:
            key: 键名
            seconds: 过期时间（秒）

        Returns:
            bool: 是否设置成功
        """
        try:
            prefixed_key = self._get_key(key)
            result = self.redis.expire(prefixed_key, seconds)
            if hasattr(result, "__await__"):
                return cast(bool, await result)
            else:
                return cast(bool, result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis设置键过期时间失败 [{key}]: {str(e)}")
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        增加键值

        Args:
            key: 键名
            amount: 增加量

        Returns:
            int: 增加后的值
        """
        try:
            prefixed_key = self._get_key(key)
            result = self.redis.incr(prefixed_key, amount)
            if hasattr(result, "__await__"):
                final_result = cast(int, await result)
            else:
                final_result = cast(int, result)
            # Redis增加键值
            return final_result
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis增加键值失败 [{key}]: {str(e)}")
            return 0

    async def hget(self, name: str, key: str) -> Optional[str]:
        """
        获取哈希表中的字段值

        Args:
            name: 哈希表名
            key: 字段名

        Returns:
            Optional[str]: 字段值，如果不存在则为None
        """
        try:
            prefixed_name = self._get_key(name)
            hget_result = self.redis.hget(prefixed_name, key)
            if hasattr(hget_result, "__await__"):
                final_result = await hget_result  # type: ignore
                return cast(Optional[str], final_result)
            else:
                return cast(Optional[str], hget_result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis获取哈希表字段值失败 [{name}:{key}]: {str(e)}")
            return None

    async def hset(self, name: str, key: str, value: str) -> int:
        """
        设置哈希表中的字段值

        Args:
            name: 哈希表名
            key: 字段名
            value: 字段值

        Returns:
            int: 新字段的数量
        """
        try:
            prefixed_name = self._get_key(name)
            result = await self.redis.hset(prefixed_name, key, value)  # type: ignore
            return cast(int, result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis设置哈希表字段值失败 [{name}:{key}]: {str(e)}")
            return 0

    async def hdel(self, name: str, *keys: str) -> int:
        """
        删除哈希表中的字段

        Args:
            name: 哈希表名
            keys: 字段名列表

        Returns:
            int: 删除的字段数量
        """
        try:
            prefixed_name = self._get_key(name)
            result = await self.redis.hdel(prefixed_name, *keys)  # type: ignore
            return cast(int, result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis删除哈希表字段失败: {str(e)}")
            return 0

    async def hgetall(self, name: str) -> Dict[str, str]:
        """
        获取哈希表中的所有字段和值

        Args:
            name: 哈希表名

        Returns:
            Dict[str, str]: 字段和值的字典
        """
        try:
            prefixed_name = self._get_key(name)
            result = await self.redis.hgetall(prefixed_name)  # type: ignore
            return cast(Dict[str, str], result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis获取哈希表所有字段和值失败: {str(e)}")
            return {}

    async def lpush(self, name: str, *values: Any) -> int:
        """
        将一个或多个值推入列表的左端

        Args:
            name: 列表名
            values: 值列表

        Returns:
            int: 列表的长度
        """
        try:
            prefixed_name = self._get_key(name)
            result = await self.redis.lpush(prefixed_name, *values)  # type: ignore
            return cast(int, result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis推入列表左端失败: {str(e)}")
            return 0

    async def rpush(self, name: str, *values: Any) -> int:
        """
        将一个或多个值推入列表的右端

        Args:
            name: 列表名
            values: 值列表

        Returns:
            int: 列表的长度
        """
        try:
            prefixed_name = self._get_key(name)
            result = await self.redis.rpush(prefixed_name, *values)  # type: ignore
            return cast(int, result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis推入列表右端失败: {str(e)}")
            return 0

    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """
        获取列表指定范围的元素

        Args:
            name: 列表名
            start: 开始索引
            end: 结束索引

        Returns:
            List[str]: 元素列表
        """
        try:
            prefixed_name = self._get_key(name)
            result = await self.redis.lrange(prefixed_name, start, end)  # type: ignore
            return cast(List[str], result)
        except (redis.ConnectionError, redis.RedisError) as e:
            self.logger.error(f"Redis获取列表范围元素失败: {str(e)}")
            return []

    async def close(self) -> None:
        """
        关闭Redis连接
        """
        try:
            await self.redis.close()
        except Exception as e:
            self.logger.error(f"Redis关闭连接失败: {str(e)}")

    async def _check_read_write_operations(self) -> bool:
        """
        检查Redis读写操作

        Returns:
            bool: 读写操作是否正常
        """
        test_key = self._get_key("health_check_test")
        test_value = f"health_check_{int(datetime.now().timestamp())}"

        # 写入测试
        if not await self.set(test_key, test_value, expire=10):
            return False

        # 读取测试
        read_value = await self.get(test_key)
        return read_value == test_value

    async def _check_memory_usage(self) -> None:
        """
        检查Redis内存使用情况
        """
        info = cast(
            Dict[str, Any], await self.redis.info(section="memory")
        )  # type: ignore

        max_memory = info.get("maxmemory", 0)
        used_memory = info.get("used_memory", 0)

        # 如果使用的内存超过最大内存的90%，记录警告
        if max_memory and used_memory / max_memory > 0.9:
            self.logger.warning(
                f"Redis内存使用率过高: {used_memory}/{max_memory} "
                f"({used_memory / max_memory:.1%})"
            )

    async def health_check(self) -> bool:
        """
        检查Redis连接健康状态

        包含更全面的健康检查，不只是ping

        Returns:
            bool: 健康状态
        """
        try:
            # 检查基础连接
            if not await self.ping():
                return False

            # 尝试基本的读写操作
            if not await self._check_read_write_operations():
                return False

            # 检查内存使用情况
            await self._check_memory_usage()

            return True
        except Exception as e:
            self.logger.error(f"Redis健康检查失败: {str(e)}")
            return False


async def get_redis(
    redis_client: redis.Redis = Depends(get_redis_client),
) -> RedisClient:
    """
    获取Redis客户端，用于FastAPI依赖注入

    Args:
        redis_client: Redis客户端

    Returns:
        RedisClient: Redis客户端包装类
    """
    return RedisClient(redis_client)


def get_redis_sync() -> Any:
    """
    获取同步版Redis客户端实例

    Returns:
        redis.Redis: 同步Redis客户端实例

    Note:
        这个函数用于在需要同步Redis操作的地方使用，如后台任务
    """
    try:
        # 使用同步版本的redis库，而不是异步版本
        import redis

        return cast(
            redis.Redis, redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        )
    except Exception as e:
        logger.error(f"同步Redis连接失败: {str(e)}")
        return None
