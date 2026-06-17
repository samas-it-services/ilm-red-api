"""Expert configuration schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Pagination


# Request Schemas


class ExpertConfigCreate(BaseModel):
    """Create a new expert configuration."""

    name: str = Field(..., min_length=1, max_length=200)
    category: str = Field(..., min_length=1, max_length=100)
    field: str | None = Field(default=None, max_length=200)
    traits: list = Field(default_factory=list)
    preferred_model: str | None = Field(default=None, max_length=50)
    preferred_provider: str | None = Field(default=None, max_length=50)
    system_prompt_template: str | None = None
    model_config_data: dict = Field(default_factory=dict)
    is_active: bool = True

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Islamic Finance Expert",
                "category": "fiqh",
                "field": "Islamic Finance",
                "traits": ["analytical", "patient", "scholarly"],
                "preferred_model": "gpt-4",
                "preferred_provider": "openai",
                "system_prompt_template": "You are an expert in Islamic finance...",
                "model_config_data": {"temperature": 0.7, "max_tokens": 2048},
                "is_active": True,
            }
        }
    )


class ExpertConfigUpdate(BaseModel):
    """Update an expert configuration."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    field: str | None = Field(default=None, max_length=200)
    traits: list | None = None
    preferred_model: str | None = Field(default=None, max_length=50)
    preferred_provider: str | None = Field(default=None, max_length=50)
    system_prompt_template: str | None = None
    model_config_data: dict | None = None
    is_active: bool | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Updated Expert Name",
                "is_active": False,
            }
        }
    )


# Response Schemas


class ExpertConfigResponse(BaseModel):
    """Expert configuration response."""

    id: UUID
    name: str
    category: str
    field: str | None
    traits: list
    preferred_model: str | None
    preferred_provider: str | None
    system_prompt_template: str | None
    model_config_data: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpertConfigListItem(BaseModel):
    """Simplified expert configuration for list responses."""

    id: UUID
    name: str
    category: str
    field: str | None
    preferred_model: str | None
    preferred_provider: str | None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExpertConfigListResponse(BaseModel):
    """Paginated expert configuration list response."""

    data: list[ExpertConfigListItem]
    pagination: Pagination
