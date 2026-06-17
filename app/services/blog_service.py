"""Blog service for business logic."""

import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blog import BlogPost
from app.models.user import User
from app.repositories.blog_repo import BlogRepository
from app.schemas.blog import (
    AuthorBrief,
    BlogCategoryBrief,
    BlogCategoryResponse,
    BlogCommentCreate,
    BlogCommentListResponse,
    BlogCommentResponse,
    BlogPostCreate,
    BlogPostListItem,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostUpdate,
    BlogTagBrief,
    BlogTagResponse,
)
from app.schemas.common import create_pagination

logger = structlog.get_logger(__name__)


class BlogService:
    """Service for blog-related business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BlogRepository(db)

    # ---------- Blog Post Operations ----------

    async def create_post(
        self,
        data: BlogPostCreate,
        author: User,
    ) -> BlogPostResponse:
        """Create a new blog post."""
        post = await self.repo.create_post(
            author_id=author.id,
            title=data.title,
            content=data.content,
            excerpt=data.excerpt,
            featured_image_url=data.featured_image_url,
            status=data.status.value,
            visibility=data.visibility.value,
            is_featured=data.is_featured,
            is_pinned=data.is_pinned,
            category_ids=data.category_ids,
            tag_ids=data.tag_ids,
        )
        await self.db.commit()

        # Reload with relationships
        post = await self.repo.get_post_by_id(post.id)
        logger.info("Blog post created", post_id=str(post.id), author_id=str(author.id))
        return self._post_to_response(post)

    async def get_post(
        self,
        slug: str,
        user: User | None = None,
        track_view: bool = True,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> BlogPostResponse:
        """Get a blog post by slug."""
        post = await self.repo.get_post_by_slug(slug)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found",
            )

        # Non-published posts only visible to author or admin
        if post.status != "published":
            if not user or (post.author_id != user.id and not user.is_admin):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Blog post not found",
                )

        # Track view
        if track_view:
            await self.repo.track_view(
                post_id=post.id,
                user_id=user.id if user else None,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.db.commit()

        # Check if current user liked the post
        is_liked = False
        if user:
            like = await self.repo.get_like(post.id, user.id)
            is_liked = like is not None

        return self._post_to_response(post, is_liked=is_liked)

    async def list_posts(
        self,
        user: User | None = None,
        status_filter: str | None = "published",
        category_slug: str | None = None,
        tag_slug: str | None = None,
        search_query: str | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "published_at",
        sort_order: str = "desc",
    ) -> BlogPostListResponse:
        """List blog posts with filtering and pagination."""
        # Non-admins can only see published posts
        if not user or not user.is_admin:
            status_filter = "published"

        posts, total = await self.repo.list_posts(
            status=status_filter,
            category_slug=category_slug,
            tag_slug=tag_slug,
            search_query=search_query,
            is_featured=is_featured,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        items = [self._post_to_list_item(p) for p in posts]

        return BlogPostListResponse(
            data=items,
            pagination=create_pagination(page, limit, total),
        )

    async def update_post(
        self,
        post_id: uuid.UUID,
        data: BlogPostUpdate,
        user: User,
    ) -> BlogPostResponse:
        """Update a blog post."""
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found",
            )

        # Only author or admin can update
        if post.author_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can update this post",
            )

        # Build update dict
        update_data = {}
        for field in ["title", "content", "excerpt", "featured_image_url", "is_featured", "is_pinned"]:
            value = getattr(data, field, None)
            if value is not None:
                update_data[field] = value

        if data.status is not None:
            update_data["status"] = data.status.value
        if data.visibility is not None:
            update_data["visibility"] = data.visibility.value

        if update_data:
            post = await self.repo.update_post(post, **update_data)

        # Update categories if provided
        if data.category_ids is not None:
            await self.repo.update_post_categories(post.id, data.category_ids)

        # Update tags if provided
        if data.tag_ids is not None:
            await self.repo.update_post_tags(post.id, data.tag_ids)

        await self.db.commit()

        # Reload with relationships
        post = await self.repo.get_post_by_id(post.id)
        logger.info("Blog post updated", post_id=str(post_id))
        return self._post_to_response(post)

    async def delete_post(
        self,
        post_id: uuid.UUID,
        user: User,
    ) -> None:
        """Delete a blog post."""
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found",
            )

        if post.author_id != user.id and not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the author can delete this post",
            )

        await self.repo.delete_post(post)
        await self.db.commit()
        logger.info("Blog post deleted", post_id=str(post_id), by_user=str(user.id))

    # ---------- Like Operations ----------

    async def like_post(
        self,
        post_id: uuid.UUID,
        user: User,
    ) -> dict:
        """Like a blog post."""
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found",
            )

        await self.repo.add_like(post_id, user.id)
        await self.db.commit()
        return {"message": "Post liked"}

    async def unlike_post(
        self,
        post_id: uuid.UUID,
        user: User,
    ) -> None:
        """Unlike a blog post."""
        removed = await self.repo.remove_like(post_id, user.id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Like not found",
            )
        await self.db.commit()

    # ---------- Comment Operations ----------

    async def create_comment(
        self,
        post_id: uuid.UUID,
        data: BlogCommentCreate,
        user: User,
    ) -> BlogCommentResponse:
        """Create a comment on a blog post."""
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found",
            )

        if post.status != "published":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot comment on unpublished posts",
            )

        comment = await self.repo.create_comment(
            post_id=post_id,
            author_id=user.id,
            content=data.content,
            parent_id=data.parent_id,
        )
        await self.db.commit()

        # Reload with author
        from sqlalchemy import select
        from sqlalchemy.orm import joinedload

        from app.models.blog import BlogComment

        stmt = (
            select(BlogComment)
            .options(joinedload(BlogComment.author))
            .where(BlogComment.id == comment.id)
        )
        result = await self.db.execute(stmt)
        comment = result.unique().scalar_one()

        return self._comment_to_response(comment)

    async def get_comments(
        self,
        post_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> BlogCommentListResponse:
        """Get comments for a blog post."""
        post = await self.repo.get_post_by_id(post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog post not found",
            )

        comments, total = await self.repo.get_comments(post_id, page, limit)

        return BlogCommentListResponse(
            data=[self._comment_to_response(c) for c in comments],
            pagination=create_pagination(page, limit, total),
        )

    # ---------- Category / Tag Operations ----------

    async def get_categories(self) -> list[BlogCategoryResponse]:
        """Get all active blog categories."""
        categories = await self.repo.get_categories(active_only=True)
        return [BlogCategoryResponse.model_validate(c) for c in categories]

    async def get_tags(self) -> list[BlogTagResponse]:
        """Get all blog tags."""
        tags = await self.repo.get_tags()
        return [BlogTagResponse.model_validate(t) for t in tags]

    # ---------- Converters ----------

    def _post_to_response(
        self,
        post: BlogPost,
        is_liked: bool = False,
    ) -> BlogPostResponse:
        """Convert BlogPost model to response schema."""
        categories = [
            BlogCategoryBrief(
                id=pc.category.id,
                name=pc.category.name,
                slug=pc.category.slug,
                icon=pc.category.icon,
                color=pc.category.color,
            )
            for pc in post.categories
        ]

        tags = [
            BlogTagBrief(
                id=pt.tag.id,
                name=pt.tag.name,
                slug=pt.tag.slug,
                color=pt.tag.color,
            )
            for pt in post.tags
        ]

        return BlogPostResponse(
            id=post.id,
            title=post.title,
            slug=post.slug,
            content=post.content,
            excerpt=post.excerpt,
            featured_image_url=post.featured_image_url,
            status=post.status,
            visibility=post.visibility,
            is_featured=post.is_featured,
            is_pinned=post.is_pinned,
            published_at=post.published_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            word_count=post.word_count,
            reading_time=post.reading_time,
            author=AuthorBrief(
                id=post.author.id,
                username=post.author.username,
                display_name=post.author.display_name,
                avatar_url=post.author.avatar_url,
            ),
            categories=categories,
            tags=tags,
            is_liked=is_liked,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )

    def _post_to_list_item(self, post: BlogPost) -> BlogPostListItem:
        """Convert BlogPost model to list item schema."""
        categories = [
            BlogCategoryBrief(
                id=pc.category.id,
                name=pc.category.name,
                slug=pc.category.slug,
                icon=pc.category.icon,
                color=pc.category.color,
            )
            for pc in post.categories
        ]

        tags = [
            BlogTagBrief(
                id=pt.tag.id,
                name=pt.tag.name,
                slug=pt.tag.slug,
                color=pt.tag.color,
            )
            for pt in post.tags
        ]

        return BlogPostListItem(
            id=post.id,
            title=post.title,
            slug=post.slug,
            excerpt=post.excerpt,
            featured_image_url=post.featured_image_url,
            status=post.status,
            visibility=post.visibility,
            is_featured=post.is_featured,
            is_pinned=post.is_pinned,
            published_at=post.published_at,
            view_count=post.view_count,
            like_count=post.like_count,
            comment_count=post.comment_count,
            reading_time=post.reading_time,
            author=AuthorBrief(
                id=post.author.id,
                username=post.author.username,
                display_name=post.author.display_name,
                avatar_url=post.author.avatar_url,
            ),
            categories=categories,
            tags=tags,
            created_at=post.created_at,
        )

    def _comment_to_response(self, comment) -> BlogCommentResponse:
        """Convert BlogComment model to response schema."""
        return BlogCommentResponse(
            id=comment.id,
            post_id=comment.post_id,
            content=comment.content,
            parent_id=comment.parent_id,
            is_approved=comment.is_approved,
            author=AuthorBrief(
                id=comment.author.id,
                username=comment.author.username,
                display_name=comment.author.display_name,
                avatar_url=comment.author.avatar_url,
            ),
            created_at=comment.created_at,
            updated_at=comment.updated_at,
        )
