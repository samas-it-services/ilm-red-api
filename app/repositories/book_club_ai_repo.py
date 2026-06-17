"""Book club AI repository for database operations."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.book_club_ai import (
    BookClubAIChatMessage,
    BookClubAIChatParticipant,
    BookClubAIChatSession,
    BookClubAICreditTransaction,
    BookClubAICredits,
    BookClubAIModel,
)


class BookClubAIRepository:
    """Repository for book club AI database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Credits
    async def get_credits(self, club_id: uuid.UUID) -> BookClubAICredits | None:
        stmt = select(BookClubAICredits).where(BookClubAICredits.club_id == club_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_credits(self, club_id: uuid.UUID, **kwargs) -> BookClubAICredits:
        credits = BookClubAICredits(club_id=club_id, **kwargs)
        self.db.add(credits)
        await self.db.flush()
        await self.db.refresh(credits)
        return credits

    async def update_credits(self, club_id: uuid.UUID, **kwargs) -> BookClubAICredits | None:
        credits = await self.get_credits(club_id)
        if credits:
            for key, value in kwargs.items():
                if hasattr(credits, key) and value is not None:
                    setattr(credits, key, value)
            await self.db.flush()
            await self.db.refresh(credits)
        return credits

    # Credit Transactions
    async def create_credit_transaction(self, **kwargs) -> BookClubAICreditTransaction:
        transaction = BookClubAICreditTransaction(**kwargs)
        self.db.add(transaction)
        await self.db.flush()
        await self.db.refresh(transaction)
        return transaction

    async def list_credit_transactions(self, club_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[BookClubAICreditTransaction], int]:
        count_stmt = select(func.count()).select_from(BookClubAICreditTransaction).where(BookClubAICreditTransaction.club_id == club_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = (
            select(BookClubAICreditTransaction)
            .where(BookClubAICreditTransaction.club_id == club_id)
            .order_by(BookClubAICreditTransaction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    # Models
    async def list_models(self, club_id: uuid.UUID, enabled_only: bool = False) -> list[BookClubAIModel]:
        stmt = select(BookClubAIModel).where(BookClubAIModel.club_id == club_id)
        if enabled_only:
            stmt = stmt.where(BookClubAIModel.is_enabled.is_(True))
        stmt = stmt.order_by(BookClubAIModel.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_model_by_name(self, club_id: uuid.UUID, model_name: str) -> BookClubAIModel | None:
        stmt = select(BookClubAIModel).where(
            BookClubAIModel.club_id == club_id, BookClubAIModel.model_name == model_name
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_model(self, **kwargs) -> BookClubAIModel:
        model = BookClubAIModel(**kwargs)
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def update_model(self, model_id: uuid.UUID, **kwargs) -> BookClubAIModel | None:
        stmt = select(BookClubAIModel).where(BookClubAIModel.id == model_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            for key, value in kwargs.items():
                if hasattr(model, key) and value is not None:
                    setattr(model, key, value)
            await self.db.flush()
            await self.db.refresh(model)
        return model

    # Chat Sessions
    async def create_session(self, **kwargs) -> BookClubAIChatSession:
        session = BookClubAIChatSession(**kwargs)
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID) -> BookClubAIChatSession | None:
        stmt = select(BookClubAIChatSession).where(BookClubAIChatSession.id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_with_details(self, session_id: uuid.UUID) -> BookClubAIChatSession | None:
        stmt = (
            select(BookClubAIChatSession)
            .options(
                selectinload(BookClubAIChatSession.messages),
                selectinload(BookClubAIChatSession.participants),
            )
            .where(BookClubAIChatSession.id == session_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(self, club_id: uuid.UUID, page: int = 1, limit: int = 20) -> tuple[list[BookClubAIChatSession], int]:
        count_stmt = select(func.count()).select_from(BookClubAIChatSession).where(BookClubAIChatSession.club_id == club_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = (
            select(BookClubAIChatSession)
            .where(BookClubAIChatSession.club_id == club_id)
            .order_by(BookClubAIChatSession.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def update_session(self, session_id: uuid.UUID, **kwargs) -> BookClubAIChatSession | None:
        session = await self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key) and value is not None:
                    setattr(session, key, value)
            await self.db.flush()
            await self.db.refresh(session)
        return session

    # Chat Messages
    async def create_message(self, **kwargs) -> BookClubAIChatMessage:
        message = BookClubAIChatMessage(**kwargs)
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def list_messages(self, session_id: uuid.UUID, page: int = 1, limit: int = 50) -> tuple[list[BookClubAIChatMessage], int]:
        count_stmt = select(func.count()).select_from(BookClubAIChatMessage).where(BookClubAIChatMessage.session_id == session_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        stmt = (
            select(BookClubAIChatMessage)
            .where(BookClubAIChatMessage.session_id == session_id)
            .order_by(BookClubAIChatMessage.created_at.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    # Chat Participants
    async def add_participant(self, session_id: uuid.UUID, user_id: uuid.UUID) -> BookClubAIChatParticipant:
        participant = BookClubAIChatParticipant(session_id=session_id, user_id=user_id)
        self.db.add(participant)
        await self.db.flush()
        await self.db.refresh(participant)
        return participant

    async def get_participant(self, session_id: uuid.UUID, user_id: uuid.UUID) -> BookClubAIChatParticipant | None:
        stmt = select(BookClubAIChatParticipant).where(
            BookClubAIChatParticipant.session_id == session_id,
            BookClubAIChatParticipant.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_participant(self, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
        participant = await self.get_participant(session_id, user_id)
        if participant:
            participant.is_active = False
            await self.db.flush()

    async def list_participants(self, session_id: uuid.UUID) -> list[BookClubAIChatParticipant]:
        stmt = (
            select(BookClubAIChatParticipant)
            .where(BookClubAIChatParticipant.session_id == session_id, BookClubAIChatParticipant.is_active.is_(True))
            .order_by(BookClubAIChatParticipant.joined_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
