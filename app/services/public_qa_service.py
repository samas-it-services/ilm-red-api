"""Public Q&A service for business logic."""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.public_qa_repo import PublicQARepository
from app.schemas.common import create_pagination
from app.schemas.public_qa import (
    EditHistoryEntry,
    EditHistoryResponse,
    FeedbackRequest,
    FeedbackResponse,
    PromoteToPublicQARequest,
    PublicQAListResponse,
    PublicQAResponse,
    PublicQAUpdate,
    UserBrief,
    VoteRequest,
    VoteResponse,
)

logger = structlog.get_logger(__name__)


class PublicQAService:
    """Service for public Q&A business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PublicQARepository(db)

    async def promote_to_public_qa(
        self,
        request: PromoteToPublicQARequest,
        user: User,
    ) -> PublicQAResponse:
        """Promote a chat message to a public Q&A entry."""
        qa = await self.repo.create(
            user_id=user.id,
            original_message_id=request.original_message_id,
            book_id=request.book_id,
            question=request.question,
            answer=request.answer,
            title=request.title,
            description=request.description,
            tags=request.tags,
            category=request.category,
            status=request.status.value if request.status else "draft",
            visibility=request.visibility.value if request.visibility else "public",
        )

        await self.db.commit()

        logger.info(
            "Chat promoted to public QA",
            qa_id=str(qa.id),
            user_id=str(user.id),
            book_id=str(request.book_id),
        )

        return self._qa_to_response(qa, user)

    async def list_qa(
        self,
        book_id: uuid.UUID | None = None,
        category: str | None = None,
        status: str | None = None,
        search_query: str | None = None,
        featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PublicQAListResponse:
        """List public Q&A entries with filtering and pagination."""
        qa_list, total = await self.repo.list_qa(
            book_id=book_id,
            category=category,
            status=status,
            search_query=search_query,
            featured=featured,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        items = [self._qa_to_response(qa) for qa in qa_list]

        return PublicQAListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def get_qa(
        self,
        qa_id: uuid.UUID,
        viewer_id: uuid.UUID | None = None,
        ip_address: str = "0.0.0.0",
        user_agent: str | None = None,
    ) -> PublicQAResponse:
        """Get a Q&A entry by ID and track the view."""
        qa = await self.repo.get_by_id(qa_id)
        if not qa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Q&A entry not found",
            )

        # Deduplicated view tracking
        has_recent = await self.repo.has_recent_view(
            qa_id=qa_id,
            viewer_id=viewer_id,
            ip_address=ip_address,
        )
        if not has_recent:
            await self.repo.record_view(
                qa_id=qa_id,
                viewer_id=viewer_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.db.commit()
            # Refresh to get updated view_count
            await self.db.refresh(qa)

        return self._qa_to_response(qa)

    async def update_qa(
        self,
        qa_id: uuid.UUID,
        updates: PublicQAUpdate,
        user: User,
    ) -> PublicQAResponse:
        """Update a Q&A entry and create edit history."""
        qa = await self.repo.get_by_id(qa_id)
        if not qa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Q&A entry not found",
            )

        # Only the author or an admin can edit
        if qa.user_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author or an admin can edit this Q&A",
            )

        # Create edit history before updating
        await self.repo.create_edit_history(
            qa_id=qa_id,
            edited_by=user.id,
            previous_question=qa.question,
            previous_answer=qa.answer,
            previous_title=qa.title,
            previous_description=qa.description,
            previous_tags=qa.tags,
            previous_category=qa.category,
            edit_reason=updates.edit_reason,
        )

        # Build update dict
        update_data = {}
        if updates.question is not None:
            update_data["question"] = updates.question
        if updates.answer is not None:
            update_data["answer"] = updates.answer
        if updates.title is not None:
            update_data["title"] = updates.title
        if updates.description is not None:
            update_data["description"] = updates.description
        if updates.tags is not None:
            update_data["tags"] = updates.tags
        if updates.category is not None:
            update_data["category"] = updates.category
        if updates.status is not None:
            update_data["status"] = updates.status.value
            if updates.status.value == "published" and qa.published_at is None:
                update_data["published_at"] = datetime.now(UTC)
                update_data["published_by"] = user.id
        if updates.visibility is not None:
            update_data["visibility"] = updates.visibility.value
        if updates.featured is not None:
            update_data["featured"] = updates.featured

        if update_data:
            update_data["last_edited_at"] = datetime.now(UTC)
            update_data["last_edited_by"] = user.id
            qa = await self.repo.update_qa(qa, **update_data)

        await self.db.commit()

        logger.info(
            "Public QA updated",
            qa_id=str(qa_id),
            edited_by=str(user.id),
        )

        return self._qa_to_response(qa)

    async def delete_qa(
        self,
        qa_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete a Q&A entry."""
        qa = await self.repo.get_by_id(qa_id)
        if not qa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Q&A entry not found",
            )

        # Only the author or an admin can delete
        if qa.user_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author or an admin can delete this Q&A",
            )

        await self.repo.delete_qa(qa)
        await self.db.commit()

        logger.info(
            "Public QA deleted",
            qa_id=str(qa_id),
            deleted_by=str(user.id),
        )

    async def vote(
        self,
        qa_id: uuid.UUID,
        vote_request: VoteRequest,
        user: User,
    ) -> VoteResponse:
        """Vote on a Q&A entry with toggle support.

        If the user already has the same vote type, the vote is removed (toggle off).
        If the user has a different vote type, it is changed.
        If the user has no vote, a new vote is created.
        """
        qa = await self.repo.get_by_id(qa_id)
        if not qa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Q&A entry not found",
            )

        existing_vote = await self.repo.get_user_vote(qa_id, user.id)

        if existing_vote:
            if existing_vote.vote_type == vote_request.vote_type.value:
                # Toggle off - remove the vote
                await self.repo.delete_vote(existing_vote)
                upvotes, downvotes, net_votes = await self.repo.recalculate_vote_counts(qa_id)
                await self.db.commit()

                return VoteResponse(
                    qa_id=qa_id,
                    vote_type=None,
                    upvotes=upvotes,
                    downvotes=downvotes,
                    net_votes=net_votes,
                    message="Vote removed",
                )
            else:
                # Change vote type
                await self.repo.update_vote(
                    existing_vote,
                    vote_type=vote_request.vote_type.value,
                    explanation=vote_request.explanation,
                )
                upvotes, downvotes, net_votes = await self.repo.recalculate_vote_counts(qa_id)
                await self.db.commit()

                return VoteResponse(
                    qa_id=qa_id,
                    vote_type=vote_request.vote_type.value,
                    upvotes=upvotes,
                    downvotes=downvotes,
                    net_votes=net_votes,
                    message="Vote updated",
                )
        else:
            # Create new vote
            await self.repo.create_vote(
                qa_id=qa_id,
                user_id=user.id,
                vote_type=vote_request.vote_type.value,
                explanation=vote_request.explanation,
            )
            upvotes, downvotes, net_votes = await self.repo.recalculate_vote_counts(qa_id)
            await self.db.commit()

            return VoteResponse(
                qa_id=qa_id,
                vote_type=vote_request.vote_type.value,
                upvotes=upvotes,
                downvotes=downvotes,
                net_votes=net_votes,
                message="Vote recorded",
            )

    async def submit_feedback(
        self,
        qa_id: uuid.UUID,
        feedback_request: FeedbackRequest,
        user: User,
    ) -> FeedbackResponse:
        """Submit feedback on a Q&A entry."""
        qa = await self.repo.get_by_id(qa_id)
        if not qa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Q&A entry not found",
            )

        # Check for existing feedback
        existing = await self.repo.get_user_feedback(qa_id, user.id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already submitted feedback for this Q&A",
            )

        feedback = await self.repo.create_feedback(
            qa_id=qa_id,
            user_id=user.id,
            feedback_type=feedback_request.feedback_type.value,
            feedback_text=feedback_request.feedback_text,
        )

        await self.db.commit()

        logger.info(
            "QA feedback submitted",
            qa_id=str(qa_id),
            user_id=str(user.id),
            feedback_type=feedback_request.feedback_type.value,
        )

        return FeedbackResponse(
            id=feedback.id,
            qa_id=qa_id,
            feedback_type=feedback.feedback_type,
            feedback_text=feedback.feedback_text,
            created_at=feedback.created_at,
        )

    async def get_edit_history(
        self,
        qa_id: uuid.UUID,
    ) -> EditHistoryResponse:
        """Get edit history for a Q&A entry."""
        qa = await self.repo.get_by_id(qa_id)
        if not qa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Q&A entry not found",
            )

        history = await self.repo.get_edit_history(qa_id)

        entries = []
        for h in history:
            editor_brief = None
            if h.editor:
                editor_brief = UserBrief(
                    id=h.editor.id,
                    username=h.editor.username,
                    display_name=h.editor.display_name,
                    avatar_url=h.editor.avatar_url,
                )

            entries.append(
                EditHistoryEntry(
                    id=h.id,
                    qa_id=h.qa_id,
                    edited_by=h.edited_by,
                    edited_at=h.edited_at,
                    previous_question=h.previous_question,
                    previous_answer=h.previous_answer,
                    previous_title=h.previous_title,
                    previous_description=h.previous_description,
                    previous_tags=h.previous_tags,
                    previous_category=h.previous_category,
                    edit_reason=h.edit_reason,
                    version_number=h.version_number,
                    editor=editor_brief,
                )
            )

        return EditHistoryResponse(
            data=entries,
            qa_id=qa_id,
        )

    # Helper methods

    def _qa_to_response(self, qa, user: User | None = None) -> PublicQAResponse:
        """Convert PublicQA model to response schema."""
        user_brief = None
        if qa.user:
            user_brief = UserBrief(
                id=qa.user.id,
                username=qa.user.username,
                display_name=qa.user.display_name,
                avatar_url=qa.user.avatar_url,
            )
        elif user:
            user_brief = UserBrief(
                id=user.id,
                username=user.username,
                display_name=user.display_name,
                avatar_url=user.avatar_url,
            )

        return PublicQAResponse(
            id=qa.id,
            original_message_id=qa.original_message_id,
            book_id=qa.book_id,
            user_id=qa.user_id,
            question=qa.question,
            answer=qa.answer,
            title=qa.title,
            description=qa.description,
            tags=qa.tags or [],
            category=qa.category,
            status=qa.status,
            visibility=qa.visibility,
            featured=qa.featured,
            upvotes=qa.upvotes,
            downvotes=qa.downvotes,
            net_votes=qa.net_votes,
            view_count=qa.view_count,
            helpful_count=qa.helpful_count,
            not_helpful_count=qa.not_helpful_count,
            published_at=qa.published_at,
            last_edited_at=qa.last_edited_at,
            user=user_brief,
            created_at=qa.created_at,
            updated_at=qa.updated_at,
        )
