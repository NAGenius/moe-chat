#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证服务

处理邮箱验证码等功能
"""

import random
import string
from typing import Optional, Tuple

from app.config import settings
from app.db.schemas.dto.output.user_dto import (
    EmailVerificationCodeDTO,
    EmailVerificationResultDTO,
)
from app.utils.email_sender import EmailSender
from app.utils.logger import get_logger
from app.utils.redis_client import RedisClient, get_redis
from fastapi import Depends

logger = get_logger(__name__)


class VerificationService:
    """验证码服务类"""

    def __init__(self, redis_client: RedisClient, email_sender: EmailSender):
        """
        初始化验证码服务

        Args:
            redis_client: Redis客户端
            email_sender: 邮件发送器
        """
        self.redis = redis_client
        self.email_sender = email_sender

    async def send_verification_code(
        self, email: str
    ) -> Tuple[bool, Optional[EmailVerificationCodeDTO], Optional[str]]:
        """
        发送验证码

        Args:
            email: 邮箱地址

        Returns:
            Tuple[bool, Optional[EmailVerificationCodeDTO], Optional[str]]:
                (是否成功, 验证码DTO, 错误信息)
        """
        # 检查是否在限制时间内
        rate_limit_key = f"email_verification_rate_limit:{email}"
        if await self.redis.exists(rate_limit_key):
            ttl = await self.redis.ttl(rate_limit_key)
            return (False, None, f"发送过于频繁，请在 {ttl} 秒后重试")

        # 生成验证码
        code = self._generate_code()

        # 发送邮件
        try:
            email_send_result = await self.email_sender.send_verification_email(
                to_email=email, code=code
            )
            if not email_send_result:
                return False, None, "邮件发送失败，请检查邮箱地址或稍后再试"
        except Exception as e:
            logger.error(f"发送验证码邮件失败: {str(e)}")
            return False, None, f"发送邮件失败: {str(e)}"

        # 保存验证码到Redis，明确设置过期时间（秒）
        verification_key = f"email_verification:{email}"
        expire_seconds = settings.EMAIL_VERIFICATION_TTL
        # 设置验证码过期时间

        # 确保验证码被正确设置并有正确的过期时间
        set_result = await self.redis.set(verification_key, code, expire=expire_seconds)
        if not set_result:
            logger.error(f"Redis设置验证码失败: {email}")
            return False, None, "服务器错误，无法保存验证码"

        # 验证是否成功设置
        ttl_check = await self.redis.ttl(verification_key)
        if ttl_check <= 0:
            logger.error(f"Redis验证码TTL检查失败: {email}, TTL={ttl_check}")
            return False, None, "服务器错误，验证码设置异常"

        # 验证码已设置

        # 设置发送频率限制
        rate_limit_seconds = settings.EMAIL_VERIFICATION_RETRY_INTERVAL
        await self.redis.set(rate_limit_key, "1", expire=rate_limit_seconds)

        logger.info(f"验证码发送成功: {email}, 过期时间: {expire_seconds}秒")

        # 创建并返回验证码DTO
        verification_code_dto = EmailVerificationCodeDTO(
            email=email, expires_in=expire_seconds
        )

        return True, verification_code_dto, None

    async def verify_code(self, email: str, code: str) -> EmailVerificationResultDTO:
        """
        验证验证码

        Args:
            email: 邮箱地址
            code: 验证码

        Returns:
            EmailVerificationResultDTO: 验证结果DTO
        """
        verification_key = f"email_verification:{email}"
        stored_code = await self.redis.get(verification_key)

        if not stored_code:
            logger.warning(f"验证码不存在或已过期: {email}")
            return EmailVerificationResultDTO(
                success=False, message="验证码不存在或已过期"
            )

        # 验证码比较
        is_valid = stored_code == code

        if is_valid:
            # 验证成功后删除验证码
            await self.redis.delete(verification_key)
            logger.info(f"验证码验证成功: {email}")
            return EmailVerificationResultDTO(success=True, message="验证成功")
        else:
            logger.warning(
                f"验证码验证失败: {email}, 输入: {code}, 实际: {stored_code}"
            )
            return EmailVerificationResultDTO(success=False, message="验证码错误")

    def _generate_code(self) -> str:
        """
        生成随机验证码

        Returns:
            str: 生成的验证码
        """
        # 生成指定长度的数字验证码
        digits = string.digits
        code_length = settings.EMAIL_VERIFICATION_CODE_LENGTH
        code = "".join(random.choice(digits) for _ in range(code_length))
        return code


async def get_verification_service(
    redis_client: RedisClient = Depends(get_redis),
) -> VerificationService:
    """
    获取验证码服务实例

    Args:
        redis_client: Redis客户端

    Returns:
        VerificationService: 验证码服务实例
    """
    email_sender = EmailSender()
    return VerificationService(redis_client=redis_client, email_sender=email_sender)
