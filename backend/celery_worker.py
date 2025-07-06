#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Celery Worker启动脚本

启动Celery Worker进程
"""

from app.core.celery_app import celery_app

if __name__ == "__main__":
    # 执行Celery Worker
    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=INFO",
            "--concurrency=2",  # 进程数
            "-Q",
            "files,users,models,celery",  # 监听的队列
        ]
    )
