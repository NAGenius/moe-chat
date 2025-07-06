#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Token计算工具模块

提供消息token数量计算和智能截断功能
"""

import re
from typing import Dict, List, Optional

from app.utils.logger import get_logger

# 获取日志记录器
logger = get_logger(__name__)


class TokenCounter:
    """
    Token计数器

    使用简单的启发式方法估算token数量，适用于中英文混合文本
    """

    def __init__(self) -> None:
        # 中文字符的正则表达式
        self.chinese_pattern = re.compile(r"[\u4e00-\u9fff]+")
        # 英文单词的正则表达式
        self.english_pattern = re.compile(r"\b\w+\b")
        # 特殊符号和标点
        self.symbol_pattern = re.compile(r"[^\w\s\u4e00-\u9fff]")

    def count_tokens(self, text: str) -> int:
        """
        估算文本的token数量

        Args:
            text: 输入文本

        Returns:
            int: 估算的token数量
        """
        if not text:
            return 0

        # 中文字符：每个字符约1个token
        chinese_tokens = sum(len(match) for match in self.chinese_pattern.findall(text))

        # 英文单词：平均每个单词约1.3个token
        english_words = len(self.english_pattern.findall(text))
        english_tokens = int(english_words * 1.3)

        # 特殊符号：每个符号约0.5个token
        symbols = len(self.symbol_pattern.findall(text))
        symbol_tokens = int(symbols * 0.5)

        total_tokens = chinese_tokens + english_tokens + symbol_tokens

        # 最小值为1（非空文本）
        return max(1, total_tokens)

    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        计算消息列表的总token数量

        Args:
            messages: 消息列表，每个消息包含role和content字段

        Returns:
            int: 总token数量
        """
        total_tokens = 0

        for message in messages:
            # 计算role的token（通常很少）
            role_tokens = self.count_tokens(message.get("role", ""))
            # 计算content的token
            content_tokens = self.count_tokens(message.get("content", ""))

            # 每条消息还有一些格式化的开销
            message_overhead = 4  # 估算的格式化开销

            total_tokens += role_tokens + content_tokens + message_overhead

        return total_tokens

    def truncate_messages_by_tokens(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        preserve_system: bool = True,
    ) -> List[Dict[str, str]]:
        """
        根据token限制智能截断消息列表

        Args:
            messages: 消息列表
            max_tokens: 最大token数量
            preserve_system: 是否保留系统消息

        Returns:
            List[Dict[str, str]]: 截断后的消息列表
        """
        if not messages:
            return []

        system_messages, other_messages = self._separate_messages(messages)
        system_messages, system_tokens = self._process_system_messages(
            system_messages, max_tokens, preserve_system
        )

        remaining_tokens = max_tokens - system_tokens
        if remaining_tokens <= 0:
            return system_messages if preserve_system else []

        selected_messages = self._select_messages_by_tokens(
            other_messages, remaining_tokens
        )

        result = self._combine_messages(
            system_messages, selected_messages, preserve_system
        )
        self._log_truncation_result(messages, result)
        return result

    def _separate_messages(self, messages: List[Dict[str, str]]) -> tuple:
        """分离系统消息和其他消息"""
        system_messages = []
        other_messages = []

        for message in messages:
            if message.get("role") == "system":
                system_messages.append(message)
            else:
                other_messages.append(message)

        return system_messages, other_messages

    def _process_system_messages(
        self,
        system_messages: List[Dict[str, str]],
        max_tokens: int,
        preserve_system: bool,
    ) -> tuple:
        """处理系统消息并返回处理后的消息和token数量"""
        if not preserve_system or not system_messages:
            return [], 0

        system_tokens = self.count_messages_tokens(system_messages)

        # 如果系统消息已经超过限制，只保留最后一个系统消息
        if system_tokens > max_tokens and system_messages:
            system_messages = [system_messages[-1]]
            system_tokens = self.count_messages_tokens(system_messages)

        return system_messages, system_tokens

    def _select_messages_by_tokens(
        self, messages: List[Dict[str, str]], max_tokens: int
    ) -> List[Dict[str, str]]:
        """根据token限制选择消息"""
        selected_messages: List[Dict[str, str]] = []
        current_tokens = 0

        # 反向遍历消息（从最新开始）
        for message in reversed(messages):
            message_tokens = self.count_messages_tokens([message])

            if current_tokens + message_tokens <= max_tokens:
                selected_messages.insert(0, message)
                current_tokens += message_tokens
            else:
                # 如果单条消息就超过限制，尝试截断内容
                if not selected_messages and message_tokens > max_tokens:
                    truncated_message = self._truncate_single_message(
                        message, max_tokens
                    )
                    if truncated_message:
                        selected_messages.insert(0, truncated_message)
                break

        return selected_messages

    def _combine_messages(
        self,
        system_messages: List[Dict[str, str]],
        selected_messages: List[Dict[str, str]],
        preserve_system: bool,
    ) -> List[Dict[str, str]]:
        """合并系统消息和选中的消息"""
        result = []
        if preserve_system:
            result.extend(system_messages)
        result.extend(selected_messages)
        return result

    def _log_truncation_result(
        self,
        original_messages: List[Dict[str, str]],
        result_messages: List[Dict[str, str]],
    ) -> None:
        """记录截断结果"""
        original_count = len(original_messages)
        result_count = len(result_messages)

        if result_count < original_count:
            original_tokens = self.count_messages_tokens(original_messages)
            result_tokens = self.count_messages_tokens(result_messages)

            # 计算截断的消息数量和token数量
            truncated_messages = original_count - result_count
            saved_tokens = original_tokens - result_tokens

            logger.info(
                f"消息已截断: {original_count} -> {result_count} 条消息 "
                f"({truncated_messages} 条被移除), "
                f"Token数量: {original_tokens} -> {result_tokens} "
                f"(节省 {saved_tokens} tokens)"
            )
        else:
            logger.debug(f"消息未截断: 保留全部 {original_count} 条消息")

    def _truncate_single_message(
        self, message: Dict[str, str], max_tokens: int
    ) -> Optional[Dict[str, str]]:
        """
        截断单条消息的内容

        Args:
            message: 消息
            max_tokens: 最大token数量

        Returns:
            Optional[Dict[str, str]]: 截断后的消息，如果无法截断则返回None
        """
        content = message.get("content", "")
        if not content:
            return message

        # 预留一些token给role和格式化开销
        content_max_tokens = max_tokens - 10
        if content_max_tokens <= 0:
            return None

        # 简单的截断策略：按字符比例截断
        current_tokens = self.count_tokens(content)
        if current_tokens <= content_max_tokens:
            return message

        # 计算截断比例
        truncate_ratio = content_max_tokens / current_tokens
        truncate_length = int(len(content) * truncate_ratio * 0.9)  # 保守一点

        if truncate_length <= 0:
            return None

        truncated_content = content[:truncate_length] + "...[内容已截断]"

        return {"role": message["role"], "content": truncated_content}


# 全局token计数器实例
_token_counter = None


def get_token_counter() -> TokenCounter:
    """
    获取全局token计数器实例

    Returns:
        TokenCounter: token计数器实例
    """
    global _token_counter
    if _token_counter is None:
        _token_counter = TokenCounter()
    return _token_counter
