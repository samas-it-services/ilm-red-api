"""Book club AI Pydantic schemas."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# Credits
class BookClubAICreditsResponse(BaseModel):
    """AI credits balance response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    club_id: uuid.UUID
    total_credits: int
    used_credits: int
    remaining_credits: int
    monthly_limit: int
    reset_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class BookClubAICreditsUpdate(BaseModel):
    """Update AI credits request."""
    total_credits: int | None = Field(None, ge=0)
    remaining_credits: int | None = Field(None, ge=0)
    monthly_limit: int | None = Field(None, ge=0)
    reset_date: datetime | None = None


# Credit Transactions
class BookClubAICreditTransactionResponse(BaseModel):
    """AI credit transaction response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    club_id: uuid.UUID
    created_by: uuid.UUID
    session_id: uuid.UUID | None = None
    message_id: uuid.UUID | None = None
    transaction_type: str
    amount: int
    balance_before: int
    balance_after: int
    description: str | None = None
    created_at: datetime


# Models
class BookClubAIModelCreate(BaseModel):
    """Create AI model config request."""
    model_name: str = Field(..., min_length=1, max_length=100)
    model_display_name: str = Field(..., min_length=1, max_length=200)
    model_provider: str = Field(..., min_length=1, max_length=100)
    is_enabled: bool = True
    input_cost_per_1m_tokens: Decimal = Field(default=Decimal("0"), ge=0)
    output_cost_per_1m_tokens: Decimal = Field(default=Decimal("0"), ge=0)


class BookClubAIModelUpdate(BaseModel):
    """Update AI model config request."""
    model_display_name: str | None = Field(None, min_length=1, max_length=200)
    is_enabled: bool | None = None
    input_cost_per_1m_tokens: Decimal | None = Field(None, ge=0)
    output_cost_per_1m_tokens: Decimal | None = Field(None, ge=0)


class BookClubAIModelResponse(BaseModel):
    """AI model config response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    club_id: uuid.UUID
    model_name: str
    model_display_name: str
    model_provider: str
    is_enabled: bool
    input_cost_per_1m_tokens: Decimal
    output_cost_per_1m_tokens: Decimal
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Chat Sessions
class BookClubAIChatSessionCreate(BaseModel):
    """Create AI chat session request."""
    session_name: str = Field(..., min_length=1, max_length=300)
    model_name: str = Field(..., min_length=1, max_length=100)
    book_id: uuid.UUID | None = None
    is_public: bool = False


class BookClubAIChatSessionResponse(BaseModel):
    """AI chat session response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    club_id: uuid.UUID
    book_id: uuid.UUID | None = None
    created_by: uuid.UUID
    session_name: str
    model_name: str
    participant_count: int
    total_messages: int
    total_cost: Decimal
    is_active: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime


# Chat Messages
class BookClubAIChatMessageCreate(BaseModel):
    """Create AI chat message request."""
    content: str = Field(..., min_length=1)
    message_type: str = Field("user", pattern="^(user|ai|system)$")


class BookClubAIChatMessageResponse(BaseModel):
    """AI chat message response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    message_type: str
    content: str
    model_used: str | None = None
    input_tokens: int
    output_tokens: int
    cost: Decimal
    created_at: datetime


# Chat Participants
class BookClubAIChatParticipantResponse(BaseModel):
    """AI chat participant response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    is_active: bool
    joined_at: datetime
    last_read_at: datetime | None = None


# Session with messages (composite response)
class BookClubAIChatSessionDetailResponse(BaseModel):
    """AI chat session with messages and participants."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    club_id: uuid.UUID
    book_id: uuid.UUID | None = None
    created_by: uuid.UUID
    session_name: str
    model_name: str
    participant_count: int
    total_messages: int
    total_cost: Decimal
    is_active: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime
    messages: list[BookClubAIChatMessageResponse] = []
    participants: list[BookClubAIChatParticipantResponse] = []
