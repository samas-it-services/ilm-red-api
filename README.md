# ILM Red API

[![CI/CD](https://github.com/samas-it-services/ilm-red-api/actions/workflows/deploy.yml/badge.svg)](https://github.com/samas-it-services/ilm-red-api/actions/workflows/deploy.yml)
[![codecov](https://codecov.io/gh/samas-it-services/ilm-red-api/graph/badge.svg)](https://codecov.io/gh/samas-it-services/ilm-red-api)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Environment](https://img.shields.io/badge/Env-Production-green.svg)](https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io)

**Read, Chat, Understand** — AI-powered digital book management API.

## Overview

ILM Red API is the backend service layer for the ILM Red ecosystem. It provides RESTful APIs for:

- **Books** - Multi-format upload (PDF, EPUB, TXT), metadata, thumbnails
- **Users** - Profiles, preferences, authentication
- **Search** - Full-text, semantic, and autocomplete
- **AI Chat** - Multi-model AI conversations with book context
- **Book Clubs** - Social features, discussions, invites
- **Progress** - Cross-device reading progress sync
- **Analytics** - Usage metrics and reporting
- **Admin** - Moderation, audit logs, user management

## Architecture

Designed for scale: **500,000+ users**, **10M+ books**, **100K+ concurrent connections**.

```
                    ┌─────────────────┐
                    │   API Gateway   │
                    │ (Azure API Mgmt)│
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │   Auth    │      │   Core    │      │    AI     │
   │  Service  │      │  Services │      │  Service  │
   └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │Cosmos DB │  │ AI Search│  │  Redis   │
        └──────────┘  └──────────┘  └──────────┘
                             │
                             ▼
                   ┌─────────────────┐
                   │ Microsoft Fabric│
                   │   (Analytics)   │
                   └─────────────────┘
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Validation | Pydantic 2.x |
| Database | PostgreSQL + pgvector |
| Cache | Redis |
| Search | pgvector (semantic) + pg_trgm (full-text) |
| Storage | Local / Azure Blob |
| AI | Multi-vendor (OpenAI, Qwen, Claude, Gemini, Grok, DeepSeek) |
| Background | ARQ (Redis-based) |
| Auth | JWT + API Keys (Argon2) |

## Live API Documentation

**Production API:** https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io

| Documentation | URL |
|---------------|-----|
| **Swagger UI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/docs |
| **Admin Swagger UI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/admin/docs |
| **ReDoc** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/redoc |
| **OpenAPI JSON** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/openapi.json |
| **Admin OpenAPI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/admin/openapi.json |

## Current Development Status

| Field | Value |
|-------|-------|
| **Current Version** | v1.2.1 |
| **Last Deployed** | 2026-01-11 |
| **Status** | Production |

### Completed Features (v1.2.0)

| Feature | Status | Description |
|---------|--------|-------------|
| Rate Limiting | Complete | 10 req/min on AI chat endpoints (slowapi) |
| Path Traversal Fix | Complete | Secure file storage path validation |
| Admin Panel | Complete | User/book/chat management for admins |
| Global Search | Complete | Redis-backed search with autocomplete |
| Extended Profile | Complete | Future-proof extra_data JSON column |
| Page Browsing | Complete | PDF page images with signed URLs |
| AI Chat | Complete | Multi-turn conversations with book context |
| Cache Management | Complete | Redis stats, invalidation, flush |

### In Progress

| Feature | Status | Description |
|---------|--------|-------------|
| RAG Integration | In Progress | Book context in AI chat responses |
| Offline Support | Planned | Page caching for offline reading |

See [Implementation Plan](./docs/IMPLEMENTATION_PLAN.md) for detailed progress.

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](./docs/PRD.md) | Product Requirements Document |
| [TDD](./docs/TDD.md) | Technical Design Document |
| [Admin API Guide](./docs/ADMIN_API.md) | Comprehensive Admin API documentation |
| [Architecture](./docs/ARCHITECTURE.md) | System Architecture |
| [OpenAPI](./openapi/api-v1.yaml) | API Specification |
| [Implementation Plan](./docs/IMPLEMENTATION_PLAN.md) | Current development phases |

## Key Design Principles

1. **Vendor Agnostic** - No lock-in to Supabase, Localbase, etc.
2. **API-First** - 100% functionality via documented APIs
3. **Horizontal Scale** - Stateless services, auto-scaling
4. **Event-Driven** - Async processing for non-critical ops
5. **Multi-Tenant Ready** - B2B SaaS architecture
6. **Zero-Trust** - JWT auth, API keys, rate limiting

## Scale Targets

| Metric | Target |
|--------|--------|
| Users | 500,000+ |
| Books | 10,000,000+ |
| Concurrent | 100,000+ |
| API Latency (p99) | < 500ms |
| Search Latency | < 200ms |
| Availability | 99.9% |

## API Authentication

```bash
# Bearer Token (JWT)
curl -H "Authorization: Bearer eyJhbG..." https://api.ilm-red.com/v1/books

# API Key
curl -H "X-API-Key: ilm_live_abc123..." https://api.ilm-red.com/v1/books
```

## Rate Limits

| Tier | Requests/min | AI Tokens/day |
|------|--------------|---------------|
| Free | 60 | 10,000 |
| Premium | 300 | 100,000 |
| Enterprise | 1,000 | Unlimited |

**AI Chat Rate Limits:** 10 requests/minute per IP (enforced via slowapi)

## Quick Start

### Prerequisites

- **Docker** & Docker Compose
- **Python 3.12+**
- **Poetry** - Install with: `curl -sSL https://install.python-poetry.org | python3 -`

### Option 1: Using Dev Script (Recommended)

```bash
# Clone repository
git clone https://github.com/ilm-red/ilm-red-api.git
cd ilm-red-api

# Copy environment file and add your API keys
cp .env.example .env

# Run the dev script (handles everything)
./scripts/dev.sh
```

The dev script will:
1. Check prerequisites (Docker, Poetry)
2. Install Python dependencies
3. Start PostgreSQL + Redis containers
4. Run database migrations
5. Start the API server with hot-reload

### Option 2: Manual Setup

```bash
# Install Python dependencies
poetry install

# Start database and Redis
docker compose -f docker/docker-compose.yml up -d db redis

# Wait for DB to be ready, then run migrations
poetry run alembic upgrade head

# Start the API server with hot-reload
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# Open API docs in browser
open http://localhost:8000/docs
```

### Other Commands

```bash
./scripts/dev.sh setup    # Setup only (no API start)
./scripts/dev.sh start    # Start API only
./scripts/dev.sh stop     # Stop Docker services
./scripts/dev.sh test     # Run tests
./scripts/dev.sh reset    # Reset database (destructive!)
./scripts/dev.sh logs     # Show Docker logs
```

## Deployment

### Prerequisites

- **Azure CLI** - Install with: `brew install azure-cli`
- **Docker**
- **Azure subscription** with Owner/Contributor access

### Deploy to Azure

```bash
# Login to Azure
az login

# Configure parameters (API keys, secrets)
cp infra/parameters.example.json infra/parameters.json
# Edit infra/parameters.json with your API keys

# Deploy everything (infrastructure + app)
./scripts/deploy-azure.sh prod

# Or deploy only infrastructure
./scripts/deploy-azure.sh prod --infra-only

# Or deploy only app (after infra exists)
./scripts/deploy-azure.sh prod --app-only
```

### Azure Resources Created

| Resource | Purpose | Estimated Cost |
|----------|---------|----------------|
| Container Registry | Docker images | ~$5/mo |
| Container Apps | API hosting | ~$23/mo (always-on) |
| PostgreSQL Flexible | Database | ~$15/mo |
| Redis Cache | Caching | ~$16/mo |
| Storage Account | File storage | ~$1/mo |
| Key Vault | Secrets | ~$0.03/mo |

**Total**: ~$60/mo (always-on) or ~$35/mo (scale-to-zero)

### Configuration

Edit `infra/parameters.json` to configure:

| Parameter | Description |
|-----------|-------------|
| `containerMinReplicas` | `0` = scale-to-zero (cold starts), `1` = always-on |
| `containerMaxReplicas` | Auto-scale limit (default: 10) |
| `jwtSecret` | Generate with: `openssl rand -base64 32` |
| `openaiApiKey` | Optional AI provider API key |

### Useful Commands

```bash
# View logs
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --follow

# Restart app
az containerapp revision restart --name ilmred-prod-api --resource-group ilmred-prod-rg

# Scale replicas
az containerapp update --name ilmred-prod-api --resource-group ilmred-prod-rg --min-replicas 2

# Delete all resources
az group delete --name ilmred-prod-rg --yes
```

## Project Structure

```
ilm-red-api/
├── app/
│   ├── main.py            # FastAPI entry point
│   ├── config.py          # Pydantic settings
│   ├── api/v1/            # API route handlers
│   │   ├── auth.py, books.py, users.py, search.py, ai.py
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic request/response schemas
│   ├── services/          # Business logic
│   ├── repositories/      # Data access layer
│   ├── db/                # Database setup + Alembic migrations
│   ├── ai/                # AI provider abstraction
│   │   └── providers/     # OpenAI, Qwen, Claude, etc.
│   └── storage/           # File storage abstraction
├── docker/
│   ├── Dockerfile.dev
│   └── docker-compose.yml
├── scripts/
│   └── dev.sh             # Local development script
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
│   ├── PRD.md, TDD.md, ARCHITECTURE.md, PRICING.md
├── openapi/
│   └── api-v1.yaml        # OpenAPI 3.1 specification
├── pyproject.toml         # Poetry dependencies
└── alembic.ini            # Database migrations config
```

## Environment Variables

```bash
# Application
ENVIRONMENT=development
DEBUG=true

# Database (PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ilmred

# Redis
REDIS_URL=redis://localhost:6379

# Authentication
JWT_SECRET=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Storage
STORAGE_TYPE=local
LOCAL_STORAGE_PATH=./uploads

# AI Providers (Multi-vendor - configure at least one)
OPENAI_API_KEY=sk-your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
QWEN_API_KEY=your-qwen-api-key          # Default for public books
GOOGLE_API_KEY=your-google-api-key
XAI_API_KEY=your-xai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# AI Model Defaults
AI_DEFAULT_MODEL_PUBLIC=qwen-turbo      # Cost-effective for public content
AI_DEFAULT_MODEL_PRIVATE=gpt-4o-mini    # Higher quality for private books
```

See `.env.example` for the complete list of configuration options.

## API Endpoints Summary

### Authentication
- `POST /v1/auth/login` - Login
- `POST /v1/auth/oauth/{provider}` - OAuth flow
- `POST /v1/auth/refresh` - Refresh tokens
- `POST /v1/auth/api-keys` - Create API key

### Books
- `GET /v1/books` - List books
- `POST /v1/books` - Upload book
- `GET /v1/books/{id}` - Get book
- `PATCH /v1/books/{id}` - Update book
- `DELETE /v1/books/{id}` - Delete book

### Page Images
- `GET /v1/books/{id}/pages` - List all pages with signed URLs
- `GET /v1/books/{id}/pages/{pageNumber}` - Get specific page URLs
- `POST /v1/books/{id}/pages/generate` - Trigger page generation
- `GET /v1/books/{id}/pages/status` - Get generation progress

### Covers
- `GET /v1/books/{id}/cover` - Get cover URL
- `PUT /v1/books/{id}/cover` - Upload custom cover
- `DELETE /v1/books/{id}/cover` - Remove custom cover (revert to auto)

### Search
- `GET /v1/search` - Global search
- `GET /v1/search/suggestions` - Autocomplete suggestions

### AI Chat
- `POST /v1/chat/{book_id}` - Send message (SSE streaming)
- `GET /v1/chat/{book_id}/history` - Get chat history

### Billing
- `GET /v1/billing/balance` - Get credit balance
- `GET /v1/billing/transactions` - Transaction history
- `GET /v1/billing/limits` - Usage limits

### Admin (Requires admin role)
- `GET /v1/admin/users` - List/search users
- `GET /v1/admin/users/{id}` - Get user detail
- `PATCH /v1/admin/users/{id}` - Update user
- `POST /v1/admin/users/{id}/disable` - Disable user
- `GET /v1/admin/books` - List all books
- `POST /v1/admin/books/{id}/generate-pages` - Generate pages
- `POST /v1/admin/books/{id}/generate-thumbnails` - Regenerate thumbnails
- `POST /v1/admin/books/{id}/process-ai` - Process AI embeddings
- `GET /v1/admin/chats` - List chat sessions
- `DELETE /v1/admin/chats/{id}` - Delete chat session
- `GET /v1/admin/stats` - System statistics

### Cache (Requires admin role)
- `GET /v1/cache/stats` - Cache statistics
- `GET /v1/cache/health` - Redis health check
- `POST /v1/cache/invalidate` - Invalidate by pattern
- `POST /v1/cache/flush` - Flush all (requires confirm)

### Clubs
- `GET /v1/clubs` - Discover clubs
- `POST /v1/clubs` - Create club
- `POST /v1/clubs/{id}/members` - Join club

### Progress
- `GET /v1/progress/{bookId}` - Get progress
- `PUT /v1/progress/{bookId}` - Update progress

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

## License

Apache 2.0 - See [LICENSE](./LICENSE)

## Related Projects

- [ilm-red-unbound](../ilm-red-unbound) - React frontend application
- [smart-search](../smart-search) - Universal search library
