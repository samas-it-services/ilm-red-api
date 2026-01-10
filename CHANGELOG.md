# **Changelog**

All notable changes to this project will be documented in this file.

## Format
- **Reverse chronological order** (newest at top)
- **Header format:** `YYYY-MM-DD | <category>: <title>`
- **Categories:**
  - 🚀 **feat**
  - 🐛 **fix**
  - 📘 **docs**
  - 🧹 **chore**
- **Sections included in every entry:**
  - 📄 **Summary**
  - 📁 **Files Changed**
  - 🧠 **Rationale**
  - 🔄 **Behavior / Compatibility Implications**
  - 🧪 **Testing Recommendations**
  - 📌 **Follow‑ups**

---

## 2026-01-10 | 🚀 feat: Production Deployment v1.1.0

### 📄 **Summary**
Successfully deployed API v1.1.0 to Azure with Admin Panel, Global Search, and Extended User Profile features. All database migrations applied automatically via entrypoint script.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| All v1.1.0 features | Deployed | Admin, Search, extra_data deployed to production |

### 🧠 **Rationale**
Production release for mobile app v1.1.0 compatibility.

### 🔄 **Deployment Details**
| Resource | Value |
|----------|-------|
| API URL | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io |
| Swagger | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/docs |
| Health | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/health |
| Region | West US 2 |
| Replicas | 1-10 (auto-scaling) |

### 🧪 **Testing Recommendations**
- [ ] Verify health endpoint responds
- [ ] Test admin endpoints with admin user
- [ ] Test search functionality
- [ ] Verify extra_data updates on profile

### 📌 **Follow‑ups**
- [ ] Monitor Azure costs and optimize if needed
- [ ] Set up alerting for health check failures
- [ ] Configure CDN for static assets

---

## 2026-01-10 | 🚀 feat: Admin Panel, Global Search, Extended User Profile

### 📄 **Summary**
Major feature release implementing Admin Panel with user/book/chat management, Global Search API with suggestions, and extended user profile with future-proof `extra_data` JSONB column. This enables mobile app admin functionality and search capabilities.

### 📁 **Files Changed**

#### Database Migration
| File | Change Type | Description |
|------|-------------|-------------|
| `app/db/migrations/versions/20260110_0007_user_extra_data.py` | Added | Add `extra_data` JSONB column to users table |

#### Models & Schemas
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/user.py` | Modified | Added `extra_data` column and helper properties |
| `app/schemas/user.py` | Modified | Added `UserExtraData` schema, updated `UserResponse` and `UserUpdate` |
| `app/schemas/admin.py` | Added | Admin schemas for users, books, chats, stats |

#### API Endpoints
| File | Change Type | Description |
|------|-------------|-------------|
| `app/api/v1/admin.py` | Added | Admin endpoints for users, books, chats, stats |
| `app/api/v1/search.py` | Added | Global search and suggestions endpoints |
| `app/api/v1/users.py` | Modified | Updated PATCH /users/me to handle `extra_data` |
| `app/api/v1/deps.py` | Modified | Added `AdminUser` type alias |
| `app/api/v1/router.py` | Modified | Included admin and search routers |

### 🧠 **Rationale**
- **extra_data JSONB**: Future-proof approach for profile fields without requiring migrations for each new field
- **Admin Panel**: Mobile app needs to manage users, trigger book processing, view chats
- **Global Search**: Users need to find books across title, author, description, category
- **Swagger/OpenAPI**: All new endpoints auto-documented via FastAPI/Pydantic

### 🔄 **Behavior / Compatibility Implications**
- **Migration Required**: Run `alembic upgrade head` to add `extra_data` column
- **Backward Compatible**: Existing users will have `extra_data = {}`
- **Admin Access**: Requires `admin` or `super_admin` role for `/admin/*` endpoints
- **Search Access**: Public books searchable without auth; private books require auth

### 🧪 **Testing Recommendations**
- [ ] Run migration and verify `extra_data` column exists
- [ ] Test PATCH /users/me with `extra_data` field
- [ ] Test admin endpoints with admin vs regular user
- [ ] Test search with various query combinations
- [ ] Verify Swagger docs at `/docs`

### 📌 **Follow‑ups**
- [ ] Implement actual page generation job queue
- [ ] Add Redis caching to search for performance
- [ ] Add search analytics/logging

---

## 2026-01-09 | 🚀 feat: Chat, Billing, AI Safety, Redis Cache, and Local Dev Tools

### 📄 **Summary**
Major feature release implementing Chat sessions with SSE streaming, Billing system with credits/transactions, AI Safety with content moderation, Redis caching infrastructure, and local development data sync tools. This completes Phases 1-3 of the implementation plan.

### 📁 **Files Changed**

#### Phase 1: Chat System
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/chat.py` | Added | ChatSession, ChatMessage, MessageFeedback SQLAlchemy models |
| `app/schemas/chat.py` | Added | Request/response Pydantic schemas for chat |
| `app/repositories/chat_repo.py` | Added | Chat data access layer |
| `app/services/chat_service.py` | Added | Chat business logic with SSE streaming |
| `app/api/v1/chat.py` | Added | Chat API endpoints (sessions, messages, stream) |
| `app/db/migrations/versions/20260109_0003_chat_sessions.py` | Added | Chat tables migration |

#### Phase 2: Billing System
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/billing.py` | Added | UserCredits, BillingTransaction, UsageLimit models |
| `app/schemas/billing.py` | Added | Billing request/response schemas |
| `app/repositories/billing_repo.py` | Added | Billing data access layer |
| `app/services/billing_service.py` | Added | Credits, limits, transaction management |
| `app/api/v1/billing.py` | Added | Billing API endpoints (balance, transactions, limits) |
| `app/db/migrations/versions/20260109_0004_billing.py` | Added | Billing tables migration |

#### Phase 3: AI Safety & Smart Router
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/safety.py` | Added | SafetyFlag model for content moderation |
| `app/services/safety_service.py` | Added | OpenAI Moderation API integration |
| `app/ai/task_classifier.py` | Added | Task type classification for model routing |
| `app/services/ai_model_router.py` | Modified | Enhanced with fallback chains and task-based routing |
| `app/db/migrations/versions/20260109_0005_safety.py` | Added | Safety tables migration |

#### Redis Caching Infrastructure
| File | Change Type | Description |
|------|-------------|-------------|
| `app/cache/__init__.py` | Added | Package exports |
| `app/cache/redis_client.py` | Added | RedisCache singleton, CacheService |
| `app/cache/decorators.py` | Added | `@cached` decorator, CacheInvalidator |
| `app/api/v1/cache.py` | Added | Admin cache endpoints (stats, invalidate, flush) |

#### Local Development Tools
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/dev-with-data.sh` | Added | One-command local dev setup with seed data |
| `scripts/export_test_data.py` | Added | Export public data from production API |
| `scripts/import_test_data.py` | Added | Import seed data into local database |
| `seeds/books.json` | Added | Sample book seed data |
| `seeds/categories.json` | Added | Default category seed data |

#### Integration Updates
| File | Change Type | Description |
|------|-------------|-------------|
| `app/api/v1/router.py` | Modified | Added chat, billing, cache routers |
| `app/main.py` | Modified | Added Redis startup/shutdown lifecycle hooks |
| `app/models/__init__.py` | Modified | Export new models (Chat, Billing, Safety) |
| `app/schemas/__init__.py` | Modified | Export new schemas |
| `app/services/__init__.py` | Modified | Export new services |
| `app/repositories/__init__.py` | Modified | Export new repositories |

### 🧠 **Rationale**

| Feature | Purpose |
|---------|---------|
| Chat System | Enable AI conversations with book context, SSE streaming for real-time responses |
| Billing System | Track AI usage, enforce limits, support future monetization |
| AI Safety | Content moderation before AI processing, compliance with safety policies |
| Task Classifier | Route queries to optimal models based on task type (summary, reasoning, creative) |
| Redis Cache | Reduce database load, improve response times for hot data |
| Dev Tools | Faster local development with realistic seed data |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| New API endpoints | Non-breaking - adds `/v1/chat/*`, `/v1/billing/*`, `/v1/cache/*` |
| Redis dependency | Optional - API works without Redis (cache operations return gracefully) |
| Database migrations | 3 new migrations must be applied |
| Safety checks | AI requests now pass through moderation (can be bypassed with config) |

### 🧪 **Testing Recommendations**

```bash
# Run migrations
poetry run alembic upgrade head

# Test chat endpoints
curl -X POST http://localhost:8000/v1/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Session"}'

# Test billing balance
curl http://localhost:8000/v1/billing/balance \
  -H "Authorization: Bearer $TOKEN"

# Test cache stats (admin only)
curl http://localhost:8000/v1/cache/stats \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Local dev with seed data
./scripts/dev-with-data.sh
```

### 📌 **Follow‑ups**
- [ ] Add unit tests for chat service (70% coverage target)
- [ ] Add integration tests for billing flow
- [ ] Implement webhook notifications for billing events
- [ ] Add cache warming on startup for hot data

---

## 2026-01-09 | 📘 docs: Add deployment documentation and cold start optimization

### 📄 **Summary**
Added comprehensive deployment documentation to README.md and rewrote TDD.md Section 8 with accurate Python/FastAPI Azure deployment details. Also implemented configurable container scaling to eliminate cold starts (~$23/mo additional cost).

### 📁 **Files Changed**

#### Documentation
| File | Change Type | Description |
|------|-------------|-------------|
| `README.md` | Modified | Added "Deployment" section with Azure CLI commands, resource costs, and configuration |
| `docs/TDD.md` | Modified | Rewrote Section 8 "Deployment & Operations" with accurate Python/Azure details |

#### Infrastructure (Cold Start Optimization)
| File | Change Type | Description |
|------|-------------|-------------|
| `infra/parameters.json` | Modified | Added `containerMinReplicas: 1` and `containerMaxReplicas: 10` |
| `infra/main.bicep` | Modified | Added scaling parameters with `@minValue`/`@maxValue` validation |
| `infra/modules/container-apps.bicep` | Modified | Made `minReplicas`/`maxReplicas` configurable via parameters |

### 🧠 **Rationale**

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Missing deployment docs | README only had local dev setup | Added Azure deployment section |
| Outdated TDD Section 8 | Had Node.js Dockerfile, generic YAML | Rewrote with actual Python/Bicep details |
| 20-30s cold starts | `minReplicas: 0` caused scale-to-zero | Made scaling configurable, set `minReplicas: 1` |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| `minReplicas: 1` | Container always running, no cold starts, +$23/mo |
| Configurable scaling | Can adjust via `parameters.json` without code changes |
| Documentation | Developers can now deploy to Azure using README |

### 🧪 **Testing Recommendations**

```bash
# Verify deployment docs
cat README.md | grep -A 50 "## Deployment"

# Check container is always-on
az containerapp show --name ilmred-prod-api --resource-group ilmred-prod-rg \
  --query "properties.template.scale.minReplicas"
# Expected: 1

# Test health endpoint (should respond immediately, no cold start)
time curl -s https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/v1/health
```

### 📌 **Follow‑ups**
- [ ] Add GitHub Actions CI/CD workflow
- [ ] Document environment promotion (dev → staging → prod)
- [ ] Add Terraform alternative to Bicep

---

## 2026-01-09 | 🚀 feat: Azure deployment fixes, auto-migrations, and API test suite

### 📄 **Summary**
Fixed Azure Container Apps deployment issues causing HTTP 500 errors on user registration. Added Docker entrypoint script to automatically run database migrations on container startup. Created comprehensive API test suite with curl-based scripts for all endpoints. Fixed infrastructure configuration for PostgreSQL SSL, health probes, and SQLAlchemy connection pooling.

### 📁 **Files Changed**

#### Docker & Migrations
| File | Change Type | Description |
|------|-------------|-------------|
| `docker/entrypoint.sh` | Added | Entrypoint script that runs `alembic upgrade head` before starting uvicorn |
| `docker/Dockerfile` | Modified | Use entrypoint script instead of direct CMD |
| `scripts/deploy-azure.sh` | Modified | Renamed misleading `run_migrations()` to `verify_app_health()` |

#### Infrastructure (Bicep)
| File | Change Type | Description |
|------|-------------|-------------|
| `infra/main.bicep` | Modified | Fixed parameter passing for PostgreSQL SSL |
| `infra/modules/postgresql.bicep` | Modified | Changed DATABASE_URL to use `ssl=require` instead of `sslmode=require` |
| `infra/modules/container-apps.bicep` | Modified | Changed health probe paths from `/health` to `/v1/health` |

#### Database Connection
| File | Change Type | Description |
|------|-------------|-------------|
| `app/db/session.py` | Modified | Use `NullPool` for serverless environments (Azure Container Apps) |

#### API Test Suite
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/api-tests/README.md` | Added | Documentation with Azure details and troubleshooting guide |
| `scripts/api-tests/config.sh` | Added | Shared configuration and helper functions |
| `scripts/api-tests/run-all-tests.sh` | Added | Master test runner script |
| `scripts/api-tests/.gitignore` | Added | Ignore test data directory |
| `scripts/api-tests/01-health/*` | Added | Health check tests |
| `scripts/api-tests/02-auth/*` | Added | Auth tests (register, login, refresh, logout) |
| `scripts/api-tests/03-api-keys/*` | Added | API key management tests |
| `scripts/api-tests/04-users/*` | Added | User profile tests |
| `scripts/api-tests/05-books/*` | Added | Book CRUD tests |
| `scripts/api-tests/06-ratings/*` | Added | Rating tests |
| `scripts/api-tests/07-favorites/*` | Added | Favorites tests |

### 🧠 **Rationale**

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| HTTP 500 on registration | Database tables didn't exist - migrations never ran | Created `docker/entrypoint.sh` to run migrations on startup |
| Misleading function name | `run_migrations()` only did health checks | Renamed to `verify_app_health()` |
| PostgreSQL SSL error | asyncpg uses `ssl=` not `sslmode=` | Changed connection string format |
| Health probe failures | Probes hit `/health` but API uses `/v1/health` | Updated Bicep templates |
| Connection pool errors | SQLAlchemy default pool incompatible with serverless | Use `NullPool` in production |
| No API testing tools | Manual curl commands scattered | Created organized test suite |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| Entrypoint script | Migrations run automatically on every deployment |
| NullPool | Each request gets fresh connection (slightly higher latency, more reliable) |
| Health probe path | Azure health checks now hit correct endpoint |
| Test suite | Developers can quickly validate API functionality |

### 🧪 **Testing Recommendations**

```bash
# Test health endpoint
./scripts/api-tests/01-health/test-health.sh

# Test user registration
./scripts/api-tests/02-auth/test-register.sh user@example.com Password123! username "Display Name"

# Run all tests
./scripts/api-tests/run-all-tests.sh

# View container logs
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --tail 100
```

### 📌 **Follow‑ups**
- [ ] Add CI/CD pipeline to run test suite on PRs
- [ ] Add load testing scripts
- [ ] Implement migration rollback strategy
- [ ] Add Prometheus metrics endpoint

---

## 2026-01-08 | 🐛 fix: Fix dev.sh startup issues (Python 3.14, PostgreSQL, dependencies)

### 📄 **Summary**
Fixed multiple issues preventing `scripts/dev.sh` from running successfully on macOS with Python 3.14 and Homebrew PostgreSQL. The API now starts correctly with proper Python version detection, dependency management, and database connectivity.

### 📁 **Files Changed**

| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/dev.sh` | Modified | Added Python 3.12/3.13 version detection, auto-configure Poetry to use correct Python |
| `pyproject.toml` | Modified | Set `python = ">=3.12,<3.14"`, added `package-mode = false`, added `email-validator` |
| `app/db/migrations/env.py` | Modified | Added sys.path.insert for project root imports |
| `.env` | Modified | Changed CORS_ORIGINS to JSON array format |

### 🧠 **Rationale**

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Python 3.14 incompatibility | tiktoken, asyncpg don't have pre-built wheels for Python 3.14 (alpha) | Added version check, prefer python3.12/3.13 |
| Poetry package-mode error | Project is an API, not a library | Added `package-mode = false` |
| Alembic module not found | Project root not in Python path | Added sys.path.insert in env.py |
| CORS_ORIGINS parsing error | Pydantic expects JSON array, not CSV | Changed to JSON array format |
| PostgreSQL "role postgres" error | Homebrew PostgreSQL 17 conflicts on port 5432 | Documented: stop Homebrew pg17 |
| Missing email-validator | Pydantic EmailStr requires it | Added dependency |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| Python version check | dev.sh now rejects Python 3.14+, prefers python3.12 |
| package-mode = false | Poetry no longer tries to install project as package |
| sys.path fix | Alembic migrations work without PYTHONPATH |
| email-validator | Required for user email validation |

### 🧪 **Testing Recommendations**

```bash
# Stop Homebrew PostgreSQL if running
brew services stop postgresql@17

# Run dev script
./scripts/dev.sh

# Verify API health
curl http://localhost:8000/v1/health
# Expected: {"status":"healthy",...}
```

### 📌 **Follow‑ups**
- [ ] Add Windows PowerShell equivalent for Python version detection
- [ ] Consider adding pyenv/asdf support to dev.sh
- [ ] Update .env.example with CORS_ORIGINS JSON format

---

## 2026-01-07 | 🚀 feat: Phase 2 Books CRUD, Multi-Vendor AI, and Local Dev Setup

### 📄 **Summary**
Major release implementing Phase 2 (Books CRUD + File Storage), Phase 2.5 (Multi-Vendor AI Model Support), local development tooling, and comprehensive documentation updates. This release adds full book management capabilities, support for 6 AI vendors with intelligent model routing, and streamlined developer experience.

### 📁 **Files Changed**

#### Books CRUD + File Storage (Phase 2)
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/book.py` | Added | Book, Rating, Favorite SQLAlchemy models |
| `app/models/__init__.py` | Modified | Export new book models |
| `app/db/migrations/versions/20250107_0002_books.py` | Added | Books table migration with indexes |
| `app/schemas/book.py` | Added | Book request/response Pydantic schemas |
| `app/schemas/rating.py` | Added | Rating schemas |
| `app/schemas/__init__.py` | Modified | Export new schemas |
| `app/storage/base.py` | Added | Abstract StorageProvider interface |
| `app/storage/local.py` | Added | Local filesystem storage implementation |
| `app/storage/azure_blob.py` | Added | Azure Blob Storage implementation |
| `app/storage/__init__.py` | Modified | Storage provider factory |
| `app/repositories/book_repo.py` | Added | Book data access layer |
| `app/repositories/__init__.py` | Modified | Export book repository |
| `app/services/book_service.py` | Added | Book business logic |
| `app/services/__init__.py` | Modified | Export book service |
| `app/api/v1/books.py` | Modified | Complete books CRUD endpoints |
| `tests/integration/test_books.py` | Added | Book integration tests |

#### Multi-Vendor AI Model Support (Phase 2.5)
| File | Change Type | Description |
|------|-------------|-------------|
| `app/ai/base.py` | Added | AIProvider abstract base class, ModelConfig, ChatMessage, ChatResponse |
| `app/ai/__init__.py` | Modified | Model registry (17 models) and provider factory |
| `app/ai/providers/openai_provider.py` | Added | OpenAI GPT implementation |
| `app/ai/providers/qwen_provider.py` | Added | Qwen/Alibaba DashScope implementation |
| `app/ai/providers/anthropic_provider.py` | Added | Anthropic Claude implementation |
| `app/ai/providers/google_provider.py` | Added | Google Gemini implementation |
| `app/ai/providers/xai_provider.py` | Added | xAI Grok implementation |
| `app/ai/providers/deepseek_provider.py` | Added | DeepSeek implementation |
| `app/services/ai_model_router.py` | Added | Model routing based on book visibility |
| `app/config.py` | Modified | Added AI provider keys and model defaults |
| `app/schemas/user.py` | Modified | Added AIPreferences for user model selection |

#### Local Development Setup
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/dev.sh` | Added | Comprehensive local dev setup script |
| `.env.example` | Modified | Added all AI provider keys and model defaults |
| `README.md` | Modified | Fixed tech stack (Python/FastAPI), added Quick Start |

#### Documentation & Project Config
| File | Change Type | Description |
|------|-------------|-------------|
| `.gitignore` | Added | Python gitignore (pycache, venv, .env, etc.) |
| `CLAUDE.md` | Added | Project guidance for Claude Code |
| `CHANGELOG.md` | Added | This changelog file |
| `docs/PRICING.md` | Modified | Multi-vendor AI pricing tables |
| `docs/PRD.md` | Modified | Updated FR-AI-003 with multi-vendor requirements |
| `openapi/api-v1.yaml` | Modified | Added vendor field, expanded model enums |
| `pyproject.toml` | Modified | Added google-generativeai dependency |

### 🧠 **Rationale**

**Books CRUD:**
- Core feature required for all book-related functionality
- Storage abstraction enables local dev and cloud deployment
- Separation of concerns: models → repositories → services → API

**Multi-Vendor AI:**
- **Cost optimization**: Qwen ($0.40/1M) vs GPT-4o-mini ($0.75/1M) for public content
- **User choice**: Premium users can select preferred model
- **Vendor diversity**: Reduces single-provider dependency
- **Abstraction**: Easy to add new providers

**Local Dev Setup:**
- README was outdated (showed Node.js, actual stack is Python/FastAPI)
- Developers needed simple one-command setup
- `scripts/dev.sh` handles prerequisites, Docker, migrations, server startup

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| New book endpoints | Non-breaking - new functionality |
| AI model routing | Public books now use Qwen by default (cost savings) |
| User preferences | New `ai` field in user preferences (backward compatible) |
| Storage abstraction | Supports both local and Azure Blob |
| API spec | New `vendor` field in AI model responses |

### 🧪 **Testing Recommendations**

```bash
# 1. Test local dev setup
./scripts/dev.sh

# 2. Verify health
curl http://localhost:8000/health

# 3. Test books CRUD
TOKEN="<jwt-token>"

# Upload book
curl -X POST http://localhost:8000/v1/books \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.pdf" \
  -F "title=Test Book" \
  -F "category=technology"

# List books
curl http://localhost:8000/v1/books

# 4. Test AI model listing
curl http://localhost:8000/v1/ai/models

# 5. Run automated tests
./scripts/dev.sh test
```

### 📌 **Follow‑ups**
- [ ] Add integration tests for each AI provider
- [ ] Implement AI fallback when primary provider unavailable
- [ ] Add book processing worker (PDF text extraction, chunking)
- [ ] Implement semantic search with pgvector embeddings
- [ ] Add Windows PowerShell equivalent of dev.sh
- [ ] Add CI/CD workflow to validate dev script
