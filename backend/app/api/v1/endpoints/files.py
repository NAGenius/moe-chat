#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件API端点
"""

import uuid
from typing import Any, Dict

from app.api.deps import get_current_active_user
from app.db.database import db_context
from app.db.models.user import User
from app.db.schemas.api.response.base import success_response
from app.db.schemas.api.response.file import FileInfoResponse, FileUploadResponse
from app.services.file_service import FileService
from app.utils.exceptions import BadRequestException, NotFoundException
from app.utils.logger import get_logger
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

router = APIRouter()
logger = get_logger(__name__)


@router.post("", summary="上传文件")
async def upload_file(
    file: UploadFile = File(...), current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    上传文件用于聊天。

    参数:
        - file: 要上传的文件（≤2MB）

    返回:
        - 文件信息
    """
    async with db_context() as session:
        file_service = FileService(session)

        try:
            # 使用文件服务上传文件
            file_db, _ = await file_service.upload_file(
                file=file, user_id=current_user.id, max_size=2 * 1024 * 1024  # 2MB
            )
        except ValueError as e:
            raise BadRequestException(str(e))

    # 转换为API响应
    response = FileUploadResponse(
        file_id=str(file_db.id), filename=file_db.filename, file_type=file_db.file_type
    )

    return success_response(data=response.dict())


@router.get("/{file_id}", summary="获取文件信息")
async def get_file_info(
    file_id: uuid.UUID, current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    获取已上传文件的信息。

    参数:
        - file_id: 文件ID

    返回:
        - 文件信息
    """
    async with db_context() as session:
        file_service = FileService(session)
        file = await file_service.get_file_by_id(file_id, current_user.id)

    # 转换为API响应
    response = FileInfoResponse(
        file_id=str(file.id),
        filename=file.filename,
        file_type=file.file_type,
        download_url=f"/api/v1/file/{file.id}/download",
        file_size=file.file_size,
    )

    return success_response(data=response.dict())


@router.get("/{file_id}/download", summary="下载文件")
async def download_file(
    file_id: uuid.UUID, current_user: User = Depends(get_current_active_user)
) -> FileResponse:
    """
    下载已上传的文件。

    参数:
        - file_id: 文件ID

    返回:
        - 文件内容（二进制）
    """
    async with db_context() as session:
        file_service = FileService(session)
        file = await file_service.get_file_by_id(file_id, current_user.id)

    # 检查文件是否存在
    if not await file_service.verify_file_exists(file.file_path):
        logger.error(f"文件不存在: {file.file_path}")
        raise NotFoundException("文件不存在")

    return FileResponse(
        path=file.file_path,
        filename=file.filename,
        media_type=file.file_type or "application/octet-stream",
    )
