# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ILM Red API is a cloud-native, vendor-agnostic backend API platform for the ILM Red digital knowledge management ecosystem. It provides RESTful APIs for books, users, search, AI chat, book clubs, and more.

## Key Design Decisions

### 1. Vendor Agnostic Architecture
- **NO lock-in to Supabase or Localbase**
- Use abstraction layers for all data access
- Primary database: Azure Cosmos DB (but swappable)
- Cache: Azure Redis (but swappable)
- Search: Azure AI Search (but swappable)

### 2. Microsoft Fabric Integration
- Analytics data flows to Microsoft Fabric
- Use Delta Lake for historical data
- OneLake for unified data storage
- Power BI for reporting

### 3. Scale Targets
- 500,000+ total users
- 100,000+ concurrent users
- 10,000,000+ books
- < 500ms API latency (p99)
- 99.9% availability

## Architecture Patterns

### Service Decomposition
```
auth-service     - Authentication, tokens, API keys
books-service    - Book CRUD, files, metadata
users-service    - Profiles, preferences, social
search-service   - Full-text, semantic, autocomplete
ai-service       - Chat sessions, model routing
clubs-service    - Book clubs, membership
progress-service - Reading progress, sync
billing-service  - AI credits, transactions
admin-service    - Moderation, audit logs
worker-service   - Background jobs
```

### Data Layer Abstraction
```typescript
// Always use abstract interfaces, not direct SDK calls
interface DatabaseProvider {
  create<T>(collection: string, doc: T): Promise<T>;
  findById<T>(collection: string, id: string): Promise<T | null>;
  query<T>(collection: string, filter: QueryFilter): Promise<T[]>;
  update<T>(collection: string, id: string, updates: Partial<T>): Promise<T>;
  delete(collection: string, id: string): Promise<void>;
}

// Implementation can be swapped:
// - CosmosDBProvider
// - PostgreSQLProvider
// - MongoDBProvider
```

### Caching Strategy
- L1: In-memory (service-local, 100ms TTL)
- L2: Redis (distributed, 5-60min TTL)
- L3: Database (source of truth)

## Development Commands

```bash
# Development
npm run dev          # Start dev server
npm run lint         # Run ESLint
npm run typecheck    # TypeScript check

# Testing
npm run test         # All tests
npm run test:unit    # Unit tests only
npm run test:int     # Integration tests
npm run test:e2e     # End-to-end tests
npm run test:cov     # With coverage

# Build
npm run build        # Production build
npm run start        # Start production server

# Database
npm run db:migrate   # Run migrations
npm run db:seed      # Seed test data
```

## Code Style

### API Endpoints
- Use RESTful conventions
- Prefix all routes with `/v1/`
- Use consistent error responses
- Include pagination on list endpoints

### Request Validation
```typescript
// Use Zod for all input validation
const CreateBookSchema = z.object({
  title: z.string().min(1).max(500),
  author: z.string().max(200).optional(),
  category: z.enum(BOOK_CATEGORIES),
  visibility: z.enum(['public', 'private', 'friends']).default('private')
});
```

### Error Handling
```typescript
// Consistent error format
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [...],
    "requestId": "req_xxx",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Logging
```typescript
// Use structured logging with correlation
logger.info({
  requestId: request.id,
  userId: user?.id,
  action: 'book.created',
  bookId: book.id
}, 'Book created successfully');
```

## Security Guidelines

1. **Authentication**
   - JWT tokens (15min expiry)
   - Refresh tokens (7 day expiry, rotate on use)
   - API keys with hashed storage (Argon2)

2. **Authorization**
   - RBAC with roles: user, premium, moderator, admin, super_admin
   - Permission-based access control
   - Row-level security in queries

3. **Input Validation**
   - Validate ALL inputs with Zod
   - Sanitize file uploads
   - Rate limit all endpoints

4. **Audit Logging**
   - Log all mutations
   - Track IP, user agent, request ID
   - Send to Fabric for compliance

## Key Files

| File | Purpose |
|------|---------|
| `docs/ARCHITECTURE.md` | Full system architecture |
| `docs/PRD.md` | Product requirements |
| `docs/TDD.md` | Technical design |
| `openapi/api-v1.yaml` | API specification |
| `src/config/index.ts` | Configuration |
| `src/db/index.ts` | Database abstraction |
| `src/cache/index.ts` | Cache abstraction |

## Testing Strategy

```
Unit Tests (70%)       - Business logic, utilities
Integration Tests (20%) - API endpoints, database
E2E Tests (10%)        - Critical user flows
```

### Test Naming
```typescript
describe('BooksService', () => {
  describe('uploadBook', () => {
    it('should reject files exceeding size limit', async () => { ... });
    it('should detect duplicate files by hash', async () => { ... });
  });
});
```

## Event-Driven Processing

### Synchronous (Critical Path)
- Authentication
- Permission checks
- Book metadata retrieval
- Search queries

### Asynchronous (Event Hubs)
- Page image generation
- Thumbnail generation
- Text extraction
- Embedding generation
- Search indexing
- Analytics updates
- Email notifications

## Page Image Processing

### Overview
PDF books are converted to images at multiple resolutions for optimal reading experience across devices.

### Resolution Tiers
| Resolution | Width | Quality | Use Case |
|------------|-------|---------|----------|
| thumbnail  | 150px | 70%     | Navigation, grids |
| medium     | 800px | 85%     | Mobile reading |
| high-res   | 1600px| 92%     | Desktop reading |
| ultra      | 3200px| 95%     | Zoom, print, 4K |

### Key Files
| File | Purpose |
|------|---------|
| `src/services/pageImageService.ts` | Page extraction and rendering |
| `src/services/coverService.ts` | Cover management (auto/custom) |
| `src/workers/pageGenerationWorker.ts` | Background processing |

### Processing Flow
```
book.created → page_generation.queued → Worker processes pages → page_generation.completed
                                                              ↓
                                                    Auto-generates cover from page 1
                                                    Updates book thumbnail
```

### Storage Structure
```
books/{bookId}/pages/
├── thumb/{n}.jpg    # 150px
├── med/{n}.jpg      # 800px
├── high/{n}.jpg     # 1600px
└── ultra/{n}.jpg    # 3200px
```

### Implementation Notes
- Use `pdfjs-dist` with `node-canvas` for server-side PDF rendering
- Process pages in batches of 10 to manage memory
- Continue on individual page failures (partial success allowed)
- Auto-generate cover from page 1 unless custom cover uploaded
- Use signed URLs (1-hour expiry) for secure access
- Page images use immutable CDN caching (1 year TTL)

### API Endpoints
```
GET  /v1/books/{bookId}/pages              # List pages with URLs
GET  /v1/books/{bookId}/pages/{pageNumber} # Get specific page
POST /v1/books/{bookId}/pages/generate     # Trigger generation
GET  /v1/books/{bookId}/pages/status       # Generation progress
GET  /v1/books/{bookId}/cover              # Get cover URL
PUT  /v1/books/{bookId}/cover              # Upload custom cover
DELETE /v1/books/{bookId}/cover            # Remove custom cover
```

## Docker Deployment (CRITICAL)

**ALWAYS build Docker images with `--platform linux/amd64`** when deploying to Azure.

Mac (ARM64) → Azure (AMD64) requires cross-platform build:
```bash
docker build --platform linux/amd64 -t image:tag -f docker/Dockerfile .
```

This is already configured in `scripts/deploy-azure.sh`. If you ever build Docker images manually for Azure deployment, you MUST include the `--platform linux/amd64` flag or the container will fail with `exec format error`.

## Important Notes

1. **Never use Supabase directly** - Use the database abstraction layer
2. **Always validate inputs** - Use Zod schemas
3. **Include request IDs** - For tracing and debugging
4. **Use transactions** - For multi-document operations
5. **Cache strategically** - Don't over-cache, invalidate properly
6. **Log structured data** - For searchability in Fabric

## Related Documentation

- [ilm-red-unbound](../ilm-red-unbound/CLAUDE.md) - Frontend application
- [smart-search](../smart-search/README.md) - Search library
