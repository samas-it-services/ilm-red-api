"""FastAPI application entry point."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.cache.redis_client import RedisCache
from app.config import settings
from app.db.session import close_db, init_db
from app.rate_limiter import limiter

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.is_production else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Admin API tag descriptions
ADMIN_OPENAPI_TAGS = [
    {
        "name": "Admin - Users",
        "description": """
**User Management (Admin Only)**

List, view, edit, and disable user accounts.

**Capabilities:**
- Search users by email, username, display name
- Filter by status (active, suspended, deleted)
- Update user roles and status
- Disable accounts for policy violations
        """,
    },
    {
        "name": "Admin - Books",
        "description": """
**Book Management (Admin Only)**

Manage all books and trigger processing operations.

**Processing Actions:**
- Generate page images from PDF
- Regenerate thumbnails
- Process AI embeddings and chunks
        """,
    },
    {
        "name": "Admin - Chats",
        "description": """
**Chat Session Management (Admin Only)**

View and delete chat sessions across all users.

**Features:**
- List all chat sessions
- View session details with messages
- Delete sessions for compliance
        """,
    },
    {
        "name": "Admin - Cache",
        "description": """
**Redis Cache Management (Admin Only)**

Monitor and manage the Redis cache.

**Operations:**
- View cache statistics and health
- Invalidate cache by pattern
- Delete specific keys
- Flush all cache (use with caution)
        """,
    },
    {
        "name": "Admin - Stats",
        "description": """
**System Statistics (Admin Only)**

View comprehensive system metrics.

**Metrics Include:**
- User counts and growth
- Book counts and processing status
- Storage usage
- AI usage and costs
        """,
    },
    {
        "name": "Admin - Ratings",
        "description": """
**Rating Moderation (Admin Only)**

Manage and moderate book ratings system-wide.

**Features:**
- View all ratings with filtering
- See flagged ratings (user-reported)
- Delete inappropriate ratings
- Rating analytics and trends

**Analytics:**
- Rating distribution (1-5 stars)
- Top-rated books (min 3 ratings)
- Most reviewed books
        """,
    },
]

# Admin API description
ADMIN_API_DESCRIPTION = """
# ILM Red Admin API

**Administrative endpoints for platform management**

---

## Overview

The Admin API provides privileged access to manage:
- **Users** - View, edit, disable accounts
- **Books** - Manage content, trigger processing
- **Chat Sessions** - View and delete conversations
- **Cache** - Redis management
- **Statistics** - System metrics

---

## Authentication

All admin endpoints require:
1. **Valid JWT Token** - `Authorization: Bearer <token>`
2. **Admin Role** - User must have `admin` or `super_admin` role

---

## Quick Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/admin/users` | GET | List all users |
| `/v1/admin/users/{id}` | GET | Get user details |
| `/v1/admin/users/{id}` | PATCH | Update user |
| `/v1/admin/users/{id}/disable` | POST | Disable user |
| `/v1/admin/books` | GET | List all books |
| `/v1/admin/books/{id}` | GET | Get book details |
| `/v1/admin/books/{id}/generate-pages` | POST | Generate pages |
| `/v1/admin/books/{id}/generate-thumbnails` | POST | Regenerate thumbnails |
| `/v1/admin/books/{id}/process-ai` | POST | Process AI embeddings |
| `/v1/admin/chats` | GET | List chat sessions |
| `/v1/admin/chats/{id}` | GET | Get chat details |
| `/v1/admin/chats/{id}` | DELETE | Delete chat session |
| `/v1/admin/stats` | GET | System statistics |
| `/v1/cache/stats` | GET | Cache statistics |
| `/v1/cache/health` | GET | Cache health check |
| `/v1/cache/invalidate` | POST | Invalidate by pattern |
| `/v1/cache/flush` | POST | Flush all cache |

---

## Documentation

- [Full Admin API Guide](/docs/ADMIN_API.md)
- [Main API Docs](/docs)

---

## Rate Limits

| Role | Requests/min |
|------|--------------|
| admin | 300 |
| super_admin | 600 |
"""

# OpenAPI tag descriptions with use cases
OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": """
**System Health & Monitoring**

Check API availability and component status.

**Use Cases:**
- Load balancer health probes
- Uptime monitoring (Pingdom, UptimeRobot)
- Deployment verification
        """,
    },
    {
        "name": "Authentication",
        "description": """
**User Authentication & API Keys**

Register, login, and manage access credentials.

**Authentication Methods:**
1. **JWT Bearer Token** - Short-lived (15 min), use for web/mobile apps
2. **API Key** - Long-lived, use for server-to-server integrations

**Quick Start:**
1. `POST /auth/register` - Create account
2. Use `access_token` from response
3. Add header: `Authorization: Bearer <token>`

**Token Refresh:**
- Access tokens expire in 15 minutes
- Use `POST /auth/refresh` with your `refresh_token` to get a new access token
- Refresh tokens expire in 7 days and rotate on each use
        """,
    },
    {
        "name": "Users",
        "description": """
**User Profiles & Preferences**

Manage user profiles and personalization settings.

**Preferences Include:**
- Theme (light/dark/system)
- Language (en, ar, etc.)
- Default AI model for chat
- Notification settings
        """,
    },
    {
        "name": "Books",
        "description": """
**Digital Book Management**

Upload, browse, and manage your digital library.

**Supported Formats:** PDF, EPUB, TXT (up to 500MB)

**Key Features:**
- Upload books with metadata (title, author, category)
- Search and filter your library
- Browse page-by-page with generated images
- Rate and favorite books
- Flag inappropriate ratings (spam, offensive, etc.)
- Control visibility (public/private/friends)

**Page Browsing:**
After upload, call `POST /books/{id}/pages/generate` to create page images.
Then browse with `GET /books/{id}/pages`.

**Rating Flags:**
Report inappropriate ratings with `POST /books/{book_id}/ratings/{rating_id}/flag`.
Reasons: spam, offensive, irrelevant, other.
        """,
    },
    {
        "name": "Chat",
        "description": """
**AI-Powered Chat**

Have intelligent conversations with multiple AI models.

**Supported AI Models:**

| Model | Provider | Best For |
|-------|----------|----------|
| qwen-turbo | Qwen | Cost-effective general use |
| gpt-4o-mini | OpenAI | Fast, intelligent responses |
| claude-3-haiku | Anthropic | Quick analysis |
| gemini-1.5-flash | Google | Multi-modal tasks |
| grok-beta | xAI | Conversational |
| deepseek-chat | DeepSeek | Technical discussions |

**Book Context (RAG):**
Link a chat session to a book, and the AI automatically reads relevant pages to answer questions with citations!

**Streaming:**
Use `POST /chats/{id}/stream` for real-time token-by-token responses via Server-Sent Events (SSE).
        """,
    },
    {
        "name": "Billing",
        "description": """
**AI Credits & Usage Tracking**

Monitor and manage your AI usage costs.

**How Credits Work:**
- Every AI operation costs credits based on tokens used
- 1 credit = $0.01 USD
- Free tier: $1.00/month (~100K tokens)
- Premium tier: $10.00/month (~1M tokens)

**Cost Transparency:**
Every chat response includes `usage` with exact token counts and cost.
        """,
    },
    {
        "name": "Cache",
        "description": """
**Cache Management (Admin Only)**

Redis cache administration for system optimization.

**Note:** Requires admin role
        """,
    },
    {
        "name": "Files",
        "description": """
**File Serving (Development Only)**

Serves files from local storage with signed URL validation.

**Note:** Development only - In production, files are served directly from Azure Blob Storage CDN.
        """,
    },
    {
        "name": "Progress",
        "description": """
**Reading Progress Tracking**

Track your reading progress with cross-device sync.

**Features:**
- Auto-save current page as you read
- Reading streak calculation (consecutive days)
- Reading time tracking per book
- Recent reads list for quick resume
- Progress statistics (books started, completed, time spent)

**Progress Updates:**
Progress is automatically updated when reading pages. You can also manually update it:

```bash
curl -X PUT /v1/books/{book_id}/progress \\
  -H "Authorization: Bearer <token>" \\
  -d '{"current_page": 42, "total_pages": 350, "reading_time_seconds": 120}'
```

**Reading Streaks:**
Streak increases for each consecutive day with reading activity. Skip a day and your streak resets!
        """,
    },
    {
        "name": "Recommendations",
        "description": """
**Personalized Book Recommendations**

Discover books tailored to your interests and reading history.

**How It Works:**
Our recommendation algorithm analyzes your reading patterns to suggest relevant books:

1. **Category-Based** (40%) - Books in categories you've been reading
2. **Top-Rated** (30%) - Highly-rated books you haven't read yet
3. **Popular** (30%) - Recently added books trending in your interests

**Each Recommendation Includes:**
- Book details (title, author, cover)
- Average rating and review count
- **Reason**: Why we're recommending it (e.g., "Based on your interest in Fiqh")

**Example:**
```bash
curl /v1/recommendations/for-you?limit=10 \\
  -H "Authorization: Bearer <token>"
```

**Note:** Recommendations require authentication and reading history for personalization.
        """,
    },
]

# Rich API description with getting started guide
API_DESCRIPTION = """
# ILM Red API

**Read, Chat, Understand** — AI-powered digital book management

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Format Books** | Upload PDF, EPUB, TXT (up to 500MB) with automatic page generation |
| **AI Chat** | Chat with 6+ AI models with transparent cost tracking |
| **Book Context (RAG)** | AI reads your books to answer questions with page citations |
| **Page Browsing** | View books page-by-page with thumbnail and medium resolution |
| **Credit System** | Pay-as-you-go AI usage with detailed transaction history |
| **Secure** | JWT tokens + API keys with role-based access control |

---

## Quick Start

### Step 1: Register
```bash
curl -X POST /v1/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email":"you@example.com","password":"SecurePass123!","username":"yourname","display_name":"Your Name"}'
```

### Step 2: Copy your `access_token` from the response

### Step 3: Use the token
Click the **Authorize** button above, paste your token, and click **Authorize**.

Now you can **Try it out** on any endpoint!

---

## Authentication

| Method | Header | Use Case |
|--------|--------|----------|
| **JWT Token** | `Authorization: Bearer <token>` | Web/mobile apps |
| **API Key** | `X-API-Key: ilm_live_...` | Server integrations |

**Token Lifecycle:**
- Access token: 15 minutes
- Refresh token: 7 days (rotates on use)

---

## Rate Limits

| Tier | Requests/min | AI Tokens/day | Monthly Cost |
|------|--------------|---------------|--------------|
| Free | 60 | 10,000 | $0 |
| Premium | 300 | 100,000 | $9.99 |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

---

## Common Workflows

### Upload and Read a Book
1. `POST /v1/books` - Upload PDF
2. `POST /v1/books/{id}/pages/generate` - Generate page images
3. `GET /v1/books/{id}/pages` - List all pages with thumbnails
4. `GET /v1/books/{id}/pages/1` - Get page 1 with full-size URL

### Chat About a Book
1. `POST /v1/chats` - Create session with `book_id`
2. `POST /v1/chats/{id}/messages` - Ask questions
3. AI responds with book context and page citations!

---

## Error Responses

All errors follow this format:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable description",
    "details": [...],
    "requestId": "req_abc123"
  }
}
```

| Status | Code | Description |
|--------|------|-------------|
| 400 | BAD_REQUEST | Invalid request format |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource doesn't exist |
| 409 | CONFLICT | Resource already exists |
| 422 | VALIDATION_ERROR | Invalid input data |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error |
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting ILM Red API", version=settings.app_version, env=settings.environment)
    await init_db()

    # Initialize Redis (optional - continues if unavailable)
    try:
        await RedisCache.get_client()
        logger.info("Redis cache initialized")
    except Exception as e:
        logger.warning("Redis unavailable, caching disabled", error=str(e))

    yield

    # Shutdown
    logger.info("Shutting down ILM Red API")

    # Close Redis
    try:
        await RedisCache.close()
    except Exception:
        pass

    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="ILM Red API",
        version=settings.app_version,
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "ILM Red Support",
            "url": "https://ilm-red.com/support",
            "email": "support@ilm-red.com",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://ilm-red.com/terms",
        },
        terms_of_service="https://ilm-red.com/terms",
        lifespan=lifespan,
    )

    # Rate limiter state and exception handler
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next) -> Response:
        """Add unique request ID to each request for tracing."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Bind request ID to structlog context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        """Log all incoming requests."""
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        response = await call_next(request)

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
        )
        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions."""
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "requestId": request.headers.get("X-Request-ID"),
                }
            },
        )

    # Include API router
    app.include_router(api_router, prefix="/v1")

    # Admin-specific OpenAPI schema
    def get_admin_openapi_schema():
        """Generate OpenAPI schema for admin endpoints only."""
        if not hasattr(app, "admin_openapi_schema"):
            # Filter routes to only include admin and cache endpoints
            admin_routes = []
            for route in app.routes:
                if hasattr(route, "path"):
                    if "/admin" in route.path or "/cache" in route.path:
                        admin_routes.append(route)

            # Create admin-specific schema
            openapi_schema = get_openapi(
                title="ILM Red Admin API",
                version=settings.app_version,
                description=ADMIN_API_DESCRIPTION,
                routes=app.routes,  # Use all routes, filter happens in docs
                tags=ADMIN_OPENAPI_TAGS,
            )

            # Filter paths to only admin endpoints
            filtered_paths = {}
            for path, methods in openapi_schema.get("paths", {}).items():
                if "/admin" in path or "/cache" in path:
                    filtered_paths[path] = methods
            openapi_schema["paths"] = filtered_paths

            app.admin_openapi_schema = openapi_schema
        return app.admin_openapi_schema

    @app.get("/admin/docs", include_in_schema=False)
    async def admin_swagger_ui_html():
        """Admin-specific Swagger UI documentation."""
        return get_swagger_ui_html(
            openapi_url="/admin/openapi.json",
            title="ILM Red Admin API - Swagger UI",
            swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
        )

    @app.get("/admin/openapi.json", include_in_schema=False)
    async def admin_openapi_json():
        """Admin-specific OpenAPI schema."""
        return get_admin_openapi_schema()

    return app


app = create_app()
