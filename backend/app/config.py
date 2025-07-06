#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
应用配置模块

定义应用的所有配置项
"""

import os
import secrets
from pathlib import Path
from typing import Any, List, Optional, Union

from dotenv import load_dotenv
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# 显式加载环境变量
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)


class Settings(BaseSettings):
    """应用配置类"""

    # API前缀
    API_PREFIX: str = os.getenv("API_V1_STR", "/api/v1")

    # 项目名称
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "MoE-Chat")

    # 项目描述
    DESCRIPTION: str = os.getenv("DESCRIPTION", "基于混合专家模型的聊天应用")

    # 项目版本
    VERSION: str = os.getenv("VERSION", "0.1.0")

    # 数据库配置
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/moe_chat"
    )

    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    REDIS_MAX_RETRY_COUNT: int = int(os.getenv("REDIS_MAX_RETRY_COUNT", "3"))
    REDIS_RETRY_INTERVAL: float = float(os.getenv("REDIS_RETRY_INTERVAL", "1.0"))
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "20"))
    REDIS_SOCKET_TIMEOUT: float = float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0"))
    REDIS_SOCKET_CONNECT_TIMEOUT: float = float(
        os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2.0")
    )
    REDIS_HEALTH_CHECK_INTERVAL: int = int(
        os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "15")
    )
    REDIS_KEY_PREFIX: str = os.getenv("REDIS_KEY_PREFIX", "moe_chat:")

    # JWT配置
    JWT_SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    JWT_REFRESH_SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
    )  # 24小时
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )  # 7天

    # 邮件配置
    SMTP_HOST: str = os.getenv("EMAIL_SMTP_SERVER", "smtp.163.com")
    SMTP_PORT: int = int(os.getenv("EMAIL_SMTP_PORT", "465"))
    SMTP_USER: str = os.getenv("EMAIL_SENDER", "user@example.com")
    SMTP_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "password")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAIL_SENDER", "noreply@example.com")
    EMAILS_FROM_NAME: str = os.getenv("EMAIL_SENDER_NAME", "MoE-Chat")

    # 邮箱验证码配置
    EMAIL_VERIFICATION_TTL: int = int(
        os.getenv("EMAIL_VERIFICATION_TTL", "600")
    )  # 10分钟
    EMAIL_VERIFICATION_CODE_LENGTH: int = int(
        os.getenv("EMAIL_VERIFICATION_CODE_LENGTH", "6")
    )
    # 验证码重发间隔（秒）
    EMAIL_VERIFICATION_RETRY_INTERVAL: int = int(
        os.getenv("EMAIL_VERIFICATION_RETRY_INTERVAL", "60")
    )
    # 为了保持向后兼容，EMAIL_VERIFICATION_RATE_LIMIT 指向相同的值
    EMAIL_VERIFICATION_RATE_LIMIT: int = int(
        os.getenv("EMAIL_VERIFICATION_RETRY_INTERVAL", "60")
    )

    # 模型服务配置
    @property
    def MODEL_SERVICE_URLS(self) -> List[str]:
        """获取所有模型服务URL列表"""
        urls = os.getenv("MODEL_SERVICE_URLS", "http://localhost:8001")
        return [url.strip() for url in urls.split(",") if url.strip()]

    @property
    def DEFAULT_SERVICE_URL(self) -> str:
        """获取默认的模型服务URL"""
        return (
            self.MODEL_SERVICE_URLS[0]
            if self.MODEL_SERVICE_URLS
            else "http://localhost:8001"
        )

    MODEL_SERVICE_TIMEOUT: int = int(os.getenv("MODEL_SERVICE_TIMEOUT", "60"))  # 60秒

    # CORS配置
    BACKEND_CORS_ORIGINS: List[str] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Optional[Union[str, List[str]]]) -> List[str]:
        """
        解析CORS配置
        """
        # 从环境变量CORS_ORIGINS读取
        cors_origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"
        )
        return [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")

    # 上传文件配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    MAX_UPLOAD_SIZE: int = int(
        os.getenv("MAX_UPLOAD_SIZE", str(10 * 1024 * 1024))
    )  # 10MB

    # 文件清理配置
    FILE_CLEANUP_INTERVAL: int = int(
        os.getenv("FILE_CLEANUP_INTERVAL", "3600")
    )  # 默认每小时清理一次
    FILE_TTL: int = int(os.getenv("FILE_TTL", "86400"))  # 默认24小时后删除未关联文件

    # 项目配置
    DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
    APP_ENV: str = os.environ.get("APP_ENV", "development")
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", "8000"))

    # 模型服务配置
    MODEL_SERVICE_RETRY_COUNT: int = int(
        os.environ.get("MODEL_SERVICE_RETRY_COUNT", "3")
    )
    MODEL_SERVICE_RETRY_DELAY: int = int(
        os.environ.get("MODEL_SERVICE_RETRY_DELAY", "1")
    )

    # 模型配置 - 直接从环境变量获取，避免复杂类型解析
    DEFAULT_MODEL: str = os.environ.get("DEFAULT_MODEL", "deepseek-moe-16b")

    @property
    def THINKING_MODELS(self) -> List[str]:
        models = os.environ.get("THINKING_MODELS", "DeepSeek-R1-Distill-Qwen-1.5B")
        return [m.strip() for m in models.split(",") if m.strip()]

    # 限流配置
    RATE_LIMIT_REQUESTS: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
    RATE_LIMIT_WINDOW: int = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))

    # 日志配置
    LOG_FORMAT: str = os.environ.get(
        "LOG_FORMAT", "%(levelprefix)s | %(asctime)s | %(message)s"
    )

    # 文件上传配置
    @property
    def ALLOWED_EXTENSIONS(self) -> List[str]:
        extensions = os.environ.get("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif,pdf")
        return [ext.strip() for ext in extensions.split(",") if ext.strip()]

    MODEL_SERVICE_RECONNECT_MAX_TRIES: int = int(
        os.environ.get("MODEL_SERVICE_RECONNECT_MAX_TRIES", "5")
    )
    MODEL_SERVICE_DISCOVER_INTERVAL: int = int(
        os.environ.get("MODEL_SERVICE_DISCOVER_INTERVAL", "300")
    )  # 服务发现间隔（秒）

    # 邮件配置
    EMAIL_USE_TLS: bool = os.environ.get("EMAIL_USE_TLS", "True").lower() == "true"

    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str]) -> Any:
        """设置数据库连接URI"""
        return os.getenv("DATABASE_URL")

    # Celery配置
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0")
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/0")
    )
    CELERY_TASK_ALWAYS_EAGER: bool = (
        os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
    )
    CELERY_TASK_EAGER_PROPAGATES: bool = True

    class Config:
        """配置元数据"""

        case_sensitive = True


# 创建全局配置实例
settings = Settings()

# 确保日志和上传目录存在
os.makedirs(os.path.dirname(BASE_DIR / settings.LOG_FILE), exist_ok=True)
os.makedirs(BASE_DIR / settings.UPLOAD_DIR, exist_ok=True)
