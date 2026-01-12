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

## 2026-01-12 | 🚀 feat: Personalized book recommendations (Phase 5 Part 1)

### 📄 **Summary**
Add personalized book recommendation system that suggests books based on user's reading history, preferences, and top-rated content. Recommendations appear on home page and help users discover relevant books.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `app/schemas/recommendation.py` | Added | Recommendation response schema with reasoning |
| `app/services/recommendation_service.py` | Added | Recommendation algorithm and business logic |
| `app/api/v1/recommendations.py` | Added | Recommendations API endpoint |
| `app/api/v1/router.py` | Modified | Register recommendations router |
| `app/db/migrations/versions/20260112_1148_*.py` | Added | Book extras table migration (for future features) |

### 🧠 **Rationale**
Users need personalized content discovery to find relevant books in a large library. Generic "all books" lists don't scale well. Recommendations based on reading history and preferences improve engagement and help users find books they'll enjoy.

Algorithm:
- 40% weight: Books in categories user has been reading
- 30% weight: Top-rated books user hasn't read (min 3 ratings)
- 30% weight: Recently added popular books

### 🔄 **Behavior / Compatibility Implications**
- New endpoint: GET /v1/recommendations/for-you
- Requires authentication (recommendations are personalized)
- Returns up to 50 books (default 10)
- Each recommendation includes reason (e.g., "Based on your interest in Fiqh")
- Excludes books user has already read

### 🧪 **Testing Recommendations**
```bash
# Test recommendations API
curl http://localhost:8000/v1/recommendations/for-you?limit=10 \
  -H "Authorization: Bearer <token>"

# Expected response:
# [
#   {
#     "book_id": "...",
#     "title": "Book Title",
#     "category": "fiqh",
#     "reason": "Based on your interest in fiqh",
#     "average_rating": 4.5,
#     ...
#   }
# ]
```

### 📌 **Follow‑ups**
- Add recommendations section to mobile home page
- Implement more sophisticated algorithm (collaborative filtering)
- Track recommendation click-through rates
- Complete Phase 5 Part 2: Book extras (flashcards, quiz, etc.)

---

## 2026-01-12 | 🐛 fix: GitHub Actions CI/CD pipeline

### 📄 **Summary**
Fix failing GitHub Actions workflow by resolving linting errors and improving test setup. Add PostgreSQL readiness check and run migrations before tests to ensure integration tests pass.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/export_prod_sample_data.py` | Modified | Remove unused variable user_ids (linting fix) |
| `.github/workflows/deploy.yml` | Modified | Add PostgreSQL wait step and migration step before tests |

### 🧠 **Rationale**
GitHub Actions CI was failing because:
1. Linting errors in scripts (unused variables, import ordering)
2. Integration tests attempted to run before database was ready
3. Missing migration step caused tests to fail on outdated schema

Adding explicit wait for PostgreSQL and running migrations ensures tests have proper database state.

### 🔄 **Behavior / Compatibility Implications**
- CI now waits for PostgreSQL to be ready before running tests
- Migrations run automatically on CI before test execution
- Linting errors fixed (11 auto-fixed, 1 manual fix)
- All unit tests passing (21/21)

### 🧪 **Testing Recommendations**
```bash
# Verify linting passes
poetry run ruff check .

# Verify unit tests pass
poetry run pytest tests/unit/ -v

# Push and verify GitHub Actions succeeds
git push origin main
```

### 📌 **Follow‑ups**
- Monitor GitHub Actions build status
- Consider splitting unit/integration tests into separate workflows for faster feedback

---

## 2026-01-12 | 🚀 feat: Rating moderation and analytics for admins

### 📄 **Summary**
Add comprehensive rating moderation system for admins with analytics, flagging, and management tools. Users can flag inappropriate ratings, and admins can view/delete flagged content with detailed analytics.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/rating_flag.py` | Added | RatingFlag model for user reports |
| `app/schemas/rating_flag.py` | Added | Flag request/response schemas |
| `app/schemas/admin.py` | Modified | Add AdminRatingResponse, RatingAnalytics |
| `app/api/v1/admin.py` | Modified | Add rating list, delete, analytics endpoints |
| `app/api/v1/books.py` | Modified | Add flag rating endpoint |
| `app/main.py` | Modified | Update OpenAPI docs for rating features |
| `app/db/migrations/versions/20260112_0837_*.py` | Added | Rating flags table migration |
| `tests/unit/test_rating_analytics.py` | Added | Unit tests for rating calculations |

### 🧠 **Rationale**
Admins need tools to moderate inappropriate ratings and understand rating patterns. Users need ability to report spam/offensive reviews. Analytics help identify top content and trends.

### 🔄 **Behavior / Compatibility Implications**
- New admin endpoints: GET/DELETE /v1/admin/ratings, GET /v1/admin/analytics/ratings
- Users can flag ratings: POST /v1/books/{book_id}/ratings/{rating_id}/flag
- Flags tracked with reason (spam, offensive, irrelevant, other)
- Analytics show distribution, top books, flagged counts
- Fixed admin stats bug (visibility field)

### 🧪 **Testing Recommendations**
```bash
# Run unit tests
poetry run pytest tests/unit/test_rating_analytics.py -v

# Test admin rating list
curl http://localhost:8000/v1/admin/ratings?flagged_only=true \
  -H "Authorization: Bearer <admin_token>"

# Test rating analytics
curl http://localhost:8000/v1/admin/analytics/ratings \
  -H "Authorization: Bearer <admin_token>"
```

### 📌 **Follow‑ups**
- Add mobile admin screens for rating moderation
- Run database migration for rating_flags table
- Consider auto-hiding ratings with multiple flags

---

## 2026-01-12 | 🚀 feat: Reading progress tracking with cross-device sync

### 📄 **Summary**
Add reading progress tracking system that records user's current page, reading time, and calculates reading streaks. Progress syncs across devices and persists in database.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/progress.py` | Added | ReadingProgress model with streak calculation |
| `app/schemas/progress.py` | Added | Progress request/response schemas |
| `app/repositories/progress_repo.py` | Added | Progress data access with streak logic |
| `app/services/progress_service.py` | Added | Progress business logic |
| `app/api/v1/progress.py` | Added | Progress API endpoints |
| `app/api/v1/router.py` | Modified | Register progress router |
| `app/db/migrations/versions/20260112_0819_*.py` | Added | Database migration for reading_progress table |
| `tests/unit/test_progress_service.py` | Added | Unit tests for progress calculations |

### 🧠 **Rationale**
Users need cross-device reading progress sync and motivation through reading streaks. Progress tracking enables:
- Resume reading from last page on any device
- Reading streaks to encourage daily reading
- Reading time statistics
- Completed books tracking

### 🔄 **Behavior / Compatibility Implications**
- New endpoints: GET/PUT /v1/books/{id}/progress, GET /v1/progress/recent, GET /v1/progress/stats
- Progress auto-updates as users read
- Streak calculated from consecutive days with reading activity
- Reading time accumulates per book

### 🧪 **Testing Recommendations**
```bash
# Run unit tests
poetry run pytest tests/unit/test_progress_service.py -v

# Test progress tracking
curl -X PUT http://localhost:8000/v1/books/{book_id}/progress \
  -H "Authorization: Bearer <token>" \
  -d '{"current_page": 42, "total_pages": 350, "reading_time_seconds": 120}'

# Get reading stats
curl http://localhost:8000/v1/books/{book_id}/progress \
  -H "Authorization: Bearer <token>"
```

### 📌 **Follow‑ups**
- Run database migration: poetry run alembic upgrade head
- Monitor progress update performance
- Consider adding progress analytics to admin panel

---

## 2026-01-12 | 🐛 fix: Critical admin schema bug and category filter

### 📄 **Summary**
Fix critical admin API bug where AdminBookResponse referenced non-existent fields (is_public, pages_count) instead of actual Book model fields (visibility, page_count). Add cache invalidation on book mutations. Fix mobile category filter by aligning categories with API.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `app/schemas/admin.py` | Modified | Fix field names: is_public → visibility, pages_count → page_count |
| `app/api/v1/admin.py` | Modified | Update queries to use visibility and page_count |
| `app/services/book_service.py` | Modified | Add cache invalidation on create/update/delete |
| `tests/unit/test_admin_schemas.py` | Added | Unit tests for admin schema validation |
| Mobile: `constants/categories.ts` | Modified | Align categories with API (add Islamic categories) |

### 🧠 **Rationale**
Admin endpoints were failing with AttributeError because the schema referenced fields that don't exist on the Book model. This was a critical bug preventing admin book management from working.

Search cache was never invalidated when books were created, updated, or deleted, leading to stale results.

Mobile category filter wasn't working because app categories (popular, trending) didn't match API categories (quran, hadith, fiqh, etc.).

### 🔄 **Behavior / Compatibility Implications**
- Admin book list endpoint now works correctly
- Search cache automatically invalidated on book mutations
- Mobile app category filter now functional
- Mobile categories updated to match Islamic library focus

### 🧪 **Testing Recommendations**
```bash
# Run unit tests
poetry run pytest tests/unit/ -v

# Test admin endpoints
curl -H "Authorization: Bearer <admin_token>" \
  http://localhost:8000/v1/admin/books?visibility=public

# Test mobile category filter
# Select "Quran" category in library screen
```

### 📌 **Follow‑ups**
- Implement PostgreSQL full-text search (Phase 1.2)
- Add more unit tests for other services

---

## 2026-01-12 | 🧹 chore: Add Sample Data Export/Import Scripts

### 📄 **Summary**
Add scripts to export sanitized sample data from production Azure PostgreSQL and import it into local development database. Exported 50 books, 20 users, ratings, favorites, and chat sessions for realistic testing.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/export_prod_sample_data.py` | Added | Export sample data from production with PII sanitization |
| `scripts/import_sample_data.py` | Added | Import sample data to local database |
| `data/.gitignore` | Added | Exclude data files from git |
| `data/README.md` | Added | Document data source and usage |

### 🧠 **Rationale**
The existing seed data in the repository was outdated and didn't match the current database schema. Using real production data (sanitized) provides:
- More realistic testing scenarios
- Verification of schema compatibility
- Complex data relationships (ratings, favorites, chat history)
- Books with actual metadata and categories

### 🔄 **Behavior / Compatibility Implications**
- Data is sanitized: all passwords hashed to "test123", emails changed to @test.com
- Display names anonymized for privacy
- Original book titles/authors preserved for testing
- No breaking changes to existing functionality

### 🧪 **Testing Recommendations**
```bash
# Export sample data (one-time)
poetry run python scripts/export_prod_sample_data.py

# Import to local database
poetry run python scripts/import_sample_data.py

# Test login with any user
# Password: test123
```

### 📌 **Follow‑ups**
- Update dev-with-data.sh to use new import script
- Consider automating periodic data refreshes

---

## 2026-01-11 | 🧹 chore: Data Migration from Supabase to Azure

### 📄 **Summary**
Complete data and file migration from Supabase (ilm-red-unbound) to Azure (ilm-red-api). Migrated 590 books, 34 users, 22 ratings, 37 favorites, and 83 chat sessions with all associated files to Azure Blob Storage.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/migrate_from_supabase.py` | Added | Main migration script for database records |
| `scripts/migrate_files_incremental.py` | Added | Incremental file migration with retry logic |
| `scripts/migrate_files_parallel.py` | Added | Parallel file migration (deprecated) |
| `scripts/migrate_files_only.py` | Added | File-only migration script |

### 🧠 **Rationale**

| Migration Component | Count | Details |
|---------------------|-------|---------|
| Users | 34 | Profiles with generated password hashes |
| Books | 590 | All book metadata and file references |
| Book Files | 590 | PDFs, EPUBs, TXTs uploaded to Azure Blob |
| Cover Images | 584 | Thumbnails uploaded to Azure Blob |
| Ratings | 22 | User book ratings |
| Favorites | 37 | User bookmarks |
| Chat Sessions | 83 | AI chat history |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| File paths | Books now use `{bookId}/file.{ext}` format in Azure Blob Storage |
| Cover URLs | Covers now use `{bookId}/cover.jpg` format |
| User passwords | All users must use "Forgot Password" to login |

### 🧪 **Testing Recommendations**

```bash
# Verify file counts in Azure
az storage blob list --account-name ilmredprodstorage --container-name books --query "length(@)"

# Verify database records
psql $DATABASE_URL -c "SELECT COUNT(*) FROM books WHERE file_path IS NOT NULL;"
```

### 📌 **Follow‑ups**
- [x] Complete file migration (590/590 books, 584/584 covers)
- [x] Update database with Azure file paths
- [ ] Migrate remaining 4 books created after initial export
- [ ] Notify users to reset passwords

---

## 2026-01-11 | 🚀 feat: Enhanced Security and Validation (v1.2.1)

### 📄 **Summary**
Additional security hardening: rate limiting on search endpoints, sort field validation, and magic byte file validation to prevent MIME type spoofing attacks.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `app/api/v1/search.py` | Modified | Added 30 req/min rate limit on search, 60 req/min on suggestions |
| `app/api/v1/books.py` | Modified | Added sort field allowlist validation |
| `app/services/book_service.py` | Modified | Added magic byte file type detection |
| `app/config.py` | Modified | Bump version to 1.2.1 |

### 🧠 **Rationale**

| Security Enhancement | Purpose |
|---------------------|---------|
| Search rate limiting | Prevent abuse of search endpoints |
| Sort field validation | Defense-in-depth against SQL injection |
| Magic byte validation | Prevent MIME type spoofing attacks on file uploads |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| Search rate limit | 30 req/min per IP on /search, 60 req/min on /suggestions |
| Sort validation | Invalid sort fields return 400 error with allowed fields list |
| Magic byte check | Files must have valid PDF/EPUB/TXT magic bytes regardless of Content-Type header |

### 📌 **Follow‑ups**
- [ ] Add more comprehensive file content validation
- [ ] Consider Redis-backed rate limiting for distributed deployments

---

## 2026-01-11 | 🔒 security: Rate Limiting and Path Traversal Fix (v1.2.0)

### 📄 **Summary**
Implemented critical security improvements including rate limiting for AI chat endpoints and fixed a path traversal vulnerability in local file storage. Also updated the app motto to "Read, Chat, Understand".

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `app/rate_limiter.py` | Added | Central rate limiter module using slowapi |
| `app/main.py` | Modified | Integrated rate limiter middleware, updated API motto |
| `app/api/v1/chat.py` | Modified | Added 10 req/min rate limits to AI endpoints |
| `app/storage/local.py` | Modified | Fixed path traversal vulnerability |
| `pyproject.toml` | Modified | Added slowapi dependency |
| `README.md` | Modified | Updated tagline to "Read, Chat, Understand" |

### 🧠 **Rationale**

| Security Issue | Risk | Fix |
|----------------|------|-----|
| No rate limiting | DoS attacks, API abuse, cost explosion from unlimited AI calls | Implemented slowapi with 10 req/min on chat endpoints |
| Path traversal | Arbitrary file read/write via `../` sequences | Added resolve() + base path validation |

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| Rate limiting | Users exceeding 10 AI requests/minute receive HTTP 429 |
| Path traversal fix | Requests with `../` in paths now raise ValueError |
| New motto | API documentation shows "Read, Chat, Understand" |

### 🧪 **Testing Recommendations**

```bash
# Test rate limiting (11th request should fail with 429)
for i in {1..11}; do
  curl -X POST http://localhost:8000/v1/chats/SESSION_ID/messages \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"content": "test"}' \
    -w "%{http_code}\n" -o /dev/null -s
done

# Test path traversal protection
# Should raise ValueError, not access /etc/passwd
```

### 📌 **Follow‑ups**
- [ ] Add rate limiting to search endpoints (30/min)
- [ ] Add magic byte file validation for uploads
- [ ] Consider Redis-backed rate limiting for distributed deployments
- [ ] Add sort field allowlist validation

---

## 2026-01-10 | 📘 docs: Comprehensive Admin API Documentation

### 📄 **Summary**
Added comprehensive documentation for the Admin API including separate Swagger UI, detailed README, and updated PRD/TDD with admin endpoint specifications.

### 📁 **Files Changed**
| File | Change Type | Description |
|------|-------------|-------------|
| `docs/ADMIN_API.md` | Added | Comprehensive Admin API documentation with examples |
| `docs/PRD.md` | Modified | Updated Section 4.9 with implemented admin endpoints |
| `app/main.py` | Modified | Added `/admin/docs` Swagger UI and `/admin/openapi.json` |

### 🧠 **Rationale**
Admin API needed comprehensive documentation for developers and operators managing the ILM Red platform.

### 🔄 **New Admin Documentation**

| Documentation | URL |
|---------------|-----|
| **Admin Swagger UI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/admin/docs |
| **Admin OpenAPI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/admin/openapi.json |
| **Admin API Guide** | [docs/ADMIN_API.md](./docs/ADMIN_API.md) |

### 🧪 **Testing Recommendations**
- [ ] Verify `/admin/docs` renders Swagger UI
- [ ] Verify `/admin/openapi.json` returns filtered schema
- [ ] Test all documented admin endpoints

### 📌 **Follow‑ups**
- [ ] Add admin API integration tests
- [ ] Add audit logging for admin actions
- [ ] Create admin SDK helpers

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
| Admin Swagger | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/admin/docs |
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
