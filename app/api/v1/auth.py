"""Authentication endpoints."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    generate_api_key,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.user import OAuthAccount, User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    AuthMeResponse,
    AuthTokenResponse,
    GoogleOAuthRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="""
Create a new user account and receive authentication tokens.

**Password Requirements:**
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

**Example:**
```bash
curl -X POST /v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email":"user@example.com","password":"SecurePass123!","username":"johndoe","display_name":"John Doe"}'
```

**Returns:** JWT access token (15 min) and refresh token (7 days)
    """,
    responses={
        409: {"description": "Email or username already exists"},
        422: {"description": "Validation error (weak password, invalid email format, etc.)"},
    },
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user account."""
    user_repo = UserRepository(db)

    # Check if email already exists
    existing = await user_repo.get_by_email(data.email)
    if existing:
        raise ConflictError("Email already registered")

    # Check if username already exists
    existing = await user_repo.get_by_username(data.username)
    if existing:
        raise ConflictError("Username already taken")

    # Create user
    password_hash = hash_password(data.password)
    user = await user_repo.create(
        email=data.email,
        username=data.username,
        display_name=data.display_name,
        password_hash=password_hash,
    )

    logger.info("User registered", user_id=str(user.id), email=user.email)

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))

    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
    description="""
Authenticate with email and password to receive tokens.

**Security:** Password is verified using Argon2 hashing.

**Example:**
```bash
curl -X POST /v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"user@example.com","password":"SecurePass123!"}'
```

**After Login:**
Use the `access_token` in the Authorization header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```
    """,
    responses={
        401: {"description": "Invalid email or password"},
        403: {"description": "Account suspended or inactive"},
    },
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user with email and password."""
    user_repo = UserRepository(db)

    # Find user
    user = await user_repo.get_by_email(data.email)
    if not user or not user.password_hash:
        raise UnauthorizedError("Invalid email or password")

    # Verify password
    if not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")

    # Check user status
    if user.status != "active":
        raise UnauthorizedError("Account is not active")

    # Update last login
    await user_repo.update_last_login(user)

    logger.info("User logged in", user_id=str(user.id))

    # Generate tokens
    access_token = create_access_token(subject=str(user.id))

    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
Exchange a refresh token for a new access token.

**Token Rotation:** For security, the old refresh token is revoked and a new one is issued.

**When to Use:**
- Access tokens expire in 15 minutes
- Call this endpoint before expiration to maintain session
- Refresh tokens expire in 7 days

**Example:**
```bash
curl -X POST /v1/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{"refresh_token":"your_refresh_token_here"}'
```
    """,
    responses={
        401: {"description": "Invalid or expired refresh token"},
    },
)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    user_repo = UserRepository(db)

    # Hash the provided token
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()

    # Find the refresh token
    token = await user_repo.get_refresh_token(token_hash)
    if not token or not token.is_valid:
        raise UnauthorizedError("Invalid or expired refresh token")

    # Get user
    user = await user_repo.get_by_id(token.user_id)
    if not user or user.status != "active":
        raise UnauthorizedError("User not found or inactive")

    # Revoke old token (token rotation)
    await user_repo.revoke_refresh_token(token)

    logger.info("Token refreshed", user_id=str(user.id))

    # Generate new tokens
    access_token = create_access_token(subject=str(user.id))

    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke refresh token",
    description="""
End session by revoking the refresh token.

**Note:** The access token remains valid until it expires (15 min max).
For immediate client-side logout, also discard the access token locally.

**Example:**
```bash
curl -X POST /v1/auth/logout \\
  -H "Content-Type: application/json" \\
  -d '{"refresh_token":"your_refresh_token_here"}'
```
    """,
)
async def logout(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout by revoking the refresh token."""
    user_repo = UserRepository(db)

    # Hash the provided token
    token_hash = hashlib.sha256(data.refresh_token.encode()).hexdigest()

    # Find and revoke the refresh token
    token = await user_repo.get_refresh_token(token_hash)
    if token and token.is_valid:
        await user_repo.revoke_refresh_token(token)
        logger.info("User logged out", user_id=str(token.user_id))


# API Key endpoints
@router.get(
    "/api-keys",
    response_model=list[ApiKeyResponse],
    summary="List API keys",
    description="""
Get all API keys for the authenticated user.

**Security:** Only the key prefix is returned (e.g., `ilm_abc12345...`), not the full key.

**Use Case:** View active keys, check last usage, manage key lifecycle.

**Requires:** Bearer token authentication
    """,
)
async def list_api_keys(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyResponse]:
    """List all API keys for the current user."""
    user_repo = UserRepository(db)
    keys = await user_repo.get_api_keys(current_user.id)
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post(
    "/api-keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create API key",
    description="""
Generate a new API key for server-to-server integrations.

**IMPORTANT:** The full API key is only shown ONCE in this response. Store it securely!

**Example:**
```bash
curl -X POST /v1/auth/api-keys \\
  -H "Authorization: Bearer <token>" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"Production Server","permissions":["read","write"],"expires_in_days":90}'
```

**Permissions:**
- `read` - Read-only access to books, profiles
- `write` - Create/update books, chat messages
- `admin` - Administrative operations (if authorized)

**Usage:**
```
X-API-Key: ilm_live_abc123...
```
    """,
)
async def create_api_key(
    data: ApiKeyCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """Create a new API key."""
    user_repo = UserRepository(db)

    # Generate the key
    full_key, key_prefix, key_hash = generate_api_key()

    # Calculate expiration
    expires_at = None
    if data.expires_in_days:
        expires_at = datetime.now(UTC) + timedelta(days=data.expires_in_days)

    # Create the key
    api_key = await user_repo.create_api_key(
        user_id=current_user.id,
        name=data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        permissions=data.permissions,
        expires_at=expires_at,
    )

    logger.info("API key created", user_id=str(current_user.id), key_name=data.name)

    return ApiKeyCreatedResponse(
        api_key=full_key,
        key_info=ApiKeyResponse.model_validate(api_key),
    )


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete API key",
    description="""
Permanently revoke an API key.

**Effect:** Any requests using this key will immediately receive 401 Unauthorized.

**Example:**
```bash
curl -X DELETE /v1/auth/api-keys/550e8400-e29b-41d4-a716-446655440000 \\
  -H "Authorization: Bearer <token>"
```
    """,
    responses={
        404: {"description": "API key not found or doesn't belong to you"},
    },
)
async def delete_api_key(
    key_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an API key."""
    user_repo = UserRepository(db)

    from uuid import UUID
    api_key = await user_repo.get_api_key_by_id(UUID(key_id))

    if not api_key or api_key.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="API key not found")

    await user_repo.delete_api_key(api_key)
    logger.info("API key deleted", user_id=str(current_user.id), key_id=key_id)


# --- Google OAuth endpoints ---


@router.post(
    "/oauth/google/token",
    response_model=AuthTokenResponse,
    summary="Exchange Google OAuth code for tokens",
    description="""
Exchange a Google authorization code for JWT access and refresh tokens.

**OAuth Flow:**
1. Frontend redirects user to Google consent screen
2. Google redirects back with an authorization code
3. Frontend sends the code to this endpoint
4. Backend verifies the code with Google, creates/links user account
5. Returns JWT tokens and user profile

**Example:**
```bash
curl -X POST /v1/auth/oauth/google/token \\
  -H "Content-Type: application/json" \\
  -d '{"code":"4/0AX4XfWh...","redirect_uri":"http://localhost:3000/auth/callback"}'
```

**Returns:** JWT access token, refresh token, user profile, and `is_new_user` flag
    """,
    responses={
        400: {"description": "Invalid authorization code or OAuth error"},
        501: {"description": "Google OAuth not configured on this server"},
    },
)
async def google_oauth_token(
    data: GoogleOAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthTokenResponse:
    """Exchange Google OAuth authorization code for JWT tokens."""
    # Verify Google OAuth is configured
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured on this server",
        )

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth dependencies (google-auth) are not installed",
        )

    # Exchange the authorization code for an ID token
    try:
        # Use Google's token endpoint to exchange the code
        import httpx

        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": data.code,
                    "client_id": settings.google_oauth_client_id,
                    "client_secret": settings.google_oauth_client_secret,
                    "redirect_uri": data.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

        if token_response.status_code != 200:
            logger.warning(
                "Google token exchange failed",
                status_code=token_response.status_code,
                response=token_response.text,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code with Google",
            )

        token_data = token_response.json()
        id_token_str = token_data.get("id_token")

        if not id_token_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from Google",
            )

        # Verify the ID token
        id_info = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.google_oauth_client_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Google OAuth verification failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth verification failed: {str(e)}",
        )

    # Extract user info from the verified token
    google_user_id = id_info.get("sub")
    email = id_info.get("email")
    email_verified = id_info.get("email_verified", False)
    name = id_info.get("name", "")
    picture = id_info.get("picture")

    if not google_user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete user information from Google",
        )

    user_repo = UserRepository(db)
    is_new_user = False

    # Look for existing OAuth account
    stmt = select(OAuthAccount).where(
        OAuthAccount.provider == "google",
        OAuthAccount.provider_user_id == google_user_id,
    )
    result = await db.execute(stmt)
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        # Existing OAuth link - get the user
        user = await user_repo.get_by_id(oauth_account.user_id)
        if not user or user.status != "active":
            raise UnauthorizedError("User account is not active")

        # Update OAuth tokens
        oauth_account.access_token = token_data.get("access_token")
        oauth_account.refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")
        if expires_in:
            oauth_account.expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))
        await db.flush()
    else:
        # Check if user exists with this email
        user = await user_repo.get_by_email(email)

        if user:
            # Link OAuth to existing user
            is_new_user = False
        else:
            # Create new user
            is_new_user = True

            # Generate a unique username from the email prefix
            base_username = email.split("@")[0].lower()
            # Sanitize: keep only alphanumeric, underscore, hyphen
            base_username = "".join(
                c for c in base_username if c.isalnum() or c in ("_", "-")
            )
            if len(base_username) < 3:
                base_username = f"user_{base_username}"

            # Ensure uniqueness
            username = base_username
            existing = await user_repo.get_by_username(username)
            while existing:
                username = f"{base_username}_{secrets.token_hex(3)}"
                existing = await user_repo.get_by_username(username)

            user = await user_repo.create(
                email=email,
                username=username,
                display_name=name or username,
                password_hash=None,  # OAuth user, no password
            )

            # Set email as verified if Google says so
            if email_verified:
                user.email_verified = True

            # Set profile picture from Google
            if picture:
                user.profile_picture_url = picture
                user.avatar_url = picture

            # Set full name from Google
            if name:
                user.full_name = name

            await db.flush()

        # Create OAuth account link
        new_oauth = OAuthAccount(
            user_id=user.id,
            provider="google",
            provider_user_id=google_user_id,
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
        )
        expires_in = token_data.get("expires_in")
        if expires_in:
            new_oauth.expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))
        db.add(new_oauth)
        await db.flush()

    # Update last login
    await user_repo.update_last_login(user)

    logger.info(
        "Google OAuth login",
        user_id=str(user.id),
        is_new_user=is_new_user,
    )

    # Generate JWT tokens
    access_token = create_access_token(subject=str(user.id))
    raw_refresh, refresh_hash = create_refresh_token(subject=str(user.id))
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)
    await user_repo.create_refresh_token(user.id, refresh_hash, expires_at)

    await db.commit()

    return AuthTokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "profile_picture_url": user.profile_picture_url,
            "email_verified": user.email_verified,
            "roles": user.roles,
        },
        is_new_user=is_new_user,
    )


@router.get(
    "/me",
    response_model=AuthMeResponse,
    summary="Get current user profile",
    description="""
Get the authenticated user's full profile including roles and RBAC permissions.

**Includes:**
- All user profile fields
- Role assignments (from the `roles` column)
- RBAC permissions (resolved from role-permission mappings)

**Example:**
```bash
curl -X GET /v1/auth/me \\
  -H "Authorization: Bearer <token>"
```

**Requires:** Bearer token or API key authentication
    """,
    responses={
        401: {"description": "Invalid or missing authentication credentials"},
    },
)
async def get_me(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> AuthMeResponse:
    """Get the current authenticated user's profile with roles and permissions."""
    # Resolve RBAC permissions
    permissions: list[str] = []
    try:
        from app.repositories.rbac_repo import RBACRepository

        rbac_repo = RBACRepository(db)
        permissions = await rbac_repo.get_user_permissions(current_user.id)
    except Exception:
        # RBAC may not be set up yet; degrade gracefully
        logger.debug(
            "Could not load RBAC permissions for user",
            user_id=str(current_user.id),
        )

    # Build response from the ORM model
    response = AuthMeResponse.model_validate(current_user)
    response.permissions = permissions
    return response
