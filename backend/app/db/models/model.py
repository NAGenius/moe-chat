#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模型配置模型定义
使用SQLModel简化SQLAlchemy操作
"""

from datetime import UTC, datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON as SQLAlchemyJSON
from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

# 删除不再需要的导入
# if TYPE_CHECKING:
#     from app.db.models.chat import Chat


# 基础模型
class ModelBase(SQLModel):
    """模型配置基础模型"""

    display_name: str = Field(..., description="显示名称")
    description: Optional[str] = Field(default=None, description="模型描述")
    is_active: bool = Field(default=True, description="是否可用")
    max_context_tokens: int = Field(default=4096, description="最大上下文长度")
    has_thinking: bool = Field(default=False, description="是否支持思考过程")
    default_params: Optional[Dict[str, Any]] = Field(
        default=None, description="默认参数", sa_column=Column(SQLAlchemyJSON)
    )
    service_url: Optional[str] = Field(
        default=None, description="模型服务URL，为空则使用默认URL"
    )


# 数据库表模型
class Model(ModelBase, table=True):
    """模型配置数据库模型"""

    __tablename__ = "models"  # type: ignore

    id: str = Field(primary_key=True, index=True, description="模型配置唯一标识")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True)),
        description="创建时间",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), onupdate=lambda: datetime.now(UTC)),
        description="更新时间",
    )

    def __repr__(self) -> str:
        return f"<ModelConfig {self.id}>"


# 操作模型
class ModelCreate(ModelBase):
    """模型配置创建模型"""

    id: str = Field(..., description="模型配置唯一标识")


class ModelUpdate(SQLModel):
    """模型配置更新模型"""

    display_name: Optional[str] = Field(None, description="显示名称")
    description: Optional[str] = Field(None, description="模型描述")
    is_active: Optional[bool] = Field(None, description="是否可用")
    max_context_tokens: Optional[int] = Field(None, description="最大上下文长度")
    has_thinking: Optional[bool] = Field(None, description="是否支持思考过程")
    default_params: Optional[Dict[str, Any]] = Field(
        None, description="默认参数", sa_column=Column(SQLAlchemyJSON)
    )


class ModelRead(ModelBase):
    """模型配置读取模型"""

    id: str = Field(..., description="模型配置唯一标识")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
