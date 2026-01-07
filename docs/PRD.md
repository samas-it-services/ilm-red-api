# ILM Red API - Product Requirements Document (PRD)

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Last Updated** | January 2025 |
| **Status** | Draft |
| **Owner** | ILM Red Team |

---

## 1. Executive Summary

### 1.1 Product Vision

**ILM Red API** is a cloud-native, vendor-agnostic backend API platform that powers the next generation of digital knowledge management applications. Built on an API-first architecture, it enables web, mobile, and third-party integrations to access a comprehensive digital library ecosystem with AI-powered features.

### 1.2 Mission Statement

To provide a scalable, secure, and extensible API platform that enables hundreds of thousands of users to manage, share, and interact with millions of digital books while leveraging AI for enhanced learning experiences.

### 1.3 Key Objectives

| Objective | Target |
|-----------|--------|
| Scale to enterprise | 500,000+ users, 10M+ books |
| Vendor independence | No lock-in to Supabase, Localbase, etc. |
| API-first design | 100% functionality via documented APIs |
| AI integration | Multi-model AI chat with billing |
| Global availability | < 200ms latency worldwide |

### 1.4 Target Audience

- **Primary**: Developers building book management applications
- **Secondary**: Educational institutions and enterprises
- **Tertiary**: Third-party integration partners

---

## 2. Product Overview

### 2.1 System Context

```
┌──────────────────────────────────────────────────────────────────────┐
│                          EXTERNAL SYSTEMS                             │
│                                                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │   Web    │  │  Mobile  │  │  3rd     │  │  Admin   │             │
│  │   Apps   │  │   Apps   │  │  Party   │  │  Portal  │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │             │                    │
│       └─────────────┴──────┬──────┴─────────────┘                    │
│                            │                                          │
│                            ▼                                          │
│                   ┌─────────────────┐                                │
│                   │  ILM RED API    │                                │
│                   │  Platform       │                                │
│                   └─────────────────┘                                │
│                            │                                          │
│       ┌────────────────────┼────────────────────┐                    │
│       │                    │                    │                    │
│       ▼                    ▼                    ▼                    │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐               │
│  │  Azure   │        │  Azure   │        │Multi-AI  │               │
│  │  Services│        │  Fabric  │        │Providers │               │
│  └──────────┘        └──────────┘        └──────────┘               │
│                                          (Qwen, OpenAI,              │
│                                           Anthropic, Google,         │
│                                           xAI, DeepSeek)             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Capabilities

| Domain | Capabilities |
|--------|-------------|
| **Authentication** | OAuth 2.0, JWT, API Keys, MFA, SSO |
| **Books** | CRUD, multi-format upload, metadata, thumbnails |
| **Users** | Profiles, preferences, roles, permissions |
| **Search** | Full-text, semantic, vector, faceted |
| **AI Chat** | Multi-model, context-aware, citations, billing |
| **Social** | Book clubs, discussions, invites, moderation |
| **Progress** | Cross-device sync, annotations, bookmarks |
| **Analytics** | Usage metrics, reports, dashboards |
| **Admin** | User management, moderation, audit logs |

### 2.3 Key Differentiators

1. **Vendor Agnostic**: Swap databases, caches, AI providers without code changes
2. **Scale from Zero**: Pay-as-you-go from startup to enterprise
3. **AI-Native**: Built-in AI chat with transparent billing
4. **Developer Experience**: Comprehensive SDKs, documentation, sandboxes
5. **Compliance Ready**: GDPR, SOC2, data residency support

---

## 3. User Personas

### 3.1 API Consumer Developer

| Attribute | Description |
|-----------|-------------|
| **Role** | Frontend/Mobile Developer |
| **Goals** | Build apps using ILM Red APIs |
| **Needs** | Clear docs, SDKs, sandbox environment |
| **Pain Points** | Inconsistent APIs, poor error messages |

**User Stories:**
- As a developer, I want clear API documentation so I can integrate quickly
- As a developer, I want SDKs in my language so I don't write boilerplate
- As a developer, I want sandbox environments so I can test safely

### 3.2 Platform Administrator

| Attribute | Description |
|-----------|-------------|
| **Role** | IT Admin / DevOps |
| **Goals** | Manage users, monitor system health |
| **Needs** | Admin APIs, dashboards, alerts |
| **Pain Points** | Manual operations, lack of visibility |

**User Stories:**
- As an admin, I want user management APIs so I can automate provisioning
- As an admin, I want audit logs so I can track all changes
- As an admin, I want health APIs so I can monitor system status

### 3.3 Integration Partner

| Attribute | Description |
|-----------|-------------|
| **Role** | Third-party Service Provider |
| **Goals** | Integrate ILM Red into their platform |
| **Needs** | Webhooks, OAuth apps, rate limits |
| **Pain Points** | Complex auth, unreliable webhooks |

**User Stories:**
- As a partner, I want webhooks so my system stays synchronized
- As a partner, I want OAuth app registration so users can authorize access
- As a partner, I want predictable rate limits so I can plan capacity

---

## 4. Functional Requirements

### 4.1 Authentication & Authorization

#### FR-AUTH-001: OAuth 2.0 / OpenID Connect
- Support authorization code flow with PKCE
- Support client credentials flow for service accounts
- Support refresh token rotation
- Issue JWT access tokens with configurable expiry

#### FR-AUTH-002: API Key Authentication
- Generate and revoke API keys per user
- Support key prefixes for identification (e.g., `ilm_live_`, `ilm_test_`)
- Track API key usage and last used timestamp
- Set key-specific rate limits and permissions

#### FR-AUTH-003: Role-Based Access Control (RBAC)
- Define roles: `user`, `premium`, `moderator`, `admin`, `super_admin`
- Assign permissions to roles
- Support custom role definitions
- Enforce least privilege principle

#### FR-AUTH-004: Multi-Factor Authentication
- Support TOTP (Authenticator apps)
- Support email verification codes
- Require MFA for admin operations

### 4.2 Books API

#### FR-BOOK-001: Book CRUD Operations
```
POST   /v1/books              Create a new book
GET    /v1/books              List books (paginated, filtered)
GET    /v1/books/{id}         Get book details
PATCH  /v1/books/{id}         Update book metadata
DELETE /v1/books/{id}         Delete a book (soft delete)
```

#### FR-BOOK-002: File Upload
- Support multipart upload for files up to 500MB
- Support resumable uploads for large files
- Accept formats: PDF, EPUB, TXT, MOBI
- Generate thumbnails asynchronously
- Calculate SHA256 hash for deduplication
- Validate file integrity on upload

#### FR-BOOK-003: Book Metadata
- Required: title, visibility
- Optional: author, description, category, language, ISBN
- Auto-detect: language from filename, page count from file
- Support custom metadata fields

#### FR-BOOK-004: Visibility Controls
```
public    - Visible to all users
private   - Visible only to owner
friends   - Visible to owner's friends
club      - Visible to book club members
```

#### FR-BOOK-005: Book Categories
Support predefined categories:
- Religion, Islamic Studies, Quran Studies, Hadith
- Fiqh, History, Biography, Philosophy
- Science, Technology, Education, Self-Help
- Fiction, Children, Languages, Other

### 4.3 Users API

#### FR-USER-001: User Management
```
GET    /v1/users/me           Get current user profile
PATCH  /v1/users/me           Update current user profile
GET    /v1/users/{id}         Get public user profile
GET    /v1/users/{id}/books   Get user's public books
```

#### FR-USER-002: User Preferences
- Theme preference (light/dark/system)
- Language preference
- Notification settings
- Privacy settings (profile visibility)
- Reading preferences
- **AI preferences** (default model, vendor, temperature, max tokens)

#### FR-USER-003: Social Connections
```
GET    /v1/users/me/friends          List friends
POST   /v1/users/me/friends          Send friend request
DELETE /v1/users/me/friends/{id}     Remove friend
GET    /v1/users/me/friends/requests List pending requests
```

### 4.4 Search API

#### FR-SEARCH-001: Global Search
```
GET /v1/search?q={query}&types=books,users,clubs
```
- Search across books, users, clubs, Q&A
- Return results grouped by type
- Support pagination per type
- Cache results for 5 minutes

#### FR-SEARCH-002: Book Search
```
GET /v1/books/search?q={query}&filters={...}
```
Filters:
- category (multi-select)
- language
- visibility
- author
- uploadedAfter / uploadedBefore
- rating (minimum)

Sort options:
- relevance (default)
- title
- date
- rating
- views

#### FR-SEARCH-003: Semantic Search
```
POST /v1/search/semantic
{
  "query": "books about personal growth",
  "limit": 10
}
```
- Use vector embeddings for semantic matching
- Support hybrid search (text + semantic)
- Return relevance scores

#### FR-SEARCH-004: Autocomplete
```
GET /v1/search/autocomplete?q={prefix}&types=books,authors
```
- Return top 10 suggestions within 100ms
- Support fuzzy matching for typos

### 4.5 AI Chat API

#### FR-AI-001: Chat Sessions
```
POST   /v1/ai/sessions              Create new chat session
GET    /v1/ai/sessions              List user's sessions
GET    /v1/ai/sessions/{id}         Get session with messages
DELETE /v1/ai/sessions/{id}         Delete session
```

#### FR-AI-002: Chat Messages
```
POST /v1/ai/sessions/{id}/messages
{
  "content": "What is the main theme of this book?",
  "model": "gpt-4o-mini"  // optional
}
```
Response:
```json
{
  "id": "msg_xxx",
  "content": "The main theme of this book...",
  "citations": [
    {"page": 15, "excerpt": "...relevant text..."},
    {"page": 42, "excerpt": "...another reference..."}
  ],
  "usage": {
    "promptTokens": 1523,
    "completionTokens": 456,
    "totalTokens": 1979,
    "costUsd": 0.0023
  }
}
```

#### FR-AI-003: Multi-Vendor Model Selection

ILM Red supports multiple AI vendors for flexibility, cost optimization, and redundancy:

**Supported Vendors & Models:**

| Vendor | Models | Use Case |
|--------|--------|----------|
| **Qwen (Alibaba)** | qwen-turbo, qwen-plus, qwen-max | Default for public books (cost-effective) |
| **OpenAI** | gpt-4o-mini, gpt-4o, gpt-4-turbo, o1-preview, o1-mini | Default for private books |
| **Anthropic** | claude-3-haiku, claude-3-5-sonnet, claude-3-opus | Long-form content |
| **Google** | gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash | Long context windows |
| **xAI** | grok-beta, grok-2 | Alternative option |
| **DeepSeek** | deepseek-chat, deepseek-coder | Cost-effective alternative |

**Model Routing Strategy:**

1. **Public Books**: Use Qwen (qwen-turbo) by default
   - Reason: Cost-effective at $0.40/1M tokens
   - Accessible to all users including anonymous

2. **Private Books**: Use user's preferred model (default: gpt-4o-mini)
   - Users can set their preferred model in preferences
   - Premium users have access to all models

3. **Explicit Override**: User can specify model in request
   - Validation against available models for user tier
   - Premium-only models require premium subscription

**Free Tier Models:**
- qwen-turbo, gpt-4o-mini, gemini-1.5-flash, deepseek-chat, claude-3-haiku

**Premium-Only Models:**
- All other models (gpt-4o, claude-3-opus, etc.)

**Model Selection API:**
```json
POST /v1/ai/sessions/{id}/messages
{
  "content": "What is the main theme?",
  "model": "claude-3-sonnet"  // optional - overrides defaults
}
```

**Available Models Endpoint:**
```
GET /v1/ai/models
```
Response:
```json
{
  "data": [
    {
      "id": "qwen-turbo",
      "name": "Qwen Turbo",
      "vendor": "qwen",
      "maxTokens": 8192,
      "inputCostPer1M": 0.10,
      "outputCostPer1M": 0.30,
      "premium": false,
      "accessible": true
    }
  ]
}
```

#### FR-AI-004: Book Context
- Automatically include book content as context
- Chunk large books intelligently
- Use vector search to find relevant passages
- Track context window usage

#### FR-AI-005: AI Billing
```
GET /v1/ai/billing/balance        Get credit balance
GET /v1/ai/billing/usage          Get usage history
POST /v1/ai/billing/purchase      Purchase credits (Stripe)
```
- Apply 40% markup on AI costs
- Track usage per model per user
- Support credit limits and alerts

### 4.6 Book Clubs API

#### FR-CLUB-001: Club Management
```
POST   /v1/clubs                  Create book club
GET    /v1/clubs                  List clubs (discover)
GET    /v1/clubs/{id}             Get club details
PATCH  /v1/clubs/{id}             Update club
DELETE /v1/clubs/{id}             Delete club
```

#### FR-CLUB-002: Membership
```
POST   /v1/clubs/{id}/members            Request to join
GET    /v1/clubs/{id}/members            List members
PATCH  /v1/clubs/{id}/members/{userId}   Update role
DELETE /v1/clubs/{id}/members/{userId}   Remove member
```

Roles:
- `owner` - Full control, can delete club
- `admin` - Manage members and content
- `moderator` - Moderate discussions
- `member` - Participate in activities

#### FR-CLUB-003: Invitations
```
POST /v1/clubs/{id}/invites
{
  "email": "user@example.com",
  "role": "member",
  "message": "Join our reading group!"
}
```
- Generate unique invite links
- Set expiration (default 7 days)
- Track invite status (pending, accepted, expired)

#### FR-CLUB-004: Club Books
```
POST   /v1/clubs/{id}/books          Add book to club
GET    /v1/clubs/{id}/books          List club books
DELETE /v1/clubs/{id}/books/{bookId} Remove book
```

#### FR-CLUB-005: Discussions
```
POST   /v1/clubs/{id}/discussions           Create discussion
GET    /v1/clubs/{id}/discussions           List discussions
GET    /v1/clubs/{id}/discussions/{did}     Get discussion
POST   /v1/clubs/{id}/discussions/{did}/comments  Add comment
```

### 4.7 Reading Progress API

#### FR-PROGRESS-001: Progress Tracking
```
GET  /v1/progress/{bookId}         Get reading progress
PUT  /v1/progress/{bookId}         Update progress
{
  "currentPage": 42,
  "totalPages": 350,
  "scale": 1.5,
  "lastPosition": {"x": 100, "y": 200}
}
```

#### FR-PROGRESS-002: Cross-Device Sync
- Sync progress within 5 seconds of update
- Handle concurrent updates (last write wins)
- Store device identifier for debugging

#### FR-PROGRESS-003: Reading History
```
GET /v1/progress/history?limit=20
```
- Return recently read books with progress
- Include reading time estimates

### 4.8 Analytics API

#### FR-ANALYTICS-001: User Analytics
```
GET /v1/analytics/users/me
{
  "booksUploaded": 25,
  "booksRead": 89,
  "readingTimeMinutes": 12500,
  "aiChatsInitiated": 156,
  "clubsJoined": 5
}
```

#### FR-ANALYTICS-002: Book Analytics (Owner)
```
GET /v1/analytics/books/{id}
{
  "views": 1523,
  "uniqueReaders": 89,
  "averageReadingTime": 45,
  "completionRate": 0.23,
  "ratings": {"1": 2, "2": 5, "3": 15, "4": 40, "5": 28}
}
```

#### FR-ANALYTICS-003: Admin Analytics
```
GET /v1/admin/analytics/overview
GET /v1/admin/analytics/users
GET /v1/admin/analytics/books
GET /v1/admin/analytics/ai
```

### 4.9 Admin API

#### FR-ADMIN-001: User Management
```
GET    /v1/admin/users              List all users
GET    /v1/admin/users/{id}         Get user details
PATCH  /v1/admin/users/{id}         Update user (roles, status)
DELETE /v1/admin/users/{id}         Delete/suspend user
POST   /v1/admin/users/{id}/impersonate  Impersonate user
```

#### FR-ADMIN-002: Content Moderation
```
GET  /v1/admin/moderation/queue     Get moderation queue
POST /v1/admin/moderation/approve   Approve content
POST /v1/admin/moderation/reject    Reject content
POST /v1/admin/moderation/flag      Flag content for review
```

#### FR-ADMIN-003: Audit Logs
```
GET /v1/admin/audit-logs
{
  "filters": {
    "userId": "...",
    "action": "book.updated",
    "startDate": "2024-01-01",
    "endDate": "2024-01-31"
  }
}
```

Log format:
```json
{
  "id": "log_xxx",
  "timestamp": "2024-01-15T10:30:00Z",
  "userId": "user_xxx",
  "action": "book.updated",
  "resourceType": "book",
  "resourceId": "book_xxx",
  "changes": {
    "title": {"old": "Old Title", "new": "New Title"}
  },
  "ipAddress": "192.168.1.1",
  "userAgent": "Mozilla/5.0..."
}
```

#### FR-ADMIN-004: System Configuration
```
GET  /v1/admin/config               Get system config
PUT  /v1/admin/config               Update config
```
Configurable:
- Upload limits per tier
- AI model availability
- Rate limits
- Feature flags

### 4.10 Webhooks API

#### FR-WEBHOOK-001: Webhook Management
```
POST   /v1/webhooks                 Register webhook
GET    /v1/webhooks                 List webhooks
GET    /v1/webhooks/{id}            Get webhook details
PATCH  /v1/webhooks/{id}            Update webhook
DELETE /v1/webhooks/{id}            Delete webhook
```

#### FR-WEBHOOK-002: Webhook Events
Supported events:
- `book.created`, `book.updated`, `book.deleted`
- `user.registered`, `user.updated`
- `club.created`, `club.memberJoined`
- `progress.updated`
- `ai.session.completed`

Payload format:
```json
{
  "id": "evt_xxx",
  "type": "book.created",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "book": {...}
  }
}
```

#### FR-WEBHOOK-003: Webhook Security
- Sign payloads with HMAC-SHA256
- Include signature in `X-ILM-Signature` header
- Provide verification SDK methods
- Retry failed deliveries (exponential backoff)

### 4.11 Page Image Processing API

#### FR-PAGE-001: PDF Page Extraction
- Extract all pages from uploaded PDF books as images
- Generate images at 4 resolution tiers:
  - **Thumbnail** (150px width) - Navigation, grids, quick preview
  - **Medium** (800px width) - Mobile reading, bandwidth-conscious
  - **High-res** (1600px width) - Desktop reading, standard zoom
  - **Ultra** (3200px width) - High-DPI displays, deep zoom, print
- Process pages asynchronously in background after upload completes
- Maintain original aspect ratio for all resolutions
- Store as JPEG with quality levels: 70% (thumb), 85% (medium), 92% (high-res), 95% (ultra)
- Continue processing on individual page failures (partial success allowed)

#### FR-PAGE-002: Book Cover Management
- **Auto-generated**: Extract from first page of PDF automatically
- **Custom upload**: Allow users to upload custom cover images
- Custom covers override auto-generated covers
- Support image formats: JPEG, PNG, WebP (max 10MB)
- Generate cover at standard dimensions (800px width)
- Revert to auto-generated cover when custom is deleted

#### FR-PAGE-003: Page Image Retrieval
```
GET  /v1/books/{bookId}/pages                    List all pages with metadata
GET  /v1/books/{bookId}/pages/{pageNumber}       Get specific page URLs
```

Response format for page listing:
```json
{
  "data": [
    {
      "pageNumber": 1,
      "dimensions": {"width": 612, "height": 792},
      "urls": {
        "thumbnail": "https://cdn.../pages/thumbnail/1.jpg",
        "medium": "https://cdn.../pages/medium/1.jpg",
        "highRes": "https://cdn.../pages/high-res/1.jpg",
        "ultra": "https://cdn.../pages/ultra/1.jpg"
      },
      "fileSizes": {
        "thumbnail": 15000,
        "medium": 85000,
        "highRes": 250000,
        "ultra": 750000
      }
    }
  ],
  "pagination": {...},
  "metadata": {
    "totalPages": 350,
    "generationStatus": "completed"
  }
}
```

- Return signed URLs for secure access (1-hour expiry)
- Support pagination for books with many pages
- Include file sizes for bandwidth planning
- Filter by resolution: `?resolution=medium`

#### FR-PAGE-004: Cover Management Endpoints
```
GET    /v1/books/{bookId}/cover                  Get cover URL
PUT    /v1/books/{bookId}/cover                  Upload custom cover
DELETE /v1/books/{bookId}/cover                  Remove custom cover
```

Response format:
```json
{
  "bookId": "book_xxx",
  "url": "https://cdn.../covers/book_xxx.jpg",
  "isCustom": true,
  "dimensions": {"width": 800, "height": 1200},
  "fileSize": 125000,
  "mimeType": "image/jpeg"
}
```

- Custom cover upload accepts multipart form data
- Returns 404 if no cover exists (edge case for failed extraction)
- Delete endpoint reverts to auto-generated cover

#### FR-PAGE-005: Generation Progress Tracking
```
POST /v1/books/{bookId}/pages/generate           Trigger page generation
GET  /v1/books/{bookId}/pages/status             Get generation status
```

Generation is automatically triggered on book upload. Manual trigger available for:
- Re-processing after failures
- Regeneration with different settings

Status response format:
```json
{
  "status": "processing",
  "progress": {
    "totalPages": 350,
    "completedPages": 125,
    "failedPages": 2,
    "percentage": 36
  },
  "currentJob": {
    "id": "job_xxx",
    "startedAt": "2024-01-15T10:30:00Z",
    "estimatedCompletion": "2024-01-15T10:35:00Z"
  },
  "failedPageNumbers": [45, 89]
}
```

Status values:
- `pending` - Queued for processing
- `processing` - Currently extracting pages
- `completed` - All pages processed successfully
- `partial` - Completed with some failures
- `failed` - Complete failure (source file issue)

#### FR-PAGE-006: Webhook Events
Emit events for page generation lifecycle:
- `book.pages.generation.started` - Processing began
- `book.pages.generation.progress` - Progress update (every 10%)
- `book.pages.generation.completed` - All pages extracted
- `book.pages.generation.failed` - Critical failure occurred
- `book.cover.updated` - Cover changed (auto or custom)

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target |
|--------|--------|
| API Response Time (p50) | < 100ms |
| API Response Time (p99) | < 500ms |
| Search Response Time | < 200ms |
| AI Chat Response Time | < 5s |
| File Upload Throughput | 50MB/s |
| Concurrent Connections | 100,000+ |

### 5.2 Scalability

| Metric | Target |
|--------|--------|
| Total Users | 500,000+ |
| Concurrent Users | 100,000+ |
| Total Books | 10,000,000+ |
| Daily API Requests | 100,000,000+ |
| File Storage | 100+ TB |

### 5.3 Availability

| Metric | Target |
|--------|--------|
| API Uptime | 99.9% (8.76 hours/year downtime) |
| Planned Maintenance Window | < 4 hours/month |
| Recovery Time Objective (RTO) | < 1 hour |
| Recovery Point Objective (RPO) | < 5 minutes |

### 5.4 Security

- TLS 1.3 for all connections
- JWT tokens with RS256 signing
- API keys with SHA256 hashing
- Rate limiting per user and IP
- DDoS protection at edge
- WAF rules for OWASP Top 10
- Data encryption at rest (AES-256)
- PII masking in logs
- SOC 2 Type II compliance ready

### 5.5 Compliance

- GDPR data residency options (EU, US, APAC)
- Right to be forgotten (data deletion API)
- Data export (user data portability)
- Consent management for analytics
- Audit logging for compliance

---

## 6. API Design Standards

### 6.1 RESTful Conventions

```
GET     /v1/resources              List resources
POST    /v1/resources              Create resource
GET     /v1/resources/{id}         Get resource
PATCH   /v1/resources/{id}         Partial update
PUT     /v1/resources/{id}         Full replace
DELETE  /v1/resources/{id}         Delete resource
```

### 6.2 Pagination

```json
GET /v1/books?page=2&limit=20

Response:
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 150,
    "totalPages": 8,
    "hasMore": true
  }
}
```

### 6.3 Filtering & Sorting

```
GET /v1/books?category=technology&language=en&sort=-createdAt
```
- Use `field=value` for exact match
- Use `-` prefix for descending sort
- Use comma for multiple values: `category=tech,science`

### 6.4 Error Responses

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      {"field": "title", "message": "Title is required"},
      {"field": "category", "message": "Invalid category"}
    ],
    "requestId": "req_abc123",
    "timestamp": "2024-01-15T10:30:00Z",
    "documentation": "https://docs.ilm-red.com/errors/VALIDATION_ERROR"
  }
}
```

Error codes:
- `400` - VALIDATION_ERROR, INVALID_REQUEST
- `401` - UNAUTHORIZED, TOKEN_EXPIRED
- `403` - FORBIDDEN, INSUFFICIENT_PERMISSIONS
- `404` - NOT_FOUND, RESOURCE_DELETED
- `409` - CONFLICT, DUPLICATE_RESOURCE
- `429` - RATE_LIMIT_EXCEEDED
- `500` - INTERNAL_ERROR
- `503` - SERVICE_UNAVAILABLE

### 6.5 Rate Limiting Headers

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 998
X-RateLimit-Reset: 1704067200
X-RateLimit-RetryAfter: 30
```

---

## 7. SDK & Developer Experience

### 7.1 Official SDKs

| Language | Package |
|----------|---------|
| JavaScript/TypeScript | `@ilm-red/sdk` |
| Python | `ilm-red-python` |
| Go | `github.com/ilm-red/go-sdk` |
| Java | `com.ilmred:sdk` |
| C# | `IlmRed.SDK` |

### 7.2 SDK Features

- Type-safe API methods
- Automatic token refresh
- Request retry with backoff
- Response pagination helpers
- Webhook signature verification
- Error handling utilities

### 7.3 Documentation

- Interactive API reference (OpenAPI/Swagger)
- Getting started guides
- Authentication tutorials
- Webhook integration guides
- Best practices documentation
- Migration guides (from Supabase)
- Changelog with breaking changes

### 7.4 Developer Portal

- API key management
- Usage dashboards
- Sandbox environment
- Request logs
- Webhook testing
- Support tickets

---

## 8. Success Metrics

### 8.1 Technical KPIs

| Metric | Target |
|--------|--------|
| API Availability | > 99.9% |
| P99 Latency | < 500ms |
| Error Rate | < 0.1% |
| SDK Adoption | 80% of API calls |

### 8.2 Business KPIs

| Metric | Target |
|--------|--------|
| Developer Signups | 1,000/month |
| Active API Users | 10,000 MAU |
| API Calls/Month | 10M+ |
| Paid Conversions | 5% |

### 8.3 Quality Metrics

| Metric | Target |
|--------|--------|
| Developer NPS | > 50 |
| Time to First API Call | < 5 minutes |
| Documentation Coverage | 100% |
| SDK Test Coverage | > 90% |

---

## 9. Risks & Mitigations

### 9.1 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Database scalability | High | Cosmos DB auto-scale, read replicas |
| AI API rate limits | Medium | Multi-provider fallback, caching |
| Search performance | High | Azure AI Search, aggressive caching |
| File storage costs | Medium | Tiered storage, lifecycle policies |

### 9.2 Business Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Low developer adoption | High | Free tier, excellent docs, SDKs |
| Competition | Medium | Unique AI features, pricing |
| Vendor lock-in (Azure) | Low | Abstraction layers, multi-cloud ready |

---

## 10. Roadmap

### Phase 1: Foundation (Months 1-3)
- Core API services (Auth, Books, Users)
- Basic search functionality
- File upload and storage
- Developer portal v1
- JavaScript SDK

### Phase 2: AI & Social (Months 4-6)
- AI Chat integration
- Book clubs functionality
- Reading progress sync
- Webhooks v1
- Python & Go SDKs

### Phase 3: Scale & Polish (Months 7-9)
- Performance optimization
- Advanced search (semantic)
- Analytics dashboards
- Admin tools
- Java & C# SDKs

### Phase 4: Enterprise (Months 10-12)
- Multi-tenant support
- SSO/SAML integration
- Custom AI models
- On-premise deployment option
- SOC 2 certification

---

## 11. Appendices

### A. Glossary

| Term | Definition |
|------|------------|
| **JWT** | JSON Web Token for authentication |
| **RBAC** | Role-Based Access Control |
| **RTO** | Recovery Time Objective |
| **RPO** | Recovery Point Objective |
| **SDK** | Software Development Kit |
| **WAF** | Web Application Firewall |

### B. Related Documents

- [Architecture Design Document](./ARCHITECTURE.md)
- [Technical Design Document](./TDD.md)
- [OpenAPI Specification](../openapi/api-v1.yaml)
- [Security Policy](./SECURITY.md)

### C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | Jan 2025 | ILM Red Team | Initial version |
