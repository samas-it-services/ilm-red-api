# ILM Red API

Cloud-native, vendor-agnostic API platform for digital knowledge management.

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
| Runtime | Node.js 20 LTS |
| Framework | Fastify |
| Language | TypeScript 5.x |
| Database | Azure Cosmos DB |
| Cache | Azure Redis |
| Search | Azure AI Search |
| Storage | Azure Blob + CDN |
| Events | Azure Event Hubs |
| Analytics | Microsoft Fabric |
| AI | Azure OpenAI |
| Gateway | Azure API Management |

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](./docs/PRD.md) | Product Requirements Document |
| [TDD](./docs/TDD.md) | Technical Design Document |
| [Architecture](./docs/ARCHITECTURE.md) | System Architecture |
| [OpenAPI](./openapi/api-v1.yaml) | API Specification |

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

## Quick Start

```bash
# Clone repository
git clone https://github.com/ilm-red/ilm-red-api.git
cd ilm-red-api

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your credentials

# Start development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## Project Structure

```
ilm-red-api/
├── docs/
│   ├── ARCHITECTURE.md    # System architecture
│   ├── PRD.md             # Product requirements
│   └── TDD.md             # Technical design
├── openapi/
│   └── api-v1.yaml        # OpenAPI 3.1 specification
├── src/
│   ├── services/          # Business logic
│   ├── routes/            # API endpoints
│   ├── models/            # Data models
│   ├── middleware/        # Auth, validation, etc.
│   └── utils/             # Helpers
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── package.json
```

## Environment Variables

```bash
# Server
NODE_ENV=development
PORT=3000

# Azure Cosmos DB
COSMOS_ENDPOINT=https://xxx.documents.azure.com
COSMOS_KEY=xxx
COSMOS_DATABASE=ilm-red

# Azure Redis
REDIS_URL=redis://xxx.redis.cache.windows.net:6380

# Azure Blob Storage
BLOB_CONNECTION_STRING=xxx
BLOB_CONTAINER=books

# Azure AI Search
SEARCH_ENDPOINT=https://xxx.search.windows.net
SEARCH_API_KEY=xxx

# Azure OpenAI
OPENAI_ENDPOINT=https://xxx.openai.azure.com
OPENAI_API_KEY=xxx

# Auth
JWT_SECRET=xxx
JWT_EXPIRY=15m
REFRESH_EXPIRY=7d
```

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
- `GET /v1/search/books` - Book search
- `POST /v1/search/semantic` - Semantic search
- `GET /v1/search/autocomplete` - Autocomplete

### AI
- `POST /v1/ai/sessions` - Create chat session
- `POST /v1/ai/sessions/{id}/messages` - Send message
- `GET /v1/ai/billing/balance` - Check credits

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
