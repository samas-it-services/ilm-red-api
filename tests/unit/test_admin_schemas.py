"""Unit tests for admin schemas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.book import Book
from app.schemas.admin import AdminBookListParams, AdminBookResponse


class TestAdminBookResponse:
    """Test AdminBookResponse schema."""

    def test_admin_book_response_from_book_model(self):
        """Test AdminBookResponse can be created from Book model."""
        # Create a mock book
        book = Book(
            id=uuid4(),
            owner_id=uuid4(),
            title="Test Book",
            author="Test Author",
            description="Test description",
            category="quran",
            language="en",
            visibility="public",
            file_path="/path/to/file.pdf",
            file_hash="abc123",
            file_size=1000,
            file_type="pdf",
            page_count=100,
            cover_url="https://example.com/cover.jpg",
            status="ready",
            stats={"views": 10, "downloads": 5, "rating_count": 3, "rating_avg": 4.5},
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # Validate with AdminBookResponse
        response = AdminBookResponse.model_validate(book)

        # Assert fields are correctly mapped
        assert response.id == book.id
        assert response.title == book.title
        assert response.author == book.author
        assert response.visibility == "public"
        assert response.page_count == 100
        assert response.processing_status == "ready"

    def test_admin_book_response_field_mapping(self):
        """Test that AdminBookResponse uses correct field names."""
        # Create a book with all fields
        book_data = {
            "id": uuid4(),
            "owner_id": uuid4(),
            "title": "Test Book",
            "author": "Test Author",
            "description": "Test description",
            "category": "hadith",
            "visibility": "private",  # Not is_public
            "page_count": 50,  # Not pages_count
            "cover_url": None,
            "file_url": None,
            "average_rating": 4.2,
            "ratings_count": 5,
            "processing_status": "ready",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        # Should validate successfully
        response = AdminBookResponse(**book_data)
        assert response.visibility == "private"
        assert response.page_count == 50

    def test_admin_book_response_visibility_values(self):
        """Test that visibility only accepts valid literal values."""
        base_data = {
            "id": uuid4(),
            "owner_id": uuid4(),
            "title": "Test",
            "author": "Author",
            "category": "quran",
            "visibility": "public",
            "page_count": None,
            "average_rating": None,
            "ratings_count": 0,
            "created_at": datetime.now(UTC),
        }

        # Valid values
        for visibility in ["public", "private", "friends"]:
            data = {**base_data, "visibility": visibility}
            response = AdminBookResponse(**data)
            assert response.visibility == visibility

        # Invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            invalid_data = {**base_data, "visibility": "invalid"}
            AdminBookResponse(**invalid_data)

    def test_admin_book_response_optional_page_count(self):
        """Test that page_count can be None."""
        book_data = {
            "id": uuid4(),
            "owner_id": uuid4(),
            "title": "Test Book",
            "visibility": "public",
            "page_count": None,  # Should be allowed
            "average_rating": None,
            "ratings_count": 0,
            "processing_status": "pending",
            "created_at": datetime.now(UTC),
        }

        response = AdminBookResponse(**book_data)
        assert response.page_count is None


class TestAdminBookListParams:
    """Test AdminBookListParams schema."""

    def test_admin_book_list_params_visibility_filter(self):
        """Test that visibility filter accepts valid values."""
        # Valid values
        for visibility in ["public", "private", "friends", None]:
            params = AdminBookListParams(visibility=visibility)
            assert params.visibility == visibility

        # Invalid value should raise ValidationError
        with pytest.raises(ValidationError):
            AdminBookListParams(visibility="invalid")

    def test_admin_book_list_params_defaults(self):
        """Test default values for AdminBookListParams."""
        params = AdminBookListParams()

        assert params.search is None
        assert params.category is None
        assert params.owner_id is None
        assert params.visibility is None
        assert params.has_pages is None
        assert params.page == 1
        assert params.page_size == 20

    def test_admin_book_list_params_page_validation(self):
        """Test page number validation."""
        # Valid page numbers
        params = AdminBookListParams(page=1)
        assert params.page == 1

        params = AdminBookListParams(page=100)
        assert params.page == 100

        # Invalid page number (< 1)
        with pytest.raises(ValidationError):
            AdminBookListParams(page=0)

        with pytest.raises(ValidationError):
            AdminBookListParams(page=-1)

    def test_admin_book_list_params_page_size_validation(self):
        """Test page size validation."""
        # Valid page sizes
        params = AdminBookListParams(page_size=1)
        assert params.page_size == 1

        params = AdminBookListParams(page_size=100)
        assert params.page_size == 100

        # Invalid page size (< 1)
        with pytest.raises(ValidationError):
            AdminBookListParams(page_size=0)

        # Invalid page size (> 100)
        with pytest.raises(ValidationError):
            AdminBookListParams(page_size=101)
