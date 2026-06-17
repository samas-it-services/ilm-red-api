"""Admin settings Pydantic schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AdminSettingResponse(BaseModel):
    """Admin setting response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    setting_key: str
    setting_value: Any
    description: str | None = None
    updated_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class AdminSettingUpdate(BaseModel):
    """Admin setting update request schema."""

    value: Any = Field(..., description="Setting value (JSON)")
    description: str | None = Field(None, description="Setting description")


class MysticalMessageResponse(BaseModel):
    """Mystical message response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    message: str
    category: str | None = None
    is_active: bool
    created_at: datetime


class MysticalMessageStats(BaseModel):
    """Stats for mystical messages."""

    total: int
    active: int
    inactive: int
    categories: list[str]
