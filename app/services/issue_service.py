"""Issue service for business logic."""

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.issue import UserIssue
from app.models.user import User
from app.repositories.issue_repo import IssueRepository
from app.schemas.common import create_pagination
from app.schemas.issue import (
    IssueCreate,
    IssueListResponse,
    IssueResponse,
    IssueResponseCreate,
    IssueResponseListResponse,
    IssueResponseResponse,
    IssueStatusUpdate,
    IssueUpdate,
    IssueUserBrief,
)

logger = structlog.get_logger(__name__)


class IssueService:
    """Service for issue-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = IssueRepository(db)

    async def create_issue(
        self,
        user: User,
        data: IssueCreate,
    ) -> IssueResponse:
        """Create a new issue.

        Args:
            user: Current authenticated user
            data: Issue creation data

        Returns:
            Created issue response
        """
        issue = await self.repo.create(
            user_id=user.id,
            title=data.title,
            description=data.description,
            issue_type=data.issue_type.value,
            priority=data.priority.value,
            error_code=data.error_code,
            book_id=data.book_id,
            session_id=data.session_id,
            attachments=data.attachments,
            metadata=data.metadata,
        )

        await self.db.commit()

        logger.info(
            "issue_created",
            issue_id=str(issue.id),
            user_id=str(user.id),
            issue_type=data.issue_type.value,
            priority=data.priority.value,
        )

        return self._issue_to_response(issue, response_count=0)

    async def get_issue(
        self,
        issue_id: uuid.UUID,
        user: User,
    ) -> IssueResponse:
        """Get an issue by ID.

        Args:
            issue_id: Issue UUID
            user: Current user

        Returns:
            Issue response

        Raises:
            HTTPException: If issue not found or access denied
        """
        # Admins can view any issue; regular users only their own
        if user.is_admin:
            issue = await self.repo.get_by_id(issue_id)
        else:
            issue = await self.repo.get_by_id(issue_id, user_id=user.id)

        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )

        response_count = await self.repo.get_response_count(issue_id)
        return self._issue_to_response(issue, response_count=response_count)

    async def list_user_issues(
        self,
        user: User,
        status_filter: str | None = None,
        issue_type: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> IssueListResponse:
        """List issues for the current user.

        Args:
            user: Current user
            status_filter: Optional status filter
            issue_type: Optional issue type filter
            page: Page number
            limit: Items per page

        Returns:
            Paginated issue list
        """
        issues, total = await self.repo.list_by_user(
            user_id=user.id,
            status=status_filter,
            issue_type=issue_type,
            page=page,
            limit=limit,
        )

        items = []
        for issue in issues:
            count = await self.repo.get_response_count(issue.id)
            items.append(self._issue_to_response(issue, response_count=count))

        return IssueListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def list_all_issues(
        self,
        status_filter: str | None = None,
        issue_type: str | None = None,
        priority: str | None = None,
        search_query: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> IssueListResponse:
        """List all issues (admin only).

        Args:
            status_filter: Optional status filter
            issue_type: Optional issue type filter
            priority: Optional priority filter
            search_query: Optional search in title
            page: Page number
            limit: Items per page

        Returns:
            Paginated issue list
        """
        issues, total = await self.repo.list_all(
            status=status_filter,
            issue_type=issue_type,
            priority=priority,
            search_query=search_query,
            page=page,
            limit=limit,
        )

        items = []
        for issue in issues:
            count = await self.repo.get_response_count(issue.id)
            items.append(self._issue_to_response(issue, response_count=count))

        return IssueListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_issue(
        self,
        issue_id: uuid.UUID,
        user: User,
        data: IssueUpdate,
    ) -> IssueResponse:
        """Update an issue.

        Regular users can update their own issues (title, description, type, priority).
        Admins can update any issue including status.

        Args:
            issue_id: Issue UUID
            user: Current user
            data: Update data

        Returns:
            Updated issue response

        Raises:
            HTTPException: If issue not found or access denied
        """
        if user.is_admin:
            issue = await self.repo.get_by_id(issue_id)
        else:
            issue = await self.repo.get_by_id(issue_id, user_id=user.id)

        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )

        # Build update dict
        update_data = {}
        if data.title is not None:
            update_data["title"] = data.title
        if data.description is not None:
            update_data["description"] = data.description
        if data.issue_type is not None:
            update_data["issue_type"] = data.issue_type.value
        if data.priority is not None:
            update_data["priority"] = data.priority.value
        if data.error_code is not None:
            update_data["error_code"] = data.error_code

        # Only admins can change status via update
        if data.status is not None and user.is_admin:
            update_data["status"] = data.status.value

        if update_data:
            issue = await self.repo.update(issue, **update_data)
            await self.db.commit()

        response_count = await self.repo.get_response_count(issue_id)
        return self._issue_to_response(issue, response_count=response_count)

    async def update_issue_status(
        self,
        issue_id: uuid.UUID,
        data: IssueStatusUpdate,
    ) -> IssueResponse:
        """Update issue status (admin only).

        Args:
            issue_id: Issue UUID
            data: Status update data

        Returns:
            Updated issue response

        Raises:
            HTTPException: If issue not found
        """
        issue = await self.repo.get_by_id(issue_id)

        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )

        issue = await self.repo.update_status(issue, data.status.value)
        await self.db.commit()

        logger.info(
            "issue_status_updated",
            issue_id=str(issue_id),
            new_status=data.status.value,
        )

        response_count = await self.repo.get_response_count(issue_id)
        return self._issue_to_response(issue, response_count=response_count)

    async def add_response(
        self,
        issue_id: uuid.UUID,
        user: User,
        data: IssueResponseCreate,
    ) -> IssueResponseResponse:
        """Add a response to an issue.

        Args:
            issue_id: Issue UUID
            user: Current user (responder)
            data: Response creation data

        Returns:
            Created response

        Raises:
            HTTPException: If issue not found or access denied
        """
        # Verify the issue exists and the user has access
        if user.is_admin:
            issue = await self.repo.get_by_id(issue_id)
        else:
            issue = await self.repo.get_by_id(issue_id, user_id=user.id)
            # Non-admins cannot create internal responses
            if data.is_internal:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can create internal notes",
                )

        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )

        response = await self.repo.create_response(
            issue_id=issue_id,
            responder_id=user.id,
            response_text=data.response_text,
            is_internal=data.is_internal,
            attached_article_id=data.attached_article_id,
        )
        await self.db.commit()

        # Reload with responder relationship
        await self.db.refresh(response, ["responder"])

        logger.info(
            "issue_response_added",
            issue_id=str(issue_id),
            responder_id=str(user.id),
            is_internal=data.is_internal,
        )

        return self._response_to_schema(response)

    async def list_responses(
        self,
        issue_id: uuid.UUID,
        user: User,
        page: int = 1,
        limit: int = 50,
    ) -> IssueResponseListResponse:
        """List responses for an issue.

        Args:
            issue_id: Issue UUID
            user: Current user
            page: Page number
            limit: Items per page

        Returns:
            Paginated response list

        Raises:
            HTTPException: If issue not found or access denied
        """
        # Verify the issue exists and the user has access
        if user.is_admin:
            issue = await self.repo.get_by_id(issue_id)
        else:
            issue = await self.repo.get_by_id(issue_id, user_id=user.id)

        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Issue not found",
            )

        # Admins see internal notes; regular users do not
        responses, total = await self.repo.list_responses(
            issue_id=issue_id,
            include_internal=user.is_admin,
            page=page,
            limit=limit,
        )

        items = [self._response_to_schema(r) for r in responses]

        return IssueResponseListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    # Helper methods

    def _issue_to_response(
        self,
        issue: UserIssue,
        response_count: int = 0,
    ) -> IssueResponse:
        """Convert UserIssue model to response schema."""
        return IssueResponse(
            id=issue.id,
            user_id=issue.user_id,
            user=IssueUserBrief(
                id=issue.user.id,
                username=issue.user.username,
                display_name=issue.user.display_name,
            ),
            error_code=issue.error_code,
            issue_type=issue.issue_type,
            title=issue.title,
            description=issue.description,
            priority=issue.priority,
            status=issue.status,
            book_id=issue.book_id,
            session_id=issue.session_id,
            attachments=issue.attachments,
            metadata=issue.metadata_,
            response_count=response_count,
            created_at=issue.created_at,
            updated_at=issue.updated_at,
        )

    def _response_to_schema(
        self,
        response: "UserIssueResponse",
    ) -> IssueResponseResponse:
        """Convert UserIssueResponse model to response schema."""
        from app.models.issue import UserIssueResponse as _  # noqa: F401

        return IssueResponseResponse(
            id=response.id,
            issue_id=response.issue_id,
            responder=IssueUserBrief(
                id=response.responder.id,
                username=response.responder.username,
                display_name=response.responder.display_name,
            ),
            response_text=response.response_text,
            is_internal=response.is_internal,
            attached_article_id=response.attached_article_id,
            created_at=response.created_at,
        )
