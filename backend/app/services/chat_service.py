#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天服务模块

处理对话生成，管理聊天上下文，格式化消息等
"""

import uuid
from typing import Dict, List, Optional

from app.db.database import get_db
from app.db.models.chat import Chat
from app.db.models.message import Message, MessageRole, MessageStatus
from app.db.repositories.chat import ChatRepository
from app.db.repositories.file import FileRepository
from app.db.repositories.message import MessageRepository
from app.db.schemas.dto.input.chat_dto import (
    ChatCreateDTO,
    ChatQueryDTO,
    ChatUpdateDTO,
    MessageCreateDTO,
    MessageQueryDTO,
)
from app.db.schemas.dto.output.chat_dto import (
    ChatDetailDTO,
    ChatDTO,
    ChatListDTO,
    ChatListItemDTO,
    MessageDTO,
    MessageListDTO,
)
from app.services.cache_service import CacheService, get_cache_service
from app.services.model_service import ModelService, get_model_service
from app.utils.exceptions import ForbiddenException, NotFoundException
from app.utils.logger import get_logger
from app.utils.token_counter import TokenCounter, get_token_counter
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

# 获取日志记录器
logger = get_logger(__name__)


class ChatService:
    """聊天服务类"""

    def __init__(
        self,
        session: AsyncSession,
        model_service: ModelService,
        cache_service: CacheService,
        token_counter: TokenCounter,
    ):
        """
        初始化聊天服务

        Args:
            session: 数据库会话
            model_service: 模型服务
            cache_service: 缓存服务
            token_counter: Token计数器
        """
        self.session = session
        self.chat_repository = ChatRepository(session)
        self.message_repository = MessageRepository(session)
        self.file_repository = FileRepository(session)
        self.model_service = model_service
        self.cache_service = cache_service
        self.token_counter = token_counter

    async def get_chat_by_id(
        self, chat_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[ChatDTO]:
        """
        根据ID获取聊天

        Args:
            chat_id: 聊天ID
            user_id: 用户ID，用于验证所有权

        Returns:
            Optional[ChatDTO]: 聊天DTO，如果不存在则为None
        """
        # 获取聊天并检查权限
        chat = await self.chat_repository.get_by_user_and_id(user_id, chat_id)
        if not chat:
            return None

        return self._convert_to_chat_dto(chat)

    async def create_chat(self, chat_dto: ChatCreateDTO) -> ChatDTO:
        """
        创建新的聊天

        Args:
            chat_dto: 聊天创建DTO

        Returns:
            ChatDTO: 创建的聊天DTO
        """
        # 创建 ChatCreate 对象
        from app.db.models.chat import ChatCreate

        chat_create = ChatCreate(user_id=chat_dto.user_id, title=chat_dto.title)

        # 使用 create_chat 方法创建聊天
        chat = await self.chat_repository.create_chat(chat_create)

        return self._convert_to_chat_dto(chat)

    async def update_chat(
        self, chat_id: uuid.UUID, user_id: uuid.UUID, update_dto: ChatUpdateDTO
    ) -> Optional[ChatDTO]:
        """
        更新聊天

        Args:
            chat_id: 聊天ID
            user_id: 用户ID
            update_dto: 聊天更新DTO

        Returns:
            Optional[ChatDTO]: 更新后的聊天DTO，如果聊天不存在或用户无权限则为None
        """
        # 检查聊天是否存在并且属于该用户
        chat = await self.chat_repository.get_by_user_and_id(user_id, chat_id)
        if not chat:
            return None

        # 创建更新对象
        from app.db.models.chat import ChatUpdate

        update_data = {}
        if update_dto.title:
            update_data["title"] = update_dto.title

        chat_update = ChatUpdate(**update_data)

        # 更新聊天
        updated_chat = await self.chat_repository.update_chat(chat_id, chat_update)

        if not updated_chat:
            from app.utils.exceptions import InternalServerErrorException

            raise InternalServerErrorException("更新聊天失败")

        return self._convert_to_chat_dto(updated_chat)

    async def delete_chat(self, chat_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        删除聊天

        Args:
            chat_id: 聊天ID
            user_id: 用户ID

        Returns:
            bool: 是否删除成功
        """
        # 删除聊天
        result = await self.chat_repository.delete_by_user_and_id(user_id, chat_id)
        return result

    async def get_user_chats(self, query_dto: ChatQueryDTO) -> ChatListDTO:
        """
        获取用户的聊天列表

        Args:
            query_dto: 聊天查询DTO

        Returns:
            ChatListDTO: 聊天列表DTO
        """
        skip = (query_dto.page - 1) * query_dto.limit

        chats, total = await self.chat_repository.list_by_user(
            user_id=query_dto.user_id, limit=query_dto.limit, offset=skip
        )

        # 转换为符合API文档的格式
        chat_items = [
            ChatListItemDTO(id=chat.id, title=chat.title, updated_at=chat.updated_at)
            for chat in chats
        ]

        return ChatListDTO(
            chats=chat_items, total=total, page=query_dto.page, limit=query_dto.limit
        )

    async def add_message(self, message_dto: MessageCreateDTO) -> MessageDTO:
        """
        添加消息

        Args:
            message_dto: 消息创建DTO

        Returns:
            MessageDTO: 消息DTO
        """
        # 检查聊天是否存在
        chat = await self.chat_repository.get_by_id(message_dto.chat_id)
        if not chat:
            raise NotFoundException("聊天会话不存在")

        # 检查用户是否有权限访问此聊天
        if chat.user_id != message_dto.user_id:
            raise ForbiddenException("无权访问此聊天")

        # 获取当前聊天中的消息数量，用于设置position
        message_count = await self.message_repository.count_by_chat(message_dto.chat_id)

        # 创建消息
        from app.db.models.message import MessageCreate, MessageRole, MessageStatus

        # 设置消息角色
        role = MessageRole.USER
        if message_dto.role == "system":
            role = MessageRole.SYSTEM
        elif message_dto.role == "assistant":
            role = MessageRole.ASSISTANT

        # 创建消息
        message_create = MessageCreate(
            chat_id=message_dto.chat_id,
            role=role,
            content=message_dto.content,
            status=(
                MessageStatus.PENDING
                if role == MessageRole.ASSISTANT
                else MessageStatus.COMPLETED
            ),
            model_id=message_dto.model_id,
        )

        # 添加消息
        message = await self.message_repository.create_message(message_create)

        # 设置position
        message.position = message_count + 1
        message = await self.message_repository.update(message)

        # 更新聊天的最后更新时间
        from app.db.models.chat import ChatUpdate

        # 获取当前聊天以保持标题不变
        current_chat = await self.chat_repository.get_by_id(message_dto.chat_id)
        if current_chat:
            chat_update = ChatUpdate(title=current_chat.title)
            await self.chat_repository.update_chat(message_dto.chat_id, chat_update)

        # 使相关的上下文缓存失效
        await self.cache_service.invalidate_context_cache(str(message_dto.chat_id))
        # 使聊天上下文缓存失效

        # 如果有文件ID，添加文件关联
        if message_dto.file_ids:
            for file_id in message_dto.file_ids:
                file = await self.file_repository.get_by_id_and_user(
                    file_id, message_dto.user_id
                )
                if file:
                    file.message_id = message.id
                    await self.file_repository.update(file)

        return self._convert_to_message_dto(message)

    async def get_chat_messages(self, query_dto: MessageQueryDTO) -> MessageListDTO:
        """
        获取聊天消息列表

        Args:
            query_dto: 消息查询DTO

        Returns:
            MessageListDTO: 消息列表DTO
        """
        # 计算分页参数
        skip = (query_dto.page - 1) * query_dto.limit

        # 检查用户是否有权限访问该聊天
        chat = await self.chat_repository.get_by_user_and_id(
            query_dto.user_id, query_dto.chat_id
        )
        if not chat:
            from app.utils.exceptions import NotFoundException

            raise NotFoundException("聊天会话不存在或您无权访问")

        # 获取消息列表和总数
        messages, total = await self.message_repository.list_by_chat_with_count(
            chat_id=query_dto.chat_id, limit=query_dto.limit, offset=skip
        )

        # 转换为DTO
        message_dtos = [self._convert_to_message_dto(message) for message in messages]

        return MessageListDTO(
            messages=message_dtos,
            total=total,
            page=query_dto.page,
            limit=query_dto.limit,
        )

    async def get_chat_detail(
        self, chat_id: uuid.UUID, user_id: uuid.UUID
    ) -> Optional[ChatDetailDTO]:
        """
        获取聊天详情

        Args:
            chat_id: 聊天ID
            user_id: 用户ID

        Returns:
            Optional[ChatDetailDTO]: 聊天详情DTO，如果聊天不存在或用户无权限则为None
        """
        # 获取聊天并检查权限
        chat = await self.chat_repository.get_by_user_and_id(user_id, chat_id)
        if not chat:
            return None

        # 创建聊天详情DTO
        return ChatDetailDTO(
            id=chat.id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
        )

    def _convert_to_chat_dto(self, chat: Chat) -> ChatDTO:
        """
        将聊天模型转换为DTO

        Args:
            chat: 聊天模型

        Returns:
            ChatDTO: 聊天DTO
        """
        last_message = None
        if hasattr(chat, "last_message") and chat.last_message:
            last_message = self._convert_to_message_dto(chat.last_message)

        return ChatDTO(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            last_message=last_message,
        )

    def _convert_to_message_dto(self, message: Message) -> MessageDTO:
        """
        将消息模型转换为DTO

        Args:
            message: 消息模型

        Returns:
            MessageDTO: 消息DTO
        """
        # 创建符合API文档的MessageDTO
        return MessageDTO(
            id=message.id,
            role=message.role.value,
            content=message.content,
            model_id=message.model_id,
            created_at=message.created_at,
            status=message.status,
            position=message.position,
            # 以下字段不在API文档中，但在内部服务中使用
            chat_id=message.chat_id,
            updated_at=message.updated_at,
            model_params={},  # 使用空字典
        )

    async def prepare_chat_context(self, chat_id: uuid.UUID) -> List[Dict[str, str]]:
        """
        准备聊天上下文，转换为适合模型API的格式，支持缓存

        Args:
            chat_id: 聊天ID

        Returns:
            List[Dict[str, str]]: 消息上下文列表，符合OpenAI格式
        """
        # 获取最近的消息
        messages = await self.message_repository.get_recent_messages(chat_id, limit=10)

        # 转换为OpenAI格式
        context: List[Dict[str, str]] = []

        # 尝试从缓存获取上下文
        cached_context = await self.cache_service.get_cached_context(
            str(chat_id), context
        )
        if cached_context:
            # 从缓存获取聊天上下文
            return cached_context

        # 添加系统消息（如果有）
        system_message = next(
            (m for m in messages if m.role == MessageRole.SYSTEM), None
        )
        if system_message:
            context.append({"role": "system", "content": system_message.content})

        # 添加用户和助手消息，按时间顺序
        for message in sorted(
            [m for m in messages if m.role != MessageRole.SYSTEM],
            key=lambda x: x.created_at,
        ):
            context.append(
                {
                    "role": "user" if message.role == MessageRole.USER else "assistant",
                    "content": message.content,
                }
            )

        # 如果没有系统消息，添加默认系统消息
        if not system_message:
            context.insert(0, {"role": "system", "content": "你是一个有用的助手。"})

        # 缓存处理后的上下文
        await self.cache_service.cache_context(str(chat_id), context, context)
        # 缓存聊天上下文

        return context

    async def update_message_content(
        self, message_id: uuid.UUID, content: str
    ) -> MessageDTO:
        """
        更新消息内容

        Args:
            message_id: 消息ID
            content: 新的内容

        Returns:
            MessageDTO: 更新后的消息DTO
        """
        # 获取消息
        message = await self.message_repository.get_by_id(message_id)
        if not message:
            from app.utils.exceptions import NotFoundException

            raise NotFoundException("消息不存在")

        # 创建更新对象
        from app.db.models.message import MessageUpdate

        update_data = {"content": content, "status": MessageStatus.COMPLETED}

        message_update = MessageUpdate(**update_data)

        # 更新消息
        updated_message = await self.message_repository.update_message(
            message_id, message_update
        )

        if not updated_message:
            from app.utils.exceptions import InternalServerErrorException

            raise InternalServerErrorException("更新消息内容失败")

        # 更新聊天的最后更新时间
        from app.db.models.chat import ChatUpdate

        # 获取当前聊天以保持标题不变
        current_chat = await self.chat_repository.get_by_id(message.chat_id)
        if current_chat:
            chat_update = ChatUpdate(title=current_chat.title)
            await self.chat_repository.update_chat(message.chat_id, chat_update)

        # 使相关的上下文缓存失效
        await self.cache_service.invalidate_context_cache(str(message.chat_id))
        # 使聊天上下文缓存失效

        return self._convert_to_message_dto(updated_message)

    async def delete_message(self, message_id: uuid.UUID) -> bool:
        """
        删除消息

        Args:
            message_id: 消息ID

        Returns:
            bool: 是否删除成功
        """
        # 获取消息以获取chat_id
        message = await self.message_repository.get_by_id(message_id)
        if not message:
            return False

        chat_id = message.chat_id

        # 删除消息
        result = await self.message_repository.delete(id=message_id)

        if result > 0:
            # 使相关的上下文缓存失效
            await self.cache_service.invalidate_context_cache(str(chat_id))
            # 使聊天上下文缓存失效

        return result > 0

    async def update_message_status(
        self, message_id: uuid.UUID, status: MessageStatus
    ) -> MessageDTO:
        """
        更新消息状态

        Args:
            message_id: 消息ID
            status: 新的状态

        Returns:
            MessageDTO: 更新后的消息DTO
        """
        # 获取消息
        message = await self.message_repository.get_by_id(message_id)
        if not message:
            from app.utils.exceptions import NotFoundException

            raise NotFoundException("消息不存在")

        # 创建更新对象
        from app.db.models.message import MessageUpdate

        message_update = MessageUpdate(content=None, status=status)

        # 更新消息
        updated_message = await self.message_repository.update_message(
            message_id, message_update
        )

        if not updated_message:
            from app.utils.exceptions import InternalServerErrorException

            raise InternalServerErrorException("更新消息状态失败")

        return self._convert_to_message_dto(updated_message)

    async def get_messages_for_model(
        self,
        chat_id: uuid.UUID,
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> List[Dict[str, str]]:
        """
        获取聊天历史并转换为适合模型API的格式，支持基于token的智能截断

        Args:
            chat_id: 聊天ID
            model_id: 模型ID，用于缓存键
            max_tokens: 最大token数量限制

        Returns:
            List[Dict[str, str]]: 消息上下文列表，符合OpenAI格式
        """
        # 获取最近的消息
        messages = await self.message_repository.get_recent_messages(chat_id, limit=20)

        # 转换为OpenAI格式
        context = []

        # 添加用户和助手消息，按时间顺序
        for message in sorted(
            [m for m in messages if m.role != MessageRole.SYSTEM],
            key=lambda x: x.position,
        ):
            # 跳过空消息
            if not message.content.strip():
                continue

            context.append(
                {
                    "role": "user" if message.role == MessageRole.USER else "assistant",
                    "content": message.content,
                }
            )

        # 如果指定了token限制，进行智能截断
        if max_tokens:
            original_count = len(context)
            context = self.token_counter.truncate_messages_by_tokens(
                context, max_tokens
            )
            truncated_count = len(context)

            if truncated_count < original_count:
                # 智能截断消息
                pass

            # 缓存截断后的上下文
            if model_id:
                await self.cache_service.cache_truncated_context(
                    str(chat_id), model_id, max_tokens, context
                )
                # 缓存截断上下文

        return context


def get_chat_service(
    session: AsyncSession = Depends(get_db),
    model_service: ModelService = Depends(get_model_service),
    cache_service: CacheService = Depends(get_cache_service),
    token_counter: TokenCounter = Depends(get_token_counter),
) -> ChatService:
    """
    获取聊天服务实例

    Args:
        session: 数据库会话
        model_service: 模型服务
        cache_service: 缓存服务
        token_counter: Token计数器

    Returns:
        ChatService: 聊天服务实例
    """
    return ChatService(session, model_service, cache_service, token_counter)
