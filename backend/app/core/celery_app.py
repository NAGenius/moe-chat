#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery应用模块

定义Celery应用实例和配置
"""

import platform

from app.config import settings
from celery import Celery  # type: ignore

# 创建Celery实例
celery_app = Celery("moe_chat")

# 配置Celery
celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_time_limit = 60 * 5  # 5分钟
# 在Windows平台上禁用软超时，因为Windows不支持SIGUSR1信号
if platform.system() != "Windows":
    celery_app.conf.task_soft_time_limit = 60 * 3  # 3分钟
celery_app.conf.worker_max_tasks_per_child = 1000
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.broker_connection_max_retries = 10

# 配置任务队列
celery_app.conf.task_routes = {
    "app.tasks.file_tasks.*": {"queue": "files"},
    "app.tasks.user_tasks.*": {"queue": "users"},
    "app.tasks.model_tasks.*": {"queue": "models"},
}

# 自动检测和注册任务
celery_app.autodiscover_tasks(["app.tasks"])
