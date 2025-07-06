#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用入口模块

创建FastAPI应用实例，注册路由和中间件
"""

import asyncio
import contextlib
from typing import Any, AsyncGenerator, Optional

from app.api.v1.router import api_router
from app.config import settings
from app.core.celery_app import celery_app
from app.db.database import close_db, init_db
from app.db.schemas.api.response.base import error_response
from app.middleware.cors import setup_cors_middleware
from app.middleware.errors import (
    api_exception_handler,
    error_handler_middleware,
    http_exception_handler,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from app.middleware.logging import LoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.model_service import ModelService
from app.utils.exceptions import APIException
from app.utils.logger import get_logger, setup_logging
from app.utils.redis_client import close_redis_pool, init_redis_pool
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

# 设置日志
setup_logging()
logger = get_logger("app.main")


# 应用状态
class AppState:
    heartbeat_task: Optional[asyncio.Task[None]] = None


app_state = AppState()


# 配置Celery定时任务
@celery_app.on_after_configure.connect  # type: ignore
def setup_periodic_tasks(sender: Any, **kwargs: Any) -> None:
    """
    配置Celery定时任务

    Args:
        sender: Celery应用实例
    """
    # 每小时执行一次文件清理任务
    sender.add_periodic_task(
        settings.FILE_CLEANUP_INTERVAL,
        sender.signature("app.tasks.file_tasks.cleanup_orphaned_files"),
        name="每小时清理未关联文件",
    )

    logger.info("Celery定时任务已配置")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 应用实例
    """
    # 创建应用
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.DESCRIPTION,
        version=settings.VERSION,
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
    )

    # 注册路由
    app.include_router(api_router, prefix=settings.API_PREFIX)

    # 配置CORS
    setup_cors_middleware(app)

    # 添加中间件
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.middleware("http")(error_handler_middleware)

    # 添加自定义异常处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(APIException, api_exception_handler)

    # 添加自定义401未认证错误处理
    @app.exception_handler(401)
    async def unauthorized_exception_handler(
        request: Request, exc: Any
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error_response(code=status.HTTP_401_UNAUTHORIZED, message="未授权"),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 使用生命周期上下文管理器
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        # 启动事件
        logger.info(f"启动 {settings.PROJECT_NAME} API 服务")

        # 初始化数据库连接
        await init_db()

        # 初始化Redis连接池
        await init_redis_pool()

        # 同步模型信息
        try:
            # 使用数据库上下文管理器，避免异步上下文问题
            from app.db.database import db_context
            from app.utils.redis_client import RedisClient, get_redis_client

            # 使用正确的数据库上下文管理器
            async with db_context() as session:
                # 获取Redis客户端
                async for redis_raw_client in get_redis_client():
                    redis_client = RedisClient(redis_raw_client)

                    model_service = ModelService(session, redis_client)
                    sync_result = await model_service.sync_models_with_service()
                    if sync_result.success:
                        logger.info(f"模型同步成功: {sync_result.message}")
                    else:
                        logger.error(f"模型同步失败: {sync_result.message}")

                    # 启动模型心跳检测任务
                    await model_service.start_heartbeat_task()
                    app_state.heartbeat_task = model_service._heartbeat_task
                    break  # 只需要一次迭代

                # 记录文件清理任务将由Celery处理
                logger.info("文件清理任务由Celery管理")

                # 记录MoE可视化数据将通过Redis发布，需要单独启动可视化器程序
                logger.info("MoE专家激活数据将通过Redis频道moe:expert:activation发布")
        except Exception as e:
            logger.error(f"应用初始化异常: {str(e)}")

        yield  # 应用运行期间

        # 关闭事件
        logger.info(f"关闭 {settings.PROJECT_NAME} API 服务")

        # 取消心跳检测任务
        if app_state.heartbeat_task is not None and not app_state.heartbeat_task.done():
            logger.info("取消模型心跳检测任务")
            app_state.heartbeat_task.cancel()
            try:
                await app_state.heartbeat_task
            except asyncio.CancelledError:
                pass

        # 关闭数据库连接
        await close_db()

        # 关闭Redis连接池
        await close_redis_pool()

    app.router.lifespan_context = lifespan

    return app


app = create_app()


# 如果直接运行此文件
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG
    )
