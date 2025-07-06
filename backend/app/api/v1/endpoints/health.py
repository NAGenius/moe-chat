#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
健康检查API端点
"""

from typing import Any, Dict

from app.config import settings
from app.db.database import get_db
from app.db.schemas.api.response.base import success_response
from app.utils.logger import get_logger
from app.utils.redis_client import RedisClient, get_redis
from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()
logger = get_logger(__name__)


@router.get("")
async def health_check(
    session: AsyncSession = Depends(get_db),
    redis_client: RedisClient = Depends(get_redis),
) -> Dict[str, Any]:
    """
    检查API服务健康状态

    检查数据库和Redis连接
    """
    # 检查状态
    database_status = "正常"
    redis_status = "正常"
    overall_status = "正常"
    http_status = status.HTTP_200_OK

    # 检查数据库
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"数据库连接检查失败: {str(e)}")
        database_status = "异常"
        overall_status = "异常"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    # 检查Redis
    try:
        redis_healthy = await redis_client.health_check()
        if not redis_healthy:
            redis_status = "异常"
            overall_status = "异常"
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    except Exception as e:
        logger.error(f"Redis连接检查失败: {str(e)}")
        redis_status = "异常"
        overall_status = "异常"
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE

    # 返回结果
    return success_response(
        code=http_status,
        message="请求成功",
        data={
            "status": overall_status,
            "database": database_status,
            "redis": redis_status,
            "version": settings.VERSION,
        },
    )
