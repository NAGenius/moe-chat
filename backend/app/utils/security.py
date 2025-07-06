#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全工具模块

处理密码哈希、令牌生成和验证
"""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional

from app.config import settings
from jose import JWTError, jwt
from pydantic import ValidationError

# 哈希算法参数
ALGORITHM = "sha256"
SALT_SIZE = 32
ITERATIONS = 100000  # 推荐的迭代次数


def get_password_hash(password: str) -> str:
    """
    获取密码哈希，使用PBKDF2算法

    Args:
        password: 明文密码

    Returns:
        str: 哈希密码格式：算法$迭代次数$salt$hash
    """
    # 生成随机盐值
    salt = secrets.token_bytes(SALT_SIZE)

    # 使用PBKDF2算法哈希密码
    hash_bytes = hashlib.pbkdf2_hmac(
        ALGORITHM, password.encode("utf-8"), salt, ITERATIONS
    )

    # 编码为base64字符串
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    hash_b64 = base64.b64encode(hash_bytes).decode("utf-8")

    # 组合为格式化字符串
    return f"pbkdf2:{ALGORITHM}${ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码

    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码

    Returns:
        bool: 密码是否匹配
    """
    try:
        # 解析哈希字符串
        parts = hashed_password.split("$")
        if len(parts) != 4 or not parts[0].startswith("pbkdf2:"):
            # 处理旧格式密码（如果有）
            return False

        # 提取算法、迭代次数和盐值
        algo = parts[0].split(":")[1]
        iterations = int(parts[1])
        salt = base64.b64decode(parts[2])
        stored_hash = base64.b64decode(parts[3])

        # 使用相同参数计算哈希
        hash_bytes = hashlib.pbkdf2_hmac(
            algo, plain_password.encode("utf-8"), salt, iterations
        )

        # 比较哈希值
        return hash_bytes == stored_hash
    except Exception:
        # 任何解析错误都返回False
        return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建访问令牌

    Args:
        data: 令牌数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT访问令牌
    """
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # 添加标准声明
    to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "access"})

    # 编码JWT
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    创建刷新令牌

    Args:
        data: 令牌数据
        expires_delta: 过期时间增量

    Returns:
        str: JWT刷新令牌
    """
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # 添加标准声明
    to_encode.update({"exp": expire, "iat": datetime.now(UTC), "type": "refresh"})

    # 编码JWT
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_REFRESH_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """
    验证令牌

    Args:
        token: JWT令牌
        token_type: 令牌类型，"access"或"refresh"

    Returns:
        Optional[str]: 令牌主题，如果验证失败则返回None
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        if payload.get("type") != token_type:
            return None
        subject = payload.get("sub")
        if subject is None:
            return None
        return str(subject)
    except (JWTError, ValidationError):
        return None


def generate_password_reset_token(user_id: uuid.UUID) -> str:
    """
    生成密码重置令牌

    Args:
        user_id: 用户ID

    Returns:
        str: 密码重置令牌
    """
    expire = datetime.now(UTC) + timedelta(hours=24)
    payload = {
        "exp": expire,
        "user_id": str(user_id),
        "action": "password_reset",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def verify_password_reset_token(token: str) -> Optional[str]:
    """
    验证密码重置令牌

    Args:
        token: 密码重置令牌

    Returns:
        Optional[str]: 用户ID，如果令牌无效则为None
    """
    try:
        decoded_token = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if decoded_token.get("action") != "password_reset":
            return None
        return decoded_token.get("user_id")
    except JWTError:
        return None


def generate_token() -> str:
    """
    生成随机令牌

    Returns:
        str: 随机令牌
    """
    return secrets.token_urlsafe(32)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    解码令牌

    Args:
        token: JWT令牌

    Returns:
        Optional[Dict[str, Any]]: 解码后的令牌数据，如果解码失败则返回None
    """
    try:
        return jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except JWTError:
        return None
