"""Issue repository for database operations."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.issue import UserIssue, UserIssueResponse


class IssueRepository:
    """Repository for UserIssue database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Issue CRUD operations

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        description: str,
        issue_type: str = "bug",
        priority: str = "medium",
        error_code: str | None = None,
        book_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        attachments: dict | None = None,
        metadata: dict | None = None,
    ) -> UserIssue:
        """Create a new issue."""
        issue = UserIssue(
            user_id=user_id,
            title=title,
            description=description,
            issue_type=issue_type,
            priority=priority,
            error_code=error_code,
            book_id=book_id,
            session_id=session_id,
            attachments=attachments or {},
            metadata_=metadata or {},
        )
        self.db.add(issue)
        await self.db.flush()
        await self.db.refresh(issue)
        return issue

    async def get_by_id(
        self,
        issue_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> UserIssue | None:
        """Get issue by ID, optionally filtering by user."""
        stmt = (
            select(UserIssue)
            .options(joinedload(UserIssue.user))
            .where(UserIssue.id == issue_id)
        )

        if user_id is not None:
            stmt = stmt.where(UserIssue.user_id == user_id)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        issue_type: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[UserIssue], int]:
        """List issues for a specific user with filtering and pagination."""
        conditions = [UserIssue.user_id == user_id]

        if status:
            conditions.append(UserIssue.status == status)
        if issue_type:
            conditions.append(UserIssue.issue_type == issue_type)

        # Count query
        count_stmt = select(func.count(UserIssue.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(UserIssue)
            .options(joinedload(UserIssue.user))
            .where(and_(*conditions))
            .order_by(UserIssue.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        issues = list(result.scalars().unique().all())

        return issues, total

    async def list_all(
        self,
        status: str | None = None,
        issue_type: str | None = None,
        priority: str | None = None,
        search_query: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[UserIssue], int]:
        """List all issues with filtering and pagination (admin)."""
        conditions: list = []

        if status:
            conditions.append(UserIssue.status == status)
        if issue_type:
            conditions.append(UserIssue.issue_type == issue_type)
        if priority:
            conditions.append(UserIssue.priority == priority)
        if search_query:
            search_pattern = f"%{search_query}%"
            conditions.append(UserIssue.title.ilike(search_pattern))

        # Count query
        count_stmt = select(func.count(UserIssue.id))
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(UserIssue)
            .options(joinedload(UserIssue.user))
            .order_by(UserIssue.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.db.execute(stmt)
        issues = list(result.scalars().unique().all())

        return issues, total

    async def update(
        self,
        issue: UserIssue,
        **kwargs,
    ) -> UserIssue:
        """Update issue fields."""
        for key, value in kwargs.items():
            if hasattr(issue, key) and value is not None:
                setattr(issue, key, value)

        issue.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(issue)
        return issue

    async def update_status(
        self,
        issue: UserIssue,
        status: str,
    ) -> UserIssue:
        """Update issue status."""
        issue.status = status
        issue.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(issue)
        return issue

    async def get_response_count(self, issue_id: uuid.UUID) -> int:
        """Get the number of responses for an issue."""
        stmt = select(func.count(UserIssueResponse.id)).where(
            UserIssueResponse.issue_id == issue_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    # Issue response operations

    async def create_response(
        self,
        issue_id: uuid.UUID,
        responder_id: uuid.UUID,
        response_text: str,
        is_internal: bool = False,
        attached_article_id: uuid.UUID | None = None,
    ) -> UserIssueResponse:
        """Create a response to an issue."""
        response = UserIssueResponse(
            issue_id=issue_id,
            responder_id=responder_id,
            response_text=response_text,
            is_internal=is_internal,
            attached_article_id=attached_article_id,
        )
        self.db.add(response)
        await self.db.flush()
        await self.db.refresh(response)
        return response

    async def list_responses(
        self,
        issue_id: uuid.UUID,
        include_internal: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[UserIssueResponse], int]:
        """List responses for an issue with pagination."""
        conditions = [UserIssueResponse.issue_id == issue_id]

        if not include_internal:
            conditions.append(UserIssueResponse.is_internal.is_(False))

        # Count query
        count_stmt = select(func.count(UserIssueResponse.id)).where(
            and_(*conditions)
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        offset = (page - 1) * limit
        stmt = (
            select(UserIssueResponse)
            .options(joinedload(UserIssueResponse.responder))
            .where(and_(*conditions))
            .order_by(UserIssueResponse.created_at.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.db.execute(stmt)
        responses = list(result.scalars().unique().all())

        return responses, total
