#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
日志工具模块

使用loguru提供更美观、高效的日志功能
"""

import logging
import sys
from pathlib import Path
from types import FrameType
from typing import Any, Optional, Union

from app.config import settings
from loguru import logger

# 定义日志格式
# 更丰富、更易于阅读的格式，包括时间、级别、模块、行号和消息
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 为不同级别定义不同的颜色
LEVEL_COLORS = {
    "TRACE": {"color": "<cyan>"},
    "DEBUG": {"color": "<blue>"},
    "INFO": {"color": "<green>"},
    "SUCCESS": {"color": "<green>"},
    "WARNING": {"color": "<yellow>"},
    "ERROR": {"color": "<red>"},
    "CRITICAL": {"color": "<RED><bold>"},
}


class InterceptHandler(logging.Handler):
    """
    将标准库logging的日志重定向到loguru

    用于兼容使用标准库logging的第三方库
    """

    def emit(self, record: logging.LogRecord) -> None:
        # 获取对应的Loguru级别
        try:
            level: Union[str, int] = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 找到发出日志的源头
        frame: Optional[FrameType] = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # 将日志记录传递给Loguru
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """
    配置loguru日志系统

    设置日志格式、级别和输出目标
    """
    # 创建日志目录
    log_dir = Path(settings.LOG_FILE).parent
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)

    # 设置日志级别
    log_level = settings.LOG_LEVEL.upper()

    # 清除默认的处理器
    logger.remove()

    # 添加控制台输出处理器
    logger.add(
        sys.stdout, format=LOG_FORMAT, level=log_level, colorize=True, enqueue=True
    )

    # 添加文件输出处理器（带有轮转）
    logger.add(
        settings.LOG_FILE,
        format=LOG_FORMAT,
        level=log_level,
        rotation="10 MB",  # 当日志文件达到10MB时轮转
        retention="1 week",  # 保留1周的日志
        compression="zip",  # 轮转后压缩归档
        encoding="utf-8",
        enqueue=True,  # 多进程安全
        backtrace=True,  # 异常时显示完整栈跟踪
        diagnose=True,  # 显示变量值等诊断信息
    )

    # 拦截标准库logging的日志
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 设置第三方库的日志级别
    for logger_name in [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "fastapi",
        "sqlalchemy.engine",
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
        logging.getLogger(logger_name).handlers = [InterceptHandler()]

    # 记录初始日志
    logger.info(f"日志系统初始化完成，级别: {log_level}")


def get_logger(name: Optional[str] = None) -> Any:
    """
    获取loguru日志记录器

    Args:
        name: 模块名称

    Returns:
        loguru日志记录器
    """
    return logger.bind(name=name)


# 导出一个预先配置的实例，用于直接导入
default_logger = get_logger(__name__)
