"""Book club AI service for business logic."""

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.book_club_ai_repo import BookClubAIRepository
from app.repositories.book_club_repo import BookClubRepository
from app.schemas.book_club_ai import (
    BookClubAIChatMessageResponse,
    BookClubAIChatSessionDetailResponse,
    BookClubAIChatSessionResponse,
    BookClubAICreditsResponse,
    BookClubAIModelResponse,
)


class BookClubAIService:
    """Service for book club AI operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookClubAIRepository(db)
        self.club_repo = BookClubRepository(db)

    # Credits
    async def get_credits(self, club_id: uuid.UUID, user: User) -> BookClubAICreditsResponse:
        await self._check_membership(club_id, user)
        credits = await self.repo.get_credits(club_id)
        if not credits:
            # Auto-create default credits record
            credits = await self.repo.create_credits(club_id)
        return BookClubAICreditsResponse.model_validate(credits)

    async def update_credits(self, club_id: uuid.UUID, data, user: User) -> BookClubAICreditsResponse:
        await self._check_club_admin(club_id, user)
        credits = await self.repo.get_credits(club_id)
        if not credits:
            credits = await self.repo.create_credits(club_id, **data.model_dump(exclude_unset=True))
        else:
            update_data = data.model_dump(exclude_unset=True)
            credits = await self.repo.update_credits(club_id, **update_data)
        return BookClubAICreditsResponse.model_validate(credits)

    # Models
    async def list_models(self, club_id: uuid.UUID, user: User) -> list[BookClubAIModelResponse]:
        await self._check_membership(club_id, user)
        models = await self.repo.list_models(club_id, enabled_only=True)
        return [BookClubAIModelResponse.model_validate(m) for m in models]

    async def create_or_update_model(self, club_id: uuid.UUID, data, user: User) -> BookClubAIModelResponse:
        await self._check_club_admin(club_id, user)
        # Check if model with same name already exists for this club
        existing = await self.repo.get_model_by_name(club_id, data.model_name)
        if existing:
            update_data = data.model_dump(exclude={"model_name", "model_provider"}, exclude_unset=True)
            model = await self.repo.update_model(existing.id, **update_data)
        else:
            model = await self.repo.create_model(
                club_id=club_id, created_by=user.id, **data.model_dump(),
            )
        return BookClubAIModelResponse.model_validate(model)

    # Sessions
    async def create_session(self, club_id: uuid.UUID, data, user: User) -> BookClubAIChatSessionResponse:
        await self._check_membership(club_id, user)

        # Check credits
        credits = await self.repo.get_credits(club_id)
        if credits and credits.remaining_credits <= 0:
            raise HTTPException(status_code=402, detail="Insufficient AI credits")

        session = await self.repo.create_session(
            club_id=club_id,
            created_by=user.id,
            session_name=data.session_name,
            model_name=data.model_name,
            book_id=data.book_id,
            is_public=data.is_public,
            participant_count=1,
        )
        # Add creator as first participant
        await self.repo.add_participant(session.id, user.id)
        return BookClubAIChatSessionResponse.model_validate(session)

    async def list_sessions(self, club_id: uuid.UUID, user: User, page: int = 1, limit: int = 20):
        await self._check_membership(club_id, user)
        sessions, total = await self.repo.list_sessions(club_id, page, limit)
        return [BookClubAIChatSessionResponse.model_validate(s) for s in sessions], total

    async def get_session_with_messages(self, club_id: uuid.UUID, session_id: uuid.UUID, user: User) -> BookClubAIChatSessionDetailResponse:
        await self._check_membership(club_id, user)
        session = await self.repo.get_session_with_details(session_id)
        if not session or session.club_id != club_id:
            raise HTTPException(status_code=404, detail="AI chat session not found")

        # Auto-join participant if not already
        participant = await self.repo.get_participant(session_id, user.id)
        if not participant:
            await self.repo.add_participant(session_id, user.id)
            session.participant_count += 1
            await self.db.flush()

        return BookClubAIChatSessionDetailResponse.model_validate(session)

    # Messages
    async def send_message(self, club_id: uuid.UUID, session_id: uuid.UUID, data, user: User) -> BookClubAIChatMessageResponse:
        await self._check_membership(club_id, user)

        session = await self.repo.get_session(session_id)
        if not session or session.club_id != club_id:
            raise HTTPException(status_code=404, detail="AI chat session not found")
        if not session.is_active:
            raise HTTPException(status_code=400, detail="Chat session is no longer active")

        # Ensure user is a participant
        participant = await self.repo.get_participant(session_id, user.id)
        if not participant:
            await self.repo.add_participant(session_id, user.id)
            session.participant_count += 1

        # Check and deduct credits for AI messages
        credits = await self.repo.get_credits(club_id)
        if data.message_type == "user" and credits and credits.remaining_credits <= 0:
            raise HTTPException(status_code=402, detail="Insufficient AI credits")

        # Create message
        message = await self.repo.create_message(
            session_id=session_id,
            user_id=user.id,
            message_type=data.message_type,
            content=data.content,
        )

        # Update session totals
        session.total_messages += 1
        await self.db.flush()

        # Deduct credit and log transaction for user messages
        if data.message_type == "user" and credits:
            balance_before = credits.remaining_credits
            credits.used_credits += 1
            credits.remaining_credits -= 1
            await self.db.flush()

            await self.repo.create_credit_transaction(
                club_id=club_id,
                created_by=user.id,
                session_id=session_id,
                message_id=message.id,
                transaction_type="debit",
                amount=1,
                balance_before=balance_before,
                balance_after=credits.remaining_credits,
                description=f"AI chat message in session '{session.session_name}'",
            )

        return BookClubAIChatMessageResponse.model_validate(message)

    # Access control helpers
    async def _check_membership(self, club_id: uuid.UUID, user: User):
        member = await self.club_repo.get_member(club_id, user.id)
        if not member and not user.is_admin:
            raise HTTPException(status_code=403, detail="Not a member of this club")
        return member

    async def _check_club_admin(self, club_id: uuid.UUID, user: User):
        club = await self.club_repo.get_by_id(club_id)
        if not club:
            raise HTTPException(status_code=404, detail="Book club not found")
        if user.is_admin:
            return club
        member = await self.club_repo.get_member(club_id, user.id)
        if not member or member.role not in ("owner", "admin", "moderator"):
            raise HTTPException(status_code=403, detail="Requires club admin/owner role")
        return club
