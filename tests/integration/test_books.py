"""Book endpoint tests."""

import io

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.user import User


# Helper to create a fake PDF file
def create_fake_pdf(content: bytes = b"%PDF-1.4 Test PDF content") -> io.BytesIO:
    """Create a fake PDF file for testing."""
    return io.BytesIO(content)


def create_fake_txt(content: str = "This is test content for a book.") -> io.BytesIO:
    """Create a fake TXT file for testing."""
    return io.BytesIO(content.encode("utf-8"))


@pytest.fixture
async def test_book(db_session: AsyncSession, test_user: User) -> Book:
    """Create a test book."""
    book = Book(
        owner_id=test_user.id,
        title="Test Book",
        author="Test Author",
        description="A test book description",
        category="technology",
        visibility="public",
        language="en",
        file_path=f"books/{test_user.id}/test-book/file.pdf",
        file_hash="abc123def456",
        file_size=1024,
        file_type="pdf",
        status="ready",
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def private_book(db_session: AsyncSession, test_user: User) -> Book:
    """Create a private test book."""
    book = Book(
        owner_id=test_user.id,
        title="Private Book",
        author="Test Author",
        category="other",
        visibility="private",
        file_path=f"books/{test_user.id}/private-book/file.pdf",
        file_hash="private123",
        file_size=2048,
        file_type="pdf",
        status="ready",
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create another test user."""
    from app.core.security import hash_password

    user = User(
        email="other@example.com",
        username="otheruser",
        display_name="Other User",
        password_hash=hash_password("testpassword123"),
        roles=["user"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user_headers(other_user: User) -> dict[str, str]:
    """Create authentication headers for other user."""
    from app.core.security import create_access_token

    token = create_access_token(subject=str(other_user.id))
    return {"Authorization": f"Bearer {token}"}


class TestBookUpload:
    """Tests for book upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_txt_success(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test successful TXT file upload."""
        file_content = create_fake_txt("Test book content for upload testing.")

        response = await authenticated_client.post(
            "/v1/books",
            files={"file": ("test.txt", file_content, "text/plain")},
            data={
                "title": "Test Upload Book",
                "author": "Test Author",
                "category": "technology",
                "visibility": "private",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Upload Book"
        assert data["status"] == "processing"
        assert data["file_type"] == "txt"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_upload_requires_auth(
        self,
        client: AsyncClient,
    ):
        """Test that upload requires authentication."""
        file_content = create_fake_txt()

        response = await client.post(
            "/v1/books",
            files={"file": ("test.txt", file_content, "text/plain")},
            data={"title": "Test Book", "category": "other"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_upload_rejects_empty_file(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that empty files are rejected."""
        file_content = io.BytesIO(b"")

        response = await authenticated_client.post(
            "/v1/books",
            files={"file": ("test.txt", file_content, "text/plain")},
            data={"title": "Empty Book", "category": "other"},
        )

        assert response.status_code == 400
        assert "Empty file" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_upload_rejects_invalid_type(
        self,
        authenticated_client: AsyncClient,
    ):
        """Test that invalid file types are rejected."""
        file_content = io.BytesIO(b"fake image content")

        response = await authenticated_client.post(
            "/v1/books",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
            data={"title": "Image Book", "category": "other"},
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]


class TestBookCRUD:
    """Tests for book CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_books_public(
        self,
        client: AsyncClient,
        test_book: Book,
    ):
        """Test listing public books without authentication."""
        response = await client.get("/v1/books")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        # Should find the public test_book
        titles = [b["title"] for b in data["data"]]
        assert "Test Book" in titles

    @pytest.mark.asyncio
    async def test_list_books_pagination(
        self,
        client: AsyncClient,
        test_book: Book,
    ):
        """Test book listing pagination."""
        response = await client.get("/v1/books?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 10

    @pytest.mark.asyncio
    async def test_list_private_books_hidden(
        self,
        client: AsyncClient,
        test_book: Book,
        private_book: Book,
    ):
        """Test that private books are not shown to unauthenticated users."""
        response = await client.get("/v1/books")

        assert response.status_code == 200
        data = response.json()
        titles = [b["title"] for b in data["data"]]
        assert "Private Book" not in titles

    @pytest.mark.asyncio
    async def test_owner_sees_private_books(
        self,
        authenticated_client: AsyncClient,
        private_book: Book,
    ):
        """Test that owner can see their private books."""
        response = await authenticated_client.get("/v1/books")

        assert response.status_code == 200
        data = response.json()
        titles = [b["title"] for b in data["data"]]
        assert "Private Book" in titles

    @pytest.mark.asyncio
    async def test_get_book_public(
        self,
        client: AsyncClient,
        test_book: Book,
    ):
        """Test getting a public book without authentication."""
        response = await client.get(f"/v1/books/{test_book.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Book"
        assert data["author"] == "Test Author"

    @pytest.mark.asyncio
    async def test_get_book_private_denied(
        self,
        client: AsyncClient,
        private_book: Book,
    ):
        """Test that private books are not accessible without auth."""
        response = await client.get(f"/v1/books/{private_book.id}")

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_book_private_owner(
        self,
        authenticated_client: AsyncClient,
        private_book: Book,
    ):
        """Test that owner can access their private book."""
        response = await authenticated_client.get(f"/v1/books/{private_book.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Private Book"

    @pytest.mark.asyncio
    async def test_update_book_success(
        self,
        authenticated_client: AsyncClient,
        test_book: Book,
    ):
        """Test updating a book."""
        response = await authenticated_client.patch(
            f"/v1/books/{test_book.id}",
            json={"title": "Updated Title", "visibility": "private"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["visibility"] == "private"

    @pytest.mark.asyncio
    async def test_update_book_not_owner(
        self,
        client: AsyncClient,
        test_book: Book,
        other_user_headers: dict,
    ):
        """Test that non-owner cannot update book."""
        client.headers.update(other_user_headers)

        response = await client.patch(
            f"/v1/books/{test_book.id}",
            json={"title": "Hacked Title"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_book_success(
        self,
        authenticated_client: AsyncClient,
        test_book: Book,
    ):
        """Test deleting a book."""
        response = await authenticated_client.delete(f"/v1/books/{test_book.id}")

        assert response.status_code == 204

        # Verify book is no longer accessible
        response = await authenticated_client.get(f"/v1/books/{test_book.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_book_not_owner(
        self,
        client: AsyncClient,
        test_book: Book,
        other_user_headers: dict,
    ):
        """Test that non-owner cannot delete book."""
        client.headers.update(other_user_headers)

        response = await client.delete(f"/v1/books/{test_book.id}")

        assert response.status_code == 403


class TestRatings:
    """Tests for rating functionality."""

    @pytest.mark.asyncio
    async def test_add_rating_success(
        self,
        client: AsyncClient,
        test_book: Book,
        other_user_headers: dict,
    ):
        """Test adding a rating to a book."""
        client.headers.update(other_user_headers)

        response = await client.post(
            f"/v1/books/{test_book.id}/ratings",
            json={"rating": 5, "review": "Great book!"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["rating"] == 5
        assert data["review"] == "Great book!"

    @pytest.mark.asyncio
    async def test_cannot_rate_own_book(
        self,
        authenticated_client: AsyncClient,
        test_book: Book,
    ):
        """Test that owner cannot rate their own book."""
        response = await authenticated_client.post(
            f"/v1/books/{test_book.id}/ratings",
            json={"rating": 5},
        )

        assert response.status_code == 400
        assert "own book" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_ratings(
        self,
        client: AsyncClient,
        test_book: Book,
        other_user_headers: dict,
    ):
        """Test getting ratings for a book."""
        # First add a rating
        client.headers.update(other_user_headers)
        await client.post(
            f"/v1/books/{test_book.id}/ratings",
            json={"rating": 4},
        )

        # Get ratings
        client.headers.clear()
        response = await client.get(f"/v1/books/{test_book.id}/ratings")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    @pytest.mark.asyncio
    async def test_rating_requires_auth(
        self,
        client: AsyncClient,
        test_book: Book,
    ):
        """Test that rating requires authentication."""
        response = await client.post(
            f"/v1/books/{test_book.id}/ratings",
            json={"rating": 5},
        )

        assert response.status_code == 401


class TestFavorites:
    """Tests for favorites functionality."""

    @pytest.mark.asyncio
    async def test_add_favorite_success(
        self,
        client: AsyncClient,
        test_book: Book,
        other_user_headers: dict,
    ):
        """Test adding a book to favorites."""
        client.headers.update(other_user_headers)

        response = await client.post(f"/v1/books/{test_book.id}/favorite")

        assert response.status_code == 201
        assert "favorites" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_remove_favorite_success(
        self,
        client: AsyncClient,
        test_book: Book,
        other_user_headers: dict,
    ):
        """Test removing a book from favorites."""
        client.headers.update(other_user_headers)

        # First add to favorites
        await client.post(f"/v1/books/{test_book.id}/favorite")

        # Then remove
        response = await client.delete(f"/v1/books/{test_book.id}/favorite")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_favorite_requires_auth(
        self,
        client: AsyncClient,
        test_book: Book,
    ):
        """Test that favorites require authentication."""
        response = await client.post(f"/v1/books/{test_book.id}/favorite")

        assert response.status_code == 401
