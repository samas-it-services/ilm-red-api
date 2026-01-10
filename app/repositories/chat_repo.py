"""Chat repository for database operations."""

import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.chat import ChatMessage, ChatSession, MessageFeedback


class ChatRepository:
    """Repository for Chat database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Session operations

    async def create_session(
        self,
        user_id: uuid.UUID,
        title: str | None = None,
        book_id: uuid.UUID | None = None,
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            user_id=user_id,
            title=title,
            book_id=book_id,
            message_count=0,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_session(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        include_book: bool = False,
    ) -> ChatSession | None:
        """Get session by ID, optionally filtering by user."""
        stmt = select(ChatSession).where(ChatSession.id == session_id)

        if include_book:
            stmt = stmt.options(joinedload(ChatSession.book))

        if user_id is not None:
            stmt = stmt.where(ChatSession.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(
        self,
        user_id: uuid.UUID,
        book_id: uuid.UUID | None = None,
        include_archived: bool = False,
        page: int = 1,
        limit: int = 20,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[ChatSession], int]:
        """List chat sessions for a user with filtering and pagination.

        Args:
            user_id: User ID to filter by
            book_id: Optional book ID to filter by
            include_archived: Whether to include archived sessions
            page: Page number (1-indexed)
            limit: Items per page
            sort_order: Sort by updated_at

        Returns:
            Tuple of (sessions list, total count)
        """
        conditions = [ChatSession.user_id == user_id]

        if book_id is not None:
            conditions.append(ChatSession.book_id == book_id)

        if not include_archived:
            conditions.append(ChatSession.archived_at.is_(None))

        # Count query
        count_stmt = select(func.count(ChatSession.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(ChatSession)
            .options(joinedload(ChatSession.book))
            .where(and_(*conditions))
        )

        # Sorting
        if sort_order == "desc":
            stmt = stmt.order_by(ChatSession.updated_at.desc())
        else:
            stmt = stmt.order_by(ChatSession.updated_at.asc())

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        sessions = list(result.scalars().unique().all())

        return sessions, total

    async def update_session(
        self,
        session: ChatSession,
        title: str | None = None,
    ) -> ChatSession:
        """Update session metadata."""
        if title is not None:
            session.title = title

        session.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def update_session_after_message(
        self,
        session_id: uuid.UUID,
        model: str | None = None,
    ) -> None:
        """Update session stats after adding a message."""
        stmt = (
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(
                message_count=ChatSession.message_count + 1,
                last_model=model,
                updated_at=datetime.now(UTC),
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def archive_session(self, session: ChatSession) -> ChatSession:
        """Archive a chat session."""
        session.archive()
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def unarchive_session(self, session: ChatSession) -> ChatSession:
        """Unarchive a chat session."""
        session.unarchive()
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session: ChatSession) -> None:
        """Permanently delete a chat session and all messages."""
        await self.db.delete(session)
        await self.db.flush()

    # Message operations

    async def create_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        model: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        cost_cents: int | None = None,
        finish_reason: str | None = None,
        safety_flags: list | None = None,
    ) -> ChatMessage:
        """Create a new chat message."""
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_cents=cost_cents,
            finish_reason=finish_reason,
            safety_flags=safety_flags or [],
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_message(
        self,
        message_id: uuid.UUID,
        session_id: uuid.UUID | None = None,
    ) -> ChatMessage | None:
        """Get message by ID, optionally filtering by session."""
        stmt = select(ChatMessage).where(ChatMessage.id == message_id)

        if session_id is not None:
            stmt = stmt.where(ChatMessage.session_id == session_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_messages(
        self,
        session_id: uuid.UUID,
        page: int = 1,
        limit: int = 50,
        before_id: uuid.UUID | None = None,
        after_id: uuid.UUID | None = None,
    ) -> tuple[list[ChatMessage], int]:
        """Get messages for a session with pagination.

        Args:
            session_id: Session ID
            page: Page number (1-indexed)
            limit: Items per page
            before_id: Get messages before this message ID
            after_id: Get messages after this message ID

        Returns:
            Tuple of (messages list, total count)
        """
        conditions = [ChatMessage.session_id == session_id]

        # Cursor-based pagination
        if before_id:
            before_msg = await self.get_message(before_id, session_id)
            if before_msg:
                conditions.append(ChatMessage.created_at < before_msg.created_at)

        if after_id:
            after_msg = await self.get_message(after_id, session_id)
            if after_msg:
                conditions.append(ChatMessage.created_at > after_msg.created_at)

        # Count query (total in session, not filtered)
        count_stmt = select(func.count(ChatMessage.id)).where(
            ChatMessage.session_id == session_id
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(ChatMessage)
            .where(and_(*conditions))
            .order_by(ChatMessage.created_at.asc())
        )

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())

        return messages, total

    async def get_session_history(
        self,
        session_id: uuid.UUID,
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """Get all messages in a session for AI context.

        Args:
            session_id: Session ID
            limit: Optional limit for recent messages only

        Returns:
            List of messages in chronological order
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )

        if limit:
            # Get the most recent N messages
            stmt = (
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            messages = list(result.scalars().all())
            # Reverse to get chronological order
            return messages[::-1]

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_message(
        self,
        message: ChatMessage,
        content: str | None = None,
        tokens_input: int | None = None,
        tokens_output: int | None = None,
        cost_cents: int | None = None,
        model: str | None = None,
        finish_reason: str | None = None,
        safety_flags: list | None = None,
    ) -> ChatMessage:
        """Update message metadata (used for streaming completion)."""
        if content is not None:
            message.content = content
        if tokens_input is not None:
            message.tokens_input = tokens_input
        if tokens_output is not None:
            message.tokens_output = tokens_output
        if cost_cents is not None:
            message.cost_cents = cost_cents
        if model is not None:
            message.model = model
        if finish_reason is not None:
            message.finish_reason = finish_reason
        if safety_flags is not None:
            message.safety_flags = safety_flags

        await self.db.flush()
        await self.db.refresh(message)
        return message

    # Feedback operations

    async def create_feedback(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: int,
        comment: str | None = None,
    ) -> MessageFeedback:
        """Create or update feedback for a message."""
        # Check if feedback already exists
        existing = await self.get_feedback(message_id, user_id)

        if existing:
            # Update existing feedback
            existing.rating = rating
            existing.comment = comment
            await self.db.flush()
            await self.db.refresh(existing)
            return existing

        # Create new feedback
        feedback = MessageFeedback(
            message_id=message_id,
            user_id=user_id,
            rating=rating,
            comment=comment,
        )
        self.db.add(feedback)
        await self.db.flush()
        await self.db.refresh(feedback)
        return feedback

    async def get_feedback(
        self,
        message_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> MessageFeedback | None:
        """Get feedback for a message by a user."""
        stmt = select(MessageFeedback).where(
            and_(
                MessageFeedback.message_id == message_id,
                MessageFeedback.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_feedback(self, feedback: MessageFeedback) -> None:
        """Delete feedback."""
        await self.db.delete(feedback)
        await self.db.flush()

    async def has_feedback(self, message_id: uuid.UUID) -> bool:
        """Check if a message has any feedback."""
        stmt = select(func.count(MessageFeedback.id)).where(
            MessageFeedback.message_id == message_id
        )
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

    # Session statistics

    async def get_session_token_usage(
        self,
        session_id: uuid.UUID,
    ) -> dict:
        """Get total token usage for a session."""
        stmt = select(
            func.coalesce(func.sum(ChatMessage.tokens_input), 0),
            func.coalesce(func.sum(ChatMessage.tokens_output), 0),
            func.coalesce(func.sum(ChatMessage.cost_cents), 0),
        ).where(ChatMessage.session_id == session_id)

        result = await self.db.execute(stmt)
        row = result.one()

        return {
            "tokens_input": row[0],
            "tokens_output": row[1],
            "cost_cents": row[2],
        }

    async def get_last_message_preview(
        self,
        session_id: uuid.UUID,
        max_length: int = 100,
    ) -> str | None:
        """Get preview of the last message in a session."""
        stmt = (
            select(ChatMessage.content)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        content = result.scalar_one_or_none()

        if content and len(content) > max_length:
            return content[:max_length] + "..."
        return content
