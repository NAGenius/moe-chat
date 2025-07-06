#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CORS中间件模块

处理跨域资源共享
"""

from app.config import settings
from app.utils.logger import get_logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = get_logger(__name__)


def setup_cors_middleware(app: FastAPI) -> None:
    """
    设置CORS中间件

    Args:
        app: FastAPI应用实例
    """
    # 确保使用正确的配置项
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            allow_headers=["*"],
        )

        origins_str = ", ".join(str(origin) for origin in settings.BACKEND_CORS_ORIGINS)
        logger.info(f"CORS中间件已设置，允许的源: {origins_str}")
    else:
        logger.warning("CORS中间件未设置，因为没有配置BACKEND_CORS_ORIGINS")
