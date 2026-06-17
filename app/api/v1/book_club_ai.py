"""Book club AI API endpoints."""

import uuid

from fastapi import APIRouter, Query

from app.api.v1.deps import CurrentUser, DBSession
from app.schemas.book_club_ai import (
    BookClubAIChatMessageCreate,
    BookClubAIChatMessageResponse,
    BookClubAIChatSessionCreate,
    BookClubAIChatSessionDetailResponse,
    BookClubAIChatSessionResponse,
    BookClubAICreditsResponse,
    BookClubAICreditsUpdate,
    BookClubAIModelCreate,
    BookClubAIModelResponse,
)
from app.schemas.common import PaginatedResponse, create_pagination
from app.services.book_club_ai_service import BookClubAIService

router = APIRouter()


# Credits
@router.get("/{club_id}/ai/credits", response_model=BookClubAICreditsResponse, summary="Get club AI credits")
async def get_credits(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> BookClubAICreditsResponse:
    service = BookClubAIService(db)
    return await service.get_credits(club_id, current_user)


@router.put("/{club_id}/ai/credits", response_model=BookClubAICreditsResponse, summary="Update club AI credits")
async def update_credits(club_id: uuid.UUID, data: BookClubAICreditsUpdate, db: DBSession, current_user: CurrentUser) -> BookClubAICreditsResponse:
    service = BookClubAIService(db)
    return await service.update_credits(club_id, data, current_user)


# Models
@router.get("/{club_id}/ai/models", response_model=list[BookClubAIModelResponse], summary="List enabled AI models")
async def list_models(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> list[BookClubAIModelResponse]:
    service = BookClubAIService(db)
    return await service.list_models(club_id, current_user)


@router.put("/{club_id}/ai/models", response_model=BookClubAIModelResponse, summary="Create or update AI model config")
async def create_or_update_model(club_id: uuid.UUID, data: BookClubAIModelCreate, db: DBSession, current_user: CurrentUser) -> BookClubAIModelResponse:
    service = BookClubAIService(db)
    return await service.create_or_update_model(club_id, data, current_user)


# Sessions
@router.post("/{club_id}/ai/sessions", response_model=BookClubAIChatSessionResponse, status_code=201, summary="Create AI chat session")
async def create_session(club_id: uuid.UUID, data: BookClubAIChatSessionCreate, db: DBSession, current_user: CurrentUser) -> BookClubAIChatSessionResponse:
    service = BookClubAIService(db)
    return await service.create_session(club_id, data, current_user)


@router.get("/{club_id}/ai/sessions", response_model=PaginatedResponse[BookClubAIChatSessionResponse], summary="List AI chat sessions")
async def list_sessions(club_id: uuid.UUID, db: DBSession, current_user: CurrentUser, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    service = BookClubAIService(db)
    sessions, total = await service.list_sessions(club_id, current_user, page, limit)
    return PaginatedResponse(data=sessions, pagination=create_pagination(page, limit, total))


@router.get("/{club_id}/ai/sessions/{session_id}", response_model=BookClubAIChatSessionDetailResponse, summary="Get AI chat session with messages")
async def get_session(club_id: uuid.UUID, session_id: uuid.UUID, db: DBSession, current_user: CurrentUser) -> BookClubAIChatSessionDetailResponse:
    service = BookClubAIService(db)
    return await service.get_session_with_messages(club_id, session_id, current_user)


# Messages
@router.post("/{club_id}/ai/sessions/{session_id}/messages", response_model=BookClubAIChatMessageResponse, status_code=201, summary="Send message in AI chat session")
async def send_message(club_id: uuid.UUID, session_id: uuid.UUID, data: BookClubAIChatMessageCreate, db: DBSession, current_user: CurrentUser) -> BookClubAIChatMessageResponse:
    service = BookClubAIService(db)
    return await service.send_message(club_id, session_id, data, current_user)
