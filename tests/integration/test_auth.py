"""Authentication endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        "/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "username": "newuser",
            "display_name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test registration with duplicate email fails."""
    response = await client.post(
        "/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "securepassword123",
            "username": "differentuser",
            "display_name": "Different User",
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """Test successful login."""
    response = await client.post(
        "/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "testpassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password fails."""
    response = await client.post(
        "/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(authenticated_client: AsyncClient, test_user):
    """Test getting current user profile."""
    response = await authenticated_client.get("/v1/users/me")

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["username"] == test_user.username


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    """Test accessing protected endpoint without auth."""
    response = await client.get("/v1/users/me")

    assert response.status_code == 401
