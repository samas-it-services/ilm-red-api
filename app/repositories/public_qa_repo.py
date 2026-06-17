"""Public Q&A repository for database operations."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.public_qa import (
    PublicQA,
    PublicQAEditHistory,
    PublicQAFeedback,
    PublicQAView,
    PublicQAVote,
)


class PublicQARepository:
    """Repository for Public Q&A database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # CRUD operations

    async def create(
        self,
        user_id: uuid.UUID,
        original_message_id: uuid.UUID,
        book_id: uuid.UUID,
        question: str,
        answer: str,
        title: str,
        description: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        status: str = "draft",
        visibility: str = "public",
    ) -> PublicQA:
        """Create a new public Q&A entry."""
        qa = PublicQA(
            user_id=user_id,
            original_message_id=original_message_id,
            book_id=book_id,
            question=question,
            answer=answer,
            title=title,
            description=description,
            tags=tags or [],
            category=category,
            status=status,
            visibility=visibility,
        )
        self.db.add(qa)
        await self.db.flush()
        await self.db.refresh(qa)
        return qa

    async def get_by_id(self, qa_id: uuid.UUID) -> PublicQA | None:
        """Get a public Q&A by ID."""
        stmt = (
            select(PublicQA)
            .options(joinedload(PublicQA.user))
            .where(PublicQA.id == qa_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_qa(
        self,
        book_id: uuid.UUID | None = None,
        category: str | None = None,
        status: str | None = None,
        visibility: str | None = None,
        search_query: str | None = None,
        featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[PublicQA], int]:
        """List public Q&A with filtering and pagination."""
        conditions = []

        if book_id is not None:
            conditions.append(PublicQA.book_id == book_id)
        if category is not None:
            conditions.append(PublicQA.category == category)
        if status is not None:
            conditions.append(PublicQA.status == status)
        if visibility is not None:
            conditions.append(PublicQA.visibility == visibility)
        if featured is not None:
            conditions.append(PublicQA.featured == featured)
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(
                or_(
                    PublicQA.title.ilike(search_pattern),
                    PublicQA.question.ilike(search_pattern),
                )
            )

        # Count
        count_stmt = select(func.count(PublicQA.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        stmt = select(PublicQA).options(joinedload(PublicQA.user))
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Sorting
        sort_column = getattr(PublicQA, sort_by, PublicQA.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Pagination
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        qa_list = list(result.scalars().unique().all())

        return qa_list, total

    async def update_qa(self, qa: PublicQA, **kwargs) -> PublicQA:
        """Update a public Q&A entry."""
        for key, value in kwargs.items():
            if hasattr(qa, key) and value is not None:
                setattr(qa, key, value)

        qa.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(qa)
        return qa

    async def delete_qa(self, qa: PublicQA) -> None:
        """Delete a public Q&A entry."""
        await self.db.delete(qa)
        await self.db.flush()

    # Voting operations

    async def get_user_vote(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PublicQAVote | None:
        """Get user's existing vote on a Q&A."""
        stmt = select(PublicQAVote).where(
            and_(
                PublicQAVote.public_qa_id == qa_id,
                PublicQAVote.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_vote(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
        vote_type: str,
        explanation: str | None = None,
    ) -> PublicQAVote:
        """Create a new vote."""
        vote = PublicQAVote(
            public_qa_id=qa_id,
            user_id=user_id,
            vote_type=vote_type,
            explanation=explanation,
        )
        self.db.add(vote)
        await self.db.flush()
        await self.db.refresh(vote)
        return vote

    async def update_vote(
        self,
        vote: PublicQAVote,
        vote_type: str,
        explanation: str | None = None,
    ) -> PublicQAVote:
        """Update an existing vote."""
        vote.vote_type = vote_type
        vote.explanation = explanation
        vote.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(vote)
        return vote

    async def delete_vote(self, vote: PublicQAVote) -> None:
        """Delete a vote."""
        await self.db.delete(vote)
        await self.db.flush()

    async def recalculate_vote_counts(self, qa_id: uuid.UUID) -> tuple[int, int, int]:
        """Recalculate upvotes, downvotes, and net_votes for a Q&A."""
        upvotes_stmt = select(func.count(PublicQAVote.id)).where(
            and_(
                PublicQAVote.public_qa_id == qa_id,
                PublicQAVote.vote_type == "upvote",
            )
        )
        downvotes_stmt = select(func.count(PublicQAVote.id)).where(
            and_(
                PublicQAVote.public_qa_id == qa_id,
                PublicQAVote.vote_type == "downvote",
            )
        )

        upvotes_result = await self.db.execute(upvotes_stmt)
        downvotes_result = await self.db.execute(downvotes_stmt)

        upvotes = upvotes_result.scalar_one()
        downvotes = downvotes_result.scalar_one()
        net_votes = upvotes - downvotes

        # Update the Q&A
        stmt = (
            update(PublicQA)
            .where(PublicQA.id == qa_id)
            .values(
                upvotes=upvotes,
                downvotes=downvotes,
                net_votes=net_votes,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

        return upvotes, downvotes, net_votes

    # View tracking

    async def has_recent_view(
        self,
        qa_id: uuid.UUID,
        viewer_id: uuid.UUID | None,
        ip_address: str,
        window_minutes: int = 30,
    ) -> bool:
        """Check if a view was already recorded within the deduplication window."""
        cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)

        conditions = [
            PublicQAView.qa_id == qa_id,
            PublicQAView.viewed_at >= cutoff,
        ]

        if viewer_id is not None:
            conditions.append(PublicQAView.viewer_id == viewer_id)
        else:
            conditions.append(PublicQAView.ip_address == ip_address)

        stmt = select(func.count(PublicQAView.id)).where(and_(*conditions))
        result = await self.db.execute(stmt)
        count = result.scalar_one()
        return count > 0

    async def record_view(
        self,
        qa_id: uuid.UUID,
        viewer_id: uuid.UUID | None,
        ip_address: str,
        user_agent: str | None = None,
    ) -> PublicQAView:
        """Record a view on a Q&A entry."""
        view = PublicQAView(
            qa_id=qa_id,
            viewer_id=viewer_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(view)

        # Increment view count on the QA
        stmt = (
            update(PublicQA)
            .where(PublicQA.id == qa_id)
            .values(view_count=PublicQA.view_count + 1)
        )
        await self.db.execute(stmt)
        await self.db.flush()

        return view

    # Edit history

    async def create_edit_history(
        self,
        qa_id: uuid.UUID,
        edited_by: uuid.UUID,
        previous_question: str | None = None,
        previous_answer: str | None = None,
        previous_title: str | None = None,
        previous_description: str | None = None,
        previous_tags: list[str] | None = None,
        previous_category: str | None = None,
        edit_reason: str | None = None,
    ) -> PublicQAEditHistory:
        """Create an edit history entry."""
        # Determine version number
        version_stmt = select(func.coalesce(
            func.max(PublicQAEditHistory.version_number), 0
        )).where(PublicQAEditHistory.qa_id == qa_id)
        version_result = await self.db.execute(version_stmt)
        next_version = version_result.scalar_one() + 1

        history = PublicQAEditHistory(
            qa_id=qa_id,
            edited_by=edited_by,
            previous_question=previous_question,
            previous_answer=previous_answer,
            previous_title=previous_title,
            previous_description=previous_description,
            previous_tags=previous_tags,
            previous_category=previous_category,
            edit_reason=edit_reason,
            version_number=next_version,
        )
        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def get_edit_history(
        self,
        qa_id: uuid.UUID,
    ) -> list[PublicQAEditHistory]:
        """Get edit history for a Q&A entry."""
        stmt = (
            select(PublicQAEditHistory)
            .options(joinedload(PublicQAEditHistory.editor))
            .where(PublicQAEditHistory.qa_id == qa_id)
            .order_by(PublicQAEditHistory.version_number.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    # Feedback operations

    async def create_feedback(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
        feedback_type: str,
        feedback_text: str | None = None,
    ) -> PublicQAFeedback:
        """Create feedback for a Q&A entry."""
        feedback = PublicQAFeedback(
            qa_id=qa_id,
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
        )
        self.db.add(feedback)

        # Update feedback counts on the QA
        if feedback_type == "helpful":
            stmt = (
                update(PublicQA)
                .where(PublicQA.id == qa_id)
                .values(helpful_count=PublicQA.helpful_count + 1)
            )
        else:
            stmt = (
                update(PublicQA)
                .where(PublicQA.id == qa_id)
                .values(not_helpful_count=PublicQA.not_helpful_count + 1)
            )
        await self.db.execute(stmt)
        await self.db.flush()
        await self.db.refresh(feedback)

        return feedback

    async def get_user_feedback(
        self,
        qa_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> PublicQAFeedback | None:
        """Get user's existing feedback on a Q&A."""
        stmt = select(PublicQAFeedback).where(
            and_(
                PublicQAFeedback.qa_id == qa_id,
                PublicQAFeedback.user_id == user_id,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
