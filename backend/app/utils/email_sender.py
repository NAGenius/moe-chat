#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
邮件发送工具

处理邮件发送功能
"""

import datetime
import smtplib
import socket
import ssl
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

from app.config import settings
from app.utils.logger import get_logger
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = get_logger(__name__)


class EmailSender:
    """邮件发送类"""

    def __init__(self) -> None:
        """初始化邮件发送器"""
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.from_name = settings.EMAILS_FROM_NAME
        self.use_tls = settings.EMAIL_USE_TLS

        # 重试配置
        self.max_retries = 3
        self.retry_delay = 5  # 重试间隔(秒)
        self.timeout = 30  # 连接超时时间(秒)

        # 设置模板目录
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.verification_template_path = self.templates_dir / "verification_email.html"

        # 设置Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    async def send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            html_content: HTML格式的邮件内容

        Returns:
            bool: 是否发送成功
        """
        # 创建邮件
        message = MIMEMultipart()
        message["From"] = formataddr((self.from_name, self.from_email))
        message["To"] = formataddr(("收件人", to_email))
        message["Subject"] = subject

        # 添加HTML内容
        message.attach(MIMEText(html_content, "html"))

        # 创建SSL上下文
        context = ssl.create_default_context()

        # 使用重试机制发送邮件
        for attempt in range(self.max_retries):
            try:
                # 使用SSL连接(安全连接)
                with smtplib.SMTP_SSL(
                    host=self.host,
                    port=self.port,
                    context=context,
                    timeout=self.timeout,
                ) as server:
                    server.login(self.username, self.password)
                    server.send_message(message)

                logger.info(f"邮件发送成功: {to_email}, 主题: {subject}")
                return True

            except smtplib.SMTPServerDisconnected as e:
                logger.warning(
                    f"邮件发送尝试 {attempt + 1}/{self.max_retries}: 连接断开 - {str(e)}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                logger.error(
                    f"邮件发送失败(连接断开): {to_email}, 主题: {subject}, 错误: {str(e)}"
                )
                return False

            except socket.timeout:
                logger.warning(
                    f"邮件发送尝试 {attempt + 1}/{self.max_retries}: 连接超时"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                logger.error(f"邮件发送失败(连接超时): {to_email}, 主题: {subject}")
                return False

            except Exception as e:
                logger.error(
                    f"邮件发送失败: {to_email}, 主题: {subject}, 错误: {str(e)}"
                )
                return False

        # 如果所有重试都失败了
        return False

    async def send_verification_email(self, to_email: str, code: str) -> bool:
        """
        发送验证码邮件

        Args:
            to_email: 收件人邮箱
            code: 验证码

        Returns:
            bool: 是否发送成功
        """
        subject = f"【{settings.PROJECT_NAME}】邮箱验证码"

        try:
            # 准备模板变量
            username = to_email.split("@")[0]
            current_year = datetime.datetime.now().year
            template_vars = {
                "username": username,
                "code": code,
                "expires_in": settings.EMAIL_VERIFICATION_TTL,
                "year": current_year,
                "project_name": settings.PROJECT_NAME,
            }

            # 使用模板
            if self.verification_template_path.exists():
                # 使用Jinja2渲染模板
                template = self.jinja_env.get_template("verification_email.html")
                html_content = template.render(**template_vars)
            else:
                # 备用简单HTML
                project_name = settings.PROJECT_NAME
                expire_minutes = settings.EMAIL_VERIFICATION_TTL // 60
                html_content = (
                    f'<div style="font-family: Arial, sans-serif; '
                    f'max-width: 600px; margin: 0 auto;">'
                    f"<h2>邮箱验证码</h2>"
                    f"<p>您好，{username}，感谢您使用{project_name}!</p>"
                    f'<p>您的验证码是: <strong style="font-size: 18px;">{code}</strong></p>'
                    f"<p>此验证码将在{expire_minutes}分钟后过期。</p>"
                    f"<p>如果您没有请求此验证码，请忽略此邮件。</p>"
                    f'<div style="margin-top: 20px; font-size: 12px; '
                    f'color: #999; text-align: center;">'
                    f"<p>此邮件由系统自动发送，请勿回复。</p>"
                    f"<p>&copy; {current_year} {project_name}。保留所有权利。</p>"
                    f"</div></div>"
                )

            # 发送邮件
            return await self.send_email(to_email, subject, html_content)

        except Exception as e:
            logger.error(f"发送验证码邮件失败: {to_email}, 错误: {str(e)}")
            return False
