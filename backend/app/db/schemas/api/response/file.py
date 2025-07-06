#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件相关API响应模型
"""

from pydantic import BaseModel, Field


class FileResponse(BaseModel):
    """文件信息响应"""

    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    download_url: str = Field(..., description="下载链接")


class FileUploadResponse(BaseModel):
    """文件上传响应"""

    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")


class FileInfoResponse(BaseModel):
    """文件信息响应"""

    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    file_type: str = Field(..., description="文件类型")
    download_url: str = Field(..., description="下载URL")
    file_size: int = Field(..., description="文件大小(字节)")
