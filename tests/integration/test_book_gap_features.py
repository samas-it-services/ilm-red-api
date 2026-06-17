"""Tests for gap-analysis backend features.

Covers:
  - Global vs same-owner duplicate detection on upload.
  - Book view increment (and skipping the owner's own views).
  - Self-serve chat enablement: enqueue, quota enforcement, premium/admin bypass.
"""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token, hash_password
from app.models.book import Book, BookAIProcessing
from app.models.user import User


def create_fake_txt(content: str = "This is test content for a book.") -> io.BytesIO:
    """Create a fake TXT file for testing."""
    return io.BytesIO(content.encode("utf-8"))


async def _make_user(
    db: AsyncSession,
    email: str,
    username: str,
    roles: list[str] | None = None,
) -> User:
    user = User(
        email=email,
        username=username,
        display_name=username.title(),
        password_hash=hash_password("testpassword123"),
        roles=roles or ["user"],
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _headers(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}


async def _make_book(
    db: AsyncSession,
    owner: User,
    *,
    title: str = "A Book",
    visibility: str = "public",
    file_hash: str = "hash-abc",
    status: str = "ready",
) -> Book:
    book = Book(
        owner_id=owner.id,
        title=title,
        author="Author",
        category="other",
        visibility=visibility,
        file_path=f"books/{owner.id}/{title}/file.pdf",
        file_hash=file_hash,
        file_size=1024,
        file_type="pdf",
        status=status,
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


# --------------------------------------------------------------------------- #
# TASK 1: Duplicate detection (global vs same-owner)
# --------------------------------------------------------------------------- #


class TestDuplicateDetection:
    @pytest.mark.asyncio
    async def test_same_owner_duplicate_blocked(
        self, authenticated_client: AsyncClient
    ):
        """Re-uploading the same file as the same owner returns 409."""
        content = "Duplicate detection content - identical bytes."

        r1 = await authenticated_client.post(
            "/v1/books",
            files={"file": ("a.txt", create_fake_txt(content), "text/plain")},
            data={"title": "First", "category": "other"},
        )
        assert r1.status_code == 201
        assert r1.json()["is_global_duplicate"] is False

        r2 = await authenticated_client.post(
            "/v1/books",
            files={"file": ("b.txt", create_fake_txt(content), "text/plain")},
            data={"title": "Second", "category": "other"},
        )
        assert r2.status_code == 409
        assert "already exists" in r2.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_different_owner_global_duplicate_allowed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """A different owner uploading the same file is allowed but flagged."""
        content = "Cross-user identical content for global dedup."

        # First user uploads.
        client.headers.update(_headers(test_user))
        r1 = await client.post(
            "/v1/books",
            files={"file": ("a.txt", create_fake_txt(content), "text/plain")},
            data={"title": "Owner1 Book", "category": "other"},
        )
        assert r1.status_code == 201
        assert r1.json()["is_global_duplicate"] is False

        # Second user uploads the identical file.
        other = await _make_user(db_session, "owner2@example.com", "owner2")
        client.headers.clear()
        client.headers.update(_headers(other))
        r2 = await client.post(
            "/v1/books",
            files={"file": ("a.txt", create_fake_txt(content), "text/plain")},
            data={"title": "Owner2 Book", "category": "other"},
        )
        assert r2.status_code == 201
        assert r2.json()["is_global_duplicate"] is True


# --------------------------------------------------------------------------- #
# TASK 2: View tracking
# --------------------------------------------------------------------------- #


class TestViewTracking:
    @pytest.mark.asyncio
    async def test_anonymous_read_increments_views(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """An anonymous read of a public book increments the view counter."""
        book = await _make_book(db_session, test_user, file_hash="view-1")

        r = await client.get(f"/v1/books/{book.id}")
        assert r.status_code == 200

        await db_session.refresh(book)
        assert book.stats["views"] == 1

    @pytest.mark.asyncio
    async def test_owner_view_does_not_increment(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """The owner viewing their own book does NOT increment views."""
        book = await _make_book(db_session, test_user, file_hash="view-2")

        client.headers.update(_headers(test_user))
        r = await client.get(f"/v1/books/{book.id}")
        assert r.status_code == 200

        await db_session.refresh(book)
        assert book.stats["views"] == 0

    @pytest.mark.asyncio
    async def test_view_endpoint_returns_stats(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """POST /{id}/view records a view and returns updated stats."""
        book = await _make_book(db_session, test_user, file_hash="view-3")

        r = await client.post(f"/v1/books/{book.id}/view")
        assert r.status_code == 200
        assert r.json()["views"] == 1


# --------------------------------------------------------------------------- #
# TASK 3: Self-serve chat enablement + quota
# --------------------------------------------------------------------------- #


class TestChatEnable:
    @pytest.mark.asyncio
    async def test_enable_chat_enqueues_job(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Owner can enable chat; a pending processing job is created."""
        book = await _make_book(db_session, test_user, file_hash="chat-1")

        client.headers.update(_headers(test_user))
        r = await client.post(f"/v1/books/{book.id}/chat/enable")
        assert r.status_code == 202
        body = r.json()
        assert body["status"] == "pending"
        assert body["already_enabled"] is False
        assert body["quota"]["used"] == 1

        jobs = (
            (
                await db_session.execute(
                    select(BookAIProcessing).where(
                        BookAIProcessing.book_id == book.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(jobs) == 1
        assert jobs[0].processing_type == "chat"

    @pytest.mark.asyncio
    async def test_enable_chat_is_idempotent(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Re-enabling an already-enabled book does not create a second job."""
        book = await _make_book(db_session, test_user, file_hash="chat-2")
        client.headers.update(_headers(test_user))

        r1 = await client.post(f"/v1/books/{book.id}/chat/enable")
        assert r1.status_code == 202
        assert r1.json()["already_enabled"] is False

        r2 = await client.post(f"/v1/books/{book.id}/chat/enable")
        assert r2.status_code == 202
        assert r2.json()["already_enabled"] is True

        jobs = (
            (
                await db_session.execute(
                    select(BookAIProcessing).where(
                        BookAIProcessing.book_id == book.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(jobs) == 1

    @pytest.mark.asyncio
    async def test_enable_chat_not_owner_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """A non-owner cannot enable chat for someone else's book."""
        book = await _make_book(db_session, test_user, file_hash="chat-3")
        other = await _make_user(db_session, "stranger@example.com", "stranger")

        client.headers.update(_headers(other))
        r = await client.post(f"/v1/books/{book.id}/chat/enable")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_quota_enforced_for_free_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        monkeypatch,
    ):
        """Free users hit a 429 once their monthly quota is exhausted."""
        monkeypatch.setattr(settings, "chat_enable_monthly_quota_free", 2)
        client.headers.update(_headers(test_user))

        # Two distinct books -> both succeed (quota = 2).
        for i in range(2):
            book = await _make_book(
                db_session, test_user, title=f"Q{i}", file_hash=f"quota-{i}"
            )
            r = await client.post(f"/v1/books/{book.id}/chat/enable")
            assert r.status_code == 202

        # Third book -> quota exhausted.
        book3 = await _make_book(
            db_session, test_user, title="Q3", file_hash="quota-3"
        )
        r3 = await client.post(f"/v1/books/{book3.id}/chat/enable")
        assert r3.status_code == 429
        assert "quota" in r3.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_premium_user_bypasses_quota(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        monkeypatch,
    ):
        """Premium users are unlimited regardless of the free quota."""
        monkeypatch.setattr(settings, "chat_enable_monthly_quota_free", 1)
        premium = await _make_user(
            db_session, "prem@example.com", "premuser", roles=["user", "premium"]
        )
        client.headers.update(_headers(premium))

        for i in range(3):
            book = await _make_book(
                db_session, premium, title=f"P{i}", file_hash=f"prem-{i}"
            )
            r = await client.post(f"/v1/books/{book.id}/chat/enable")
            assert r.status_code == 202
            assert r.json()["quota"]["is_unlimited"] is True
            assert r.json()["quota"]["limit"] is None
