"""FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.router import api_router
from app.db.session import init_db, close_db
from app.cache.redis_client import RedisCache

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
- Control visibility (public/private/friends)

**Page Browsing:**
After upload, call `POST /books/{id}/pages/generate` to create page images.
Then browse with `GET /books/{id}/pages`.
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
]

# Rich API description with getting started guide
API_DESCRIPTION = """
# ILM Red API

**Cloud-native backend for AI-powered digital book management**

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

    return app


app = create_app()
