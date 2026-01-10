# ILM Red API - Implementation Plan

## Document Information

| Field | Value |
|-------|-------|
| **Feature** | Page-First Reading + AI Chunks |
| **Last Updated** | 2026-01-09 |
| **Current Phase** | Phase 1 - Database Models |
| **Status** | In Progress |

---

## Overview

This document tracks the implementation of the Page-First Reading Platform with AI Chunks feature. The feature enables:

1. **Page Browsing** - Users can view PDF pages as images without downloading entire files
2. **AI Chunks** - Book text is chunked and embedded for semantic search
3. **RAG Integration** - AI chat includes relevant book context with page citations

---

## Core Principles

| # | Principle | Description |
|---|-----------|-------------|
| P1 | Pages are for **rendering** | Users browse visually through page images |
| P2 | Chunks are for **thinking** | AI uses text chunks for understanding |
| P3 | API orchestrates, storage serves | No large media streamed through API |
| P4 | Start simple, iterate fast | MVP first, enhance later |

---

## Progress

| Phase | Description | Status | Files |
|-------|-------------|--------|-------|
| 0 | Documentation | Completed | PRD.md, TDD.md, IMPLEMENTATION_PLAN.md, README.md, api-v1.yaml |
| 1 | Database Models & Migration | In Progress | `app/models/page.py`, migration |
| 2 | Schemas | Pending | `app/schemas/page.py` |
| 3 | PDF Processing Service | Pending | `app/services/pdf_processor.py` |
| 4 | Chunking Service | Pending | `app/services/chunking_service.py` |
| 5 | Page Service | Pending | `app/services/page_service.py` |
| 6 | Embedding Service | Pending | `app/services/embedding_service.py` |
| 7 | Page Repository | Pending | `app/repositories/page_repo.py` |
| 8 | API Endpoints | Pending | `app/api/v1/pages.py` |
| 9 | Chat RAG Integration | Pending | `app/services/chat_service.py` (modify) |
| 10 | Dependencies & Config | Pending | `pyproject.toml`, `app/config.py` |

---

## Phase Details

### Phase 0: Documentation (Completed)

- [x] Update PRD.md with Main Features table
- [x] Add FR-PAGE-007 (AI Text Chunks) requirements
- [x] Add FR-PAGE-008 (RAG Integration) requirements
- [x] Update TDD.md with Section 15: Page System Design
- [x] Create IMPLEMENTATION_PLAN.md
- [x] Update README.md with development status
- [x] Update openapi/api-v1.yaml with page endpoints

### Phase 1: Database Models & Migration

**Goal:** Create SQLAlchemy models and Alembic migration.

**Files:**
- `app/models/page.py` - PageImage and TextChunk models
- `app/db/migrations/versions/20260109_0006_pages_chunks.py` - Migration

**Models:**

```python
# PageImage - Stores page image metadata
class PageImage(Base):
    __tablename__ = "page_images"
    id: UUID
    book_id: UUID (FK → books)
    page_number: int
    width: int
    height: int
    thumbnail_path: str
    medium_path: str
    created_at: datetime

# TextChunk - Stores chunked text with embeddings
class TextChunk(Base):
    __tablename__ = "text_chunks"
    id: UUID
    book_id: UUID (FK → books)
    chunk_index: int
    text: str
    token_count: int
    page_start: int
    page_end: int
    embedding: Vector(1536)
    created_at: datetime
```

**Database Requirements:**
- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`

### Phase 2: Schemas

**Goal:** Create Pydantic request/response schemas.

**Files:**
- `app/schemas/page.py`
- `app/schemas/__init__.py` (modify)

**Schemas:**
- `PageMetadata` - Single page info
- `PageListResponse` - List of pages
- `PageDetailResponse` - Page with signed URLs
- `PageGenerationResponse` - Generation result
- `ChunkResponse` - Single chunk info
- `BookChunksResponse` - List of chunks

### Phase 3: PDF Processing Service

**Goal:** Extract pages and text from PDFs using PyMuPDF.

**Files:**
- `app/services/pdf_processor.py`

**Features:**
- Render page to JPEG at specified resolution
- Extract text from pages
- Pure Python (no system dependencies)

### Phase 4: Chunking Service

**Goal:** Split book text into AI-friendly chunks.

**Files:**
- `app/services/chunking_service.py`

**Parameters:**
- Max tokens: 500
- Overlap: 50 tokens
- Encoder: tiktoken cl100k_base

### Phase 5: Page Service

**Goal:** Orchestrate page generation and retrieval.

**Files:**
- `app/services/page_service.py`

**Methods:**
- `generate_pages_and_chunks(book_id)` - Main pipeline
- `get_page_list(book_id)` - List pages with thumbnails
- `get_page_detail(book_id, page_number)` - Get page URLs

### Phase 6: Embedding Service

**Goal:** Generate embeddings using OpenAI.

**Files:**
- `app/services/embedding_service.py`

**Model:** text-embedding-3-small (1536 dimensions)

### Phase 7: Page Repository

**Goal:** Data access layer for pages and chunks.

**Files:**
- `app/repositories/page_repo.py`
- `app/repositories/__init__.py` (modify)

**Methods:**
- CRUD for PageImage
- CRUD for TextChunk
- `search_similar_chunks(book_id, embedding, limit)` - pgvector search

### Phase 8: API Endpoints

**Goal:** Expose page functionality via REST API.

**Files:**
- `app/api/v1/pages.py`
- `app/api/v1/router.py` (modify)

**Endpoints:**
- `GET /v1/books/{bookId}/pages` - List pages
- `GET /v1/books/{bookId}/pages/{pageNumber}` - Get page detail
- `POST /v1/books/{bookId}/pages/generate` - Trigger generation

### Phase 9: Chat RAG Integration

**Goal:** Enhance chat with book context.

**Files:**
- `app/services/chat_service.py` (modify)

**Changes:**
- Add `get_book_context()` method
- Modify message handling to include RAG context
- Track RAG tokens in billing

### Phase 10: Dependencies & Config

**Goal:** Add required packages and configuration.

**Files:**
- `pyproject.toml` (add pymupdf, pgvector, tiktoken)
- `app/config.py` (add page settings)

**New Dependencies:**
```toml
pymupdf = "^1.24.0"
pgvector = "^0.2.4"
tiktoken = "^0.5.0"
```

---

## API Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/v1/books/{id}/pages` | List pages with thumbnail URLs |
| GET | `/v1/books/{id}/pages/{num}` | Get page with signed URLs |
| POST | `/v1/books/{id}/pages/generate` | Generate pages + chunks |

---

## MVP Scope

### In Scope
- PDF books only
- 2 image resolutions (thumbnail 150px, medium 800px)
- Synchronous generation (< 100 pages)
- AI chunks with embeddings (pgvector)
- Chat RAG integration
- Direct Azure Blob URLs (no CDN)

### Out of Scope (Future)
- EPUB/TXT support
- High-res/ultra resolutions
- CDN integration
- Background job queue
- Async generation progress

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Page generation | < 30s for 50-page PDF |
| Thumbnail load | < 200ms |
| RAG retrieval | < 500ms for 5 chunks |
| Embedding generation | < 2s per chunk |

---

## Deployment Verification

After each implementation phase:

### Local Verification
```bash
# 1. Install dependencies
poetry install

# 2. Run migrations
poetry run alembic upgrade head

# 3. Start server
./scripts/dev.sh

# 4. Verify Swagger
open http://localhost:8000/docs

# 5. Test endpoints
curl http://localhost:8000/v1/books/{book_id}/pages
```

### Azure Verification
```bash
# 1. Deploy
./scripts/deploy-azure.sh prod --app-only

# 2. Verify health
curl https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/health

# 3. Verify Swagger
open https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/docs
```

---

## Related Documentation

- [PRD.md](./PRD.md) - Product requirements (Section 4.11)
- [TDD.md](./TDD.md) - Technical design (Section 15)
- [OpenAPI](../openapi/api-v1.yaml) - API specification
