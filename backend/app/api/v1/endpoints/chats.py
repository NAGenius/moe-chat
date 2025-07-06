#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
聊天相关API端点
"""

import json
import time
from typing import AsyncGenerator
from uuid import UUID

from app.api.deps import get_current_user
from app.db.models.message import MessageRole, MessageStatus
from app.db.models.user import User
from app.db.schemas.api.request.chat import (
    ChatCreateRequest,
    ChatUpdateRequest,
    MessageCreateRequest,
)
from app.db.schemas.api.response.base import (
    ResponseBase,
    SimpleResponse,
)
from app.db.schemas.api.response.chat import (
    ChatCreateResponse,
    ChatListItemResponse,
    ChatListResponse,
    ChatResponse,
    MessageCreateResponse,
    MessageListResponse,
    MessageResponse,
)
from app.db.schemas.dto.input.chat_dto import (
    ChatCreateDTO,
    ChatQueryDTO,
    ChatUpdateDTO,
    MessageCreateDTO,
    MessageQueryDTO,
)
from app.services.chat_service import ChatService, get_chat_service
from app.services.model_service import ModelService, get_model_service
from app.utils.exceptions import (
    BadRequestException,
    NotFoundException,
)
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

# 获取日志记录器
logger = get_logger(__name__)

router = APIRouter()


@router.post("", response_model=ResponseBase[ChatCreateResponse])
async def create_chat(
    chat_request: ChatCreateRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ResponseBase[ChatCreateResponse]:
    """创建聊天会话"""
    chat_dto = ChatCreateDTO(
        user_id=current_user.id,
        title=chat_request.title,
    )
    
    chat = await chat_service.create_chat(chat_dto)
    
    return ResponseBase[ChatCreateResponse](
        code=status.HTTP_200_OK,
        message="请求成功",
        data=ChatCreateResponse(chat_id=str(chat.id)),
    )

@router.get("", response_model=ResponseBase[ChatListResponse])
async def get_chats(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ResponseBase[ChatListResponse]:
    """获取聊天会话列表"""
    query_dto = ChatQueryDTO(user_id=current_user.id, page=page, limit=limit)
    chat_list = await chat_service.get_user_chats(query_dto)

    # 将 ChatDTO 转换为 ChatListItemResponse
    chat_items = [
        ChatListItemResponse(
            chat_id=str(chat.id),
            title=chat.title,
            updated_at=chat.updated_at,
        )
        for chat in chat_list.chats
    ]

    return ResponseBase[ChatListResponse](
        code=status.HTTP_200_OK,
        message="请求成功",
        data=ChatListResponse(
            chats=chat_items,
            total=chat_list.total,
            page=chat_list.page,
            limit=chat_list.limit,
        ),
    )


@router.post("/{chat_id}/messages", response_model=ResponseBase[MessageCreateResponse])
async def send_message(
    chat_id: UUID,
    message_request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    model_service: ModelService = Depends(get_model_service),
) -> ResponseBase[MessageCreateResponse]:
    """发送消息（非流式）"""
    # 验证模型是否存在且可用
    model = await model_service.get_model_by_id(message_request.model_id)
    if not model:
        raise NotFoundException("请求的模型不存在或不可用")
    if not model.is_active:
        raise BadRequestException("请求的模型当前不可用")

    # 创建用户消息
    user_message_dto = MessageCreateDTO(
        user_id=current_user.id,
        chat_id=chat_id,
        role=MessageRole.USER,
        content=message_request.content,
        model_id=None,
        file_ids=message_request.file_ids,
    )

    # 添加用户消息到数据库
    user_message = await chat_service.add_message(user_message_dto)
    logger.info(f"用户消息已保存，ID: {user_message.id}")

    # 创建助手消息（状态为pending）
    assistant_message_dto = MessageCreateDTO(
        user_id=current_user.id,
        chat_id=chat_id,
        role=MessageRole.ASSISTANT,
        content="",
        model_id=message_request.model_id,
        file_ids=None,
    )

    assistant_message = await chat_service.add_message(assistant_message_dto)
    logger.info(f"助手消息已创建，ID: {assistant_message.id}")

    try:
        # 获取聊天上下文
        context = await chat_service.get_messages_for_model(
            chat_id, message_request.model_id, model.max_context_tokens
        )

        # 添加用户系统提示到上下文开头
        if current_user.system_prompt:
            system_message = {"role": "system", "content": current_user.system_prompt}
            context.insert(0, system_message)
        print(context)
        model_params = {
            "temperature": 0.7,
            "top_p": 1.0,
            "max_tokens": None,
        }

        if model.default_params:
            model_params.update(model.default_params)

        # 调用模型生成响应（非流式）
        temperature = model_params.get("temperature", 0.7)
        top_p = model_params.get("top_p", 1.0)
        max_tokens = model_params.get("max_tokens")

        response = await model_service.generate(
            model_id=message_request.model_id,
            messages=context,
            temperature=float(temperature) if temperature is not None else 0.7,
            top_p=float(top_p) if top_p is not None else 1.0,
            max_tokens=int(max_tokens) if max_tokens is not None else None,
        )

        # 提取生成的内容
        generated_content = ""
        if response.get("choices") and len(response["choices"]) > 0:
            generated_content = (
                response["choices"][0].get("message", {}).get("content", "")
            )

        if not generated_content:
            generated_content = "抱歉，模型没有生成有效的回复。"

        # 更新助手消息内容
        await chat_service.update_message_content(
            assistant_message.id, generated_content
        )
        logger.info(f"助手消息已更新，内容长度: {len(generated_content)}")

        # 如果响应包含专家信息，更新专家统计
        if response.get("expert_info") and response["expert_info"].get("usage"):
            try:
                expert_usage = response["expert_info"]["usage"]
                model_service.update_expert_stats(expert_usage)
                logger.info(f"已更新专家统计信息，专家数: {len(expert_usage)}")
            except Exception as expert_error:
                logger.error(f"更新专家统计失败: {str(expert_error)}")

        return ResponseBase[MessageCreateResponse](
            code=status.HTTP_200_OK,
            message="请求成功",
            data=MessageCreateResponse(content=generated_content),
        )

    except Exception as e:
        logger.error(f"生成回复失败: {str(e)}")
        # 更新助手消息状态为错误
        await chat_service.update_message_status(
            assistant_message.id, MessageStatus.ERROR
        )
        # 重新抛出异常让全局异常处理器处理
        raise


@router.post("/{chat_id}/messages/stream")
async def send_message_stream(
    chat_id: UUID,
    message_request: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    model_service: ModelService = Depends(get_model_service),
) -> StreamingResponse:
    """发送消息（流式）"""
    # 验证模型是否存在且可用
    model = await model_service.get_model_by_id(message_request.model_id)
    if not model:
        raise NotFoundException("请求的模型不存在或不可用")
    if not model.is_active:
        raise BadRequestException("请求的模型当前不可用")

    async def generate_stream_response() -> AsyncGenerator[str, None]:
        """生成流式响应"""
        assistant_message = None
        completion_id = None
        try:
            # 创建用户消息
            user_message_dto = MessageCreateDTO(
                user_id=current_user.id,
                chat_id=chat_id,
                role=MessageRole.USER,
                content=message_request.content,
                model_id=None,
                file_ids=message_request.file_ids,
            )

            # 添加用户消息到数据库
            user_message = await chat_service.add_message(user_message_dto)
            logger.info(f"用户消息已保存，ID: {user_message.id}")

            # 创建助手消息（状态为pending）
            assistant_message_dto = MessageCreateDTO(
                user_id=current_user.id,
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content="",
                model_id=message_request.model_id,
                file_ids=None,
            )

            assistant_message = await chat_service.add_message(assistant_message_dto)
            logger.info(f"助手消息已创建，ID: {assistant_message.id}")

            # 获取聊天上下文
            context = await chat_service.get_messages_for_model(
                chat_id, message_request.model_id, model.max_context_tokens
            )

            # 添加用户系统提示到上下文开头
            if current_user.system_prompt:
                system_message = {
                    "role": "system",
                    "content": current_user.system_prompt,
                }
                context.insert(0, system_message)

            print(context)
            model_params = {
                "temperature": 0.7,
                "top_p": 1.0,
                "max_tokens": None,
            }

            # 如果模型有默认参数，使用它们覆盖默认值（不包含max_context_tokens）
            if model.default_params:
                model_params.update(model.default_params)

            # 生成唯一的completion ID
            completion_id = f"chatcmpl-{int(time.time())}{assistant_message.id.hex[:8]}"
            created_timestamp = int(time.time())

            # 发送开始响应
            start_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_timestamp,
                "model": message_request.model_id,
                "choices": [
                    {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(start_chunk)}\n\n"

            # 累积生成的内容
            accumulated_content = ""

            # 调用模型生成响应（流式）
            temperature = model_params.get("temperature", 0.7)
            top_p = model_params.get("top_p", 1.0)
            max_tokens = model_params.get("max_tokens")

            async for content_chunk in model_service.generate_stream(
                model_id=message_request.model_id,
                messages=context,
                temperature=float(temperature) if temperature is not None else 0.7,
                top_p=float(top_p) if top_p is not None else 1.0,
                max_tokens=int(max_tokens) if max_tokens is not None else None,
            ):
                if content_chunk:
                    accumulated_content += content_chunk

                    # 发送内容增量
                    content_chunk_data = {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created_timestamp,
                        "model": message_request.model_id,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": content_chunk},
                                "finish_reason": None,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(content_chunk_data)}\n\n"

            # 更新助手消息内容
            if accumulated_content:
                await chat_service.update_message_content(
                    assistant_message.id, accumulated_content
                )
                logger.info(f"助手消息已更新，内容长度: {len(accumulated_content)}")

            # 发送完成响应
            finish_chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created_timestamp,
                "model": message_request.model_id,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(finish_chunk)}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"流式生成回复失败: {str(e)}")

            # 如果助手消息已创建，更新其状态为错误
            if assistant_message:
                try:
                    await chat_service.update_message_status(
                        assistant_message.id, MessageStatus.ERROR
                    )
                except Exception as update_error:
                    logger.error(f"更新消息状态失败: {str(update_error)}")

            # 发送错误响应
            error_chunk = {
                "id": (
                    completion_id
                    if completion_id is not None
                    else f"chatcmpl-error-{int(time.time())}"
                ),
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": message_request.model_id,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": f"错误: {str(e)}"},
                        "finish_reason": "error",
                    }
                ],
                "error": {"message": str(e), "type": "generation_failed", "code": 500},
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_stream_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )


@router.get("/{chat_id}", response_model=ResponseBase[ChatResponse])
async def get_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ResponseBase[ChatResponse]:
    """获取聊天会话详情"""
    chat = await chat_service.get_chat_by_id(chat_id, current_user.id)
    if not chat:
        raise NotFoundException("聊天会话不存在")

    return ResponseBase[ChatResponse](
        code=status.HTTP_200_OK,
        message="请求成功",
        data=ChatResponse(id=chat.id, title=chat.title),
    )

@router.delete("/{chat_id}", response_model=SimpleResponse)
async def delete_chat(
    chat_id: UUID,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> SimpleResponse:
    """删除聊天会话"""
    success = await chat_service.delete_chat(chat_id, current_user.id)
    if not success:
        raise NotFoundException("聊天会话不存在")

    return SimpleResponse(code=status.HTTP_200_OK, message="请求成功")


@router.get("/{chat_id}/messages", response_model=ResponseBase[MessageListResponse])
async def get_chat_messages(
    chat_id: UUID,
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
) -> ResponseBase[MessageListResponse]:
    """获取聊天消息列表"""
    query_dto = MessageQueryDTO(
        user_id=current_user.id, chat_id=chat_id, page=page, limit=limit
    )
    message_list = await chat_service.get_chat_messages(query_dto)

    # 将 MessageDTO 转换为 MessageResponse
    message_items = [
        MessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            model_id=message.model_id,
            created_at=message.created_at,
            status=message.status,
            position=message.position if message.position is not None else 0,
        )
        for message in message_list.messages
    ]

    return ResponseBase[MessageListResponse](
        code=status.HTTP_200_OK,
        message="请求成功",
        data=MessageListResponse(
            messages=message_items,
            total=message_list.total,
            page=message_list.page,
            limit=message_list.limit,
        ),
    )
