"""Blog repository for database operations."""

import re
import uuid
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.blog import (
    BlogCategory,
    BlogComment,
    BlogLike,
    BlogPost,
    BlogPostCategory,
    BlogPostTag,
    BlogTag,
    BlogView,
)


def generate_slug(title: str) -> str:
    """Generate a URL-friendly slug from a title."""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


class BlogRepository:
    """Repository for blog database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------- Slug Helpers ----------

    async def _ensure_unique_slug(self, slug: str, exclude_id: uuid.UUID | None = None) -> str:
        """Ensure slug is unique, appending a suffix if necessary."""
        base_slug = slug
        counter = 1
        while True:
            stmt = select(func.count(BlogPost.id)).where(BlogPost.slug == slug)
            if exclude_id:
                stmt = stmt.where(BlogPost.id != exclude_id)
            result = await self.db.execute(stmt)
            if result.scalar_one() == 0:
                return slug
            slug = f"{base_slug}-{counter}"
            counter += 1

    # ---------- Blog Post CRUD ----------

    async def create_post(
        self,
        author_id: uuid.UUID,
        title: str,
        content: str,
        excerpt: str | None = None,
        featured_image_url: str | None = None,
        status: str = "draft",
        visibility: str = "public",
        is_featured: bool = False,
        is_pinned: bool = False,
        category_ids: list[uuid.UUID] | None = None,
        tag_ids: list[uuid.UUID] | None = None,
    ) -> BlogPost:
        """Create a new blog post."""
        slug = generate_slug(title)
        slug = await self._ensure_unique_slug(slug)

        # Calculate reading metrics
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)  # ~200 WPM

        published_at = datetime.now(UTC) if status == "published" else None

        post = BlogPost(
            author_id=author_id,
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            featured_image_url=featured_image_url,
            status=status,
            visibility=visibility,
            is_featured=is_featured,
            is_pinned=is_pinned,
            published_at=published_at,
            word_count=word_count,
            reading_time=reading_time,
        )
        self.db.add(post)
        await self.db.flush()
        await self.db.refresh(post)

        # Add categories
        if category_ids:
            for cid in category_ids:
                self.db.add(BlogPostCategory(post_id=post.id, category_id=cid))

        # Add tags
        if tag_ids:
            for tid in tag_ids:
                self.db.add(BlogPostTag(post_id=post.id, tag_id=tid))

        await self.db.flush()
        return post

    async def get_post_by_id(self, post_id: uuid.UUID) -> BlogPost | None:
        """Get blog post by ID with relationships."""
        stmt = (
            select(BlogPost)
            .options(
                joinedload(BlogPost.author),
                joinedload(BlogPost.categories).joinedload(BlogPostCategory.category),
                joinedload(BlogPost.tags).joinedload(BlogPostTag.tag),
            )
            .where(BlogPost.id == post_id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_post_by_slug(self, slug: str) -> BlogPost | None:
        """Get blog post by slug with relationships."""
        stmt = (
            select(BlogPost)
            .options(
                joinedload(BlogPost.author),
                joinedload(BlogPost.categories).joinedload(BlogPostCategory.category),
                joinedload(BlogPost.tags).joinedload(BlogPostTag.tag),
            )
            .where(BlogPost.slug == slug)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def list_posts(
        self,
        status: str | None = None,
        category_slug: str | None = None,
        tag_slug: str | None = None,
        search_query: str | None = None,
        author_id: uuid.UUID | None = None,
        is_featured: bool | None = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "published_at",
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> tuple[list[BlogPost], int]:
        """List blog posts with filtering and pagination."""
        base_conditions = []

        if status:
            base_conditions.append(BlogPost.status == status)

        if author_id:
            base_conditions.append(BlogPost.author_id == author_id)

        if is_featured is not None:
            base_conditions.append(BlogPost.is_featured == is_featured)

        if category_slug:
            base_conditions.append(
                BlogPost.id.in_(
                    select(BlogPostCategory.post_id)
                    .join(BlogCategory, BlogPostCategory.category_id == BlogCategory.id)
                    .where(BlogCategory.slug == category_slug)
                )
            )

        if tag_slug:
            base_conditions.append(
                BlogPost.id.in_(
                    select(BlogPostTag.post_id)
                    .join(BlogTag, BlogPostTag.tag_id == BlogTag.id)
                    .where(BlogTag.slug == tag_slug)
                )
            )

        if search_query:
            search_pattern = f"%{search_query}%"
            base_conditions.append(
                or_(
                    BlogPost.title.ilike(search_pattern),
                    BlogPost.content.ilike(search_pattern),
                    BlogPost.excerpt.ilike(search_pattern),
                )
            )

        where_clause = and_(*base_conditions) if base_conditions else True

        # Count query
        count_stmt = select(func.count(BlogPost.id)).where(where_clause)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        stmt = (
            select(BlogPost)
            .options(
                joinedload(BlogPost.author),
                joinedload(BlogPost.categories).joinedload(BlogPostCategory.category),
                joinedload(BlogPost.tags).joinedload(BlogPostTag.tag),
            )
            .where(where_clause)
        )

        # Sorting — pinned posts first, then by sort field
        sort_column = getattr(BlogPost, sort_by, BlogPost.published_at)
        if sort_order == "desc":
            stmt = stmt.order_by(BlogPost.is_pinned.desc(), sort_column.desc())
        else:
            stmt = stmt.order_by(BlogPost.is_pinned.desc(), sort_column.asc())

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        posts = list(result.unique().scalars().all())

        return posts, total

    async def update_post(self, post: BlogPost, **kwargs) -> BlogPost:
        """Update blog post fields."""
        for key, value in kwargs.items():
            if hasattr(post, key) and value is not None:
                setattr(post, key, value)

        # Recalculate reading metrics if content changed
        if "content" in kwargs and kwargs["content"] is not None:
            post.word_count = len(post.content.split())
            post.reading_time = max(1, post.word_count // 200)

        # Set published_at when publishing
        if kwargs.get("status") == "published" and post.published_at is None:
            post.published_at = datetime.now(UTC)

        post.updated_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(post)
        return post

    async def update_post_categories(
        self,
        post_id: uuid.UUID,
        category_ids: list[uuid.UUID],
    ) -> None:
        """Replace all categories for a post."""
        # Delete existing
        stmt = select(BlogPostCategory).where(BlogPostCategory.post_id == post_id)
        result = await self.db.execute(stmt)
        for pc in result.scalars().all():
            await self.db.delete(pc)

        # Add new
        for cid in category_ids:
            self.db.add(BlogPostCategory(post_id=post_id, category_id=cid))
        await self.db.flush()

    async def update_post_tags(
        self,
        post_id: uuid.UUID,
        tag_ids: list[uuid.UUID],
    ) -> None:
        """Replace all tags for a post."""
        # Delete existing
        stmt = select(BlogPostTag).where(BlogPostTag.post_id == post_id)
        result = await self.db.execute(stmt)
        for pt in result.scalars().all():
            await self.db.delete(pt)

        # Add new
        for tid in tag_ids:
            self.db.add(BlogPostTag(post_id=post_id, tag_id=tid))
        await self.db.flush()

    async def delete_post(self, post: BlogPost) -> None:
        """Delete a blog post."""
        await self.db.delete(post)
        await self.db.flush()

    # ---------- Like Operations ----------

    async def add_like(self, post_id: uuid.UUID, user_id: uuid.UUID) -> BlogLike:
        """Add a like to a post."""
        existing = await self.get_like(post_id, user_id)
        if existing:
            return existing

        like = BlogLike(post_id=post_id, user_id=user_id)
        self.db.add(like)
        await self.db.flush()

        # Update denormalized count
        await self._update_like_count(post_id)
        return like

    async def remove_like(self, post_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove a like from a post. Returns True if removed."""
        like = await self.get_like(post_id, user_id)
        if like:
            await self.db.delete(like)
            await self.db.flush()
            await self._update_like_count(post_id)
            return True
        return False

    async def get_like(self, post_id: uuid.UUID, user_id: uuid.UUID) -> BlogLike | None:
        """Get a specific like."""
        stmt = select(BlogLike).where(
            and_(BlogLike.post_id == post_id, BlogLike.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _update_like_count(self, post_id: uuid.UUID) -> None:
        """Update denormalized like count on the post."""
        count_stmt = select(func.count(BlogLike.id)).where(BlogLike.post_id == post_id)
        result = await self.db.execute(count_stmt)
        count = result.scalar_one()

        stmt = update(BlogPost).where(BlogPost.id == post_id).values(like_count=count)
        await self.db.execute(stmt)
        await self.db.flush()

    # ---------- Comment Operations ----------

    async def create_comment(
        self,
        post_id: uuid.UUID,
        author_id: uuid.UUID,
        content: str,
        parent_id: uuid.UUID | None = None,
    ) -> BlogComment:
        """Create a comment on a post."""
        comment = BlogComment(
            post_id=post_id,
            author_id=author_id,
            content=content,
            parent_id=parent_id,
        )
        self.db.add(comment)
        await self.db.flush()
        await self.db.refresh(comment)

        # Update denormalized count
        await self._update_comment_count(post_id)
        return comment

    async def get_comments(
        self,
        post_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[BlogComment], int]:
        """Get comments for a post with pagination."""
        base_conditions = [
            BlogComment.post_id == post_id,
            BlogComment.is_approved.is_(True),
        ]

        # Count
        count_stmt = select(func.count(BlogComment.id)).where(and_(*base_conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar_one()

        # Data
        offset = (page - 1) * limit
        stmt = (
            select(BlogComment)
            .options(joinedload(BlogComment.author))
            .where(and_(*base_conditions))
            .order_by(BlogComment.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        comments = list(result.unique().scalars().all())

        return comments, total

    async def _update_comment_count(self, post_id: uuid.UUID) -> None:
        """Update denormalized comment count on the post."""
        count_stmt = select(func.count(BlogComment.id)).where(
            and_(BlogComment.post_id == post_id, BlogComment.is_approved.is_(True))
        )
        result = await self.db.execute(count_stmt)
        count = result.scalar_one()

        stmt = update(BlogPost).where(BlogPost.id == post_id).values(comment_count=count)
        await self.db.execute(stmt)
        await self.db.flush()

    # ---------- View Tracking ----------

    async def track_view(
        self,
        post_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Track a post view."""
        view = BlogView(
            post_id=post_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(view)

        # Update denormalized count
        stmt = update(BlogPost).where(BlogPost.id == post_id).values(
            view_count=BlogPost.view_count + 1
        )
        await self.db.execute(stmt)
        await self.db.flush()

    # ---------- Category Operations ----------

    async def create_category(self, **kwargs) -> BlogCategory:
        """Create a blog category."""
        if not kwargs.get("slug"):
            kwargs["slug"] = generate_slug(kwargs["name"])
        category = BlogCategory(**kwargs)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category

    async def get_categories(self, active_only: bool = True) -> list[BlogCategory]:
        """Get all blog categories."""
        stmt = select(BlogCategory)
        if active_only:
            stmt = stmt.where(BlogCategory.is_active.is_(True))
        stmt = stmt.order_by(BlogCategory.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---------- Tag Operations ----------

    async def create_tag(self, **kwargs) -> BlogTag:
        """Create a blog tag."""
        if not kwargs.get("slug"):
            kwargs["slug"] = generate_slug(kwargs["name"])
        tag = BlogTag(**kwargs)
        self.db.add(tag)
        await self.db.flush()
        await self.db.refresh(tag)
        return tag

    async def get_tags(self) -> list[BlogTag]:
        """Get all blog tags."""
        stmt = select(BlogTag).order_by(BlogTag.name.asc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
