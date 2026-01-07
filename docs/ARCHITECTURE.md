# ILM Red API - Scalable Architecture Design

## Executive Summary

This document outlines a cloud-native, vendor-agnostic API architecture designed to scale from zero to hundreds of thousands of users and millions of books. The architecture leverages **Microsoft Fabric** as the preferred data platform while maintaining flexibility to use alternative providers.

---

## 1. Design Principles

### 1.1 Core Principles

| Principle | Description |
|-----------|-------------|
| **API-First** | All functionality exposed through well-documented REST/GraphQL APIs |
| **Vendor Agnostic** | Abstract data layer to swap providers (no Supabase/Localbase lock-in) |
| **Horizontal Scalability** | Stateless services that scale independently |
| **Event-Driven** | Async processing for non-critical operations |
| **Multi-Tenancy Ready** | Architecture supports B2B SaaS model |
| **Zero-Trust Security** | JWT-based auth, API keys, rate limiting |

### 1.2 Scale Targets

| Metric | Target |
|--------|--------|
| Concurrent Users | 100,000+ |
| Total Users | 500,000+ |
| Books in Catalog | 10,000,000+ |
| API Requests/sec | 50,000+ |
| File Storage | 100+ TB |
| Search Latency | < 100ms (p99) |
| API Latency | < 200ms (p99) |

---

## 2. Technology Stack

### 2.1 Microsoft Fabric Core Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MICROSOFT FABRIC                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │   OneLake       │  │  Data Factory   │  │   Synapse       │              │
│  │ (Data Lake)     │  │  (ETL/ELT)      │  │  (Analytics)    │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Lakehouse      │  │  Data Warehouse │  │  Real-Time      │              │
│  │  (Delta Lake)   │  │  (SQL Endpoint) │  │  Intelligence   │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │  Power BI       │  │  Data Activator │  │  Notebooks      │              │
│  │  (Reporting)    │  │  (Alerts)       │  │  (ML/AI)        │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Complete Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **API Gateway** | Azure API Management | Rate limiting, auth, routing |
| **Compute** | Azure Container Apps / AKS | Stateless API services |
| **Primary Database** | Azure Cosmos DB (NoSQL) | User data, books, clubs |
| **Search** | Azure AI Search | Full-text, vector, semantic |
| **Cache** | Azure Cache for Redis | Session, hot data, rate limits |
| **File Storage** | Azure Blob Storage + CDN | Books, thumbnails, assets |
| **Analytics** | Microsoft Fabric Lakehouse | Delta Lake for analytics |
| **Events** | Azure Event Hubs | Async event processing |
| **AI/ML** | Azure OpenAI + AI Services | Chat, embeddings, OCR |
| **Auth** | Azure AD B2C / Entra ID | OAuth 2.0, SSO |
| **Monitoring** | Azure Monitor + App Insights | Logging, metrics, tracing |

### 2.3 Vendor-Agnostic Alternatives

| Component | Microsoft | Alternative 1 | Alternative 2 |
|-----------|-----------|---------------|---------------|
| Database | Cosmos DB | PostgreSQL | MongoDB Atlas |
| Search | AI Search | Elasticsearch | Meilisearch |
| Cache | Azure Redis | Upstash Redis | DragonflyDB |
| Storage | Blob Storage | AWS S3 | MinIO |
| Events | Event Hubs | Kafka | RabbitMQ |
| Analytics | Fabric | Databricks | Snowflake |

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
                                    ┌─────────────────┐
                                    │   CDN (Azure)   │
                                    │   Akamai/CF     │
                                    └────────┬────────┘
                                             │
                    ┌────────────────────────┼────────────────────────┐
                    │                        │                        │
                    ▼                        ▼                        ▼
            ┌───────────────┐        ┌───────────────┐        ┌───────────────┐
            │  Web Clients  │        │ Mobile Apps   │        │  3rd Party    │
            │  (React SPA)  │        │ (iOS/Android) │        │  Integrations │
            └───────────────┘        └───────────────┘        └───────────────┘
                    │                        │                        │
                    └────────────────────────┼────────────────────────┘
                                             │
                                             ▼
                              ┌──────────────────────────┐
                              │     API Gateway          │
                              │  (Azure API Management)  │
                              │  - Rate Limiting         │
                              │  - Auth Validation       │
                              │  - Request Routing       │
                              │  - API Versioning        │
                              └────────────┬─────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │                      │                      │
                    ▼                      ▼                      ▼
         ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
         │  Auth Service    │   │  Core API        │   │  AI Service      │
         │  - OAuth 2.0     │   │  - Books CRUD    │   │  - Chat          │
         │  - JWT Tokens    │   │  - Users         │   │  - Embeddings    │
         │  - RBAC          │   │  - Clubs         │   │  - Analysis      │
         └────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
                  │                      │                      │
                  └──────────────────────┼──────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │   Cosmos DB     │       │  Azure AI       │       │  Azure Blob     │
    │   (Primary DB)  │       │  Search         │       │  Storage        │
    └─────────────────┘       └─────────────────┘       └─────────────────┘
              │                          │                          │
              └──────────────────────────┼──────────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │   Azure Redis       │
                              │   Cache             │
                              └─────────────────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │   Event Hubs        │
                              │   (Async Events)    │
                              └──────────┬──────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
    ┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
    │  Analytics      │       │  Notifications  │       │  Background     │
    │  Worker         │       │  Worker         │       │  Jobs           │
    └─────────────────┘       └─────────────────┘       └─────────────────┘
              │
              ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                     MICROSOFT FABRIC                             │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
    │  │  OneLake    │  │  Lakehouse  │  │  Power BI   │              │
    │  │  (Raw Data) │  │  (Delta)    │  │  (Reports)  │              │
    │  └─────────────┘  └─────────────┘  └─────────────┘              │
    └─────────────────────────────────────────────────────────────────┘
```

### 3.2 Service Decomposition

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          API SERVICES                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   Auth      │ │   Books     │ │   Users     │ │   Clubs     │       │
│  │   Service   │ │   Service   │ │   Service   │ │   Service   │       │
│  │             │ │             │ │             │ │             │       │
│  │ /auth/*     │ │ /books/*    │ │ /users/*    │ │ /clubs/*    │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │   Search    │ │   AI Chat   │ │   Files     │ │   Admin     │       │
│  │   Service   │ │   Service   │ │   Service   │ │   Service   │       │
│  │             │ │             │ │             │ │             │       │
│  │ /search/*   │ │ /ai/*       │ │ /files/*    │ │ /admin/*    │       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐       │
│  │  Progress   │ │  Billing    │ │ Gamification│ │  Analytics  │       │
│  │  Service    │ │  Service    │ │  Service    │ │  Service    │       │
│  │             │ │             │ │             │ │             │       │
│  │ /progress/* │ │ /billing/*  │ │ /ranking/*  │ │ /analytics/*│       │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Data Architecture

### 4.1 Database Strategy

#### 4.1.1 Azure Cosmos DB (Operational Data)

**Why Cosmos DB:**
- Global distribution for low-latency worldwide
- Auto-scaling from 0 to millions of RU/s
- Multi-model (Document, Graph, Key-Value)
- 99.999% SLA for high availability
- Built-in vector search for AI applications

**Container Design:**

```javascript
// Partition Strategy
{
  "containers": {
    "users": {
      "partitionKey": "/userId",
      "indexes": ["email", "username", "createdAt"]
    },
    "books": {
      "partitionKey": "/ownerId",  // Co-locate books with owner
      "indexes": ["title", "author", "category", "visibility"]
    },
    "bookClubs": {
      "partitionKey": "/clubId",
      "indexes": ["ownerId", "visibility", "name"]
    },
    "clubMembers": {
      "partitionKey": "/clubId",  // Co-locate with club
      "indexes": ["userId", "role", "joinedAt"]
    },
    "progress": {
      "partitionKey": "/userId",  // User-centric queries
      "indexes": ["bookId", "lastReadAt"]
    },
    "aiSessions": {
      "partitionKey": "/userId",
      "ttl": 2592000  // 30-day auto-delete
    }
  }
}
```

**Sample Document Structure:**

```json
// Book Document
{
  "id": "book_uuid",
  "ownerId": "user_uuid",
  "type": "book",
  "title": "Introduction to AI",
  "author": "John Smith",
  "description": "A comprehensive guide...",
  "category": "Technology",
  "language": "en",
  "visibility": "public",
  "fileInfo": {
    "path": "books/user_uuid/book_uuid.pdf",
    "size": 15728640,
    "mimeType": "application/pdf",
    "sha256": "abc123..."
  },
  "metadata": {
    "pageCount": 350,
    "isbn": "978-0-123456-78-9",
    "publisher": "TechBooks Inc",
    "publishedYear": 2024
  },
  "thumbnailUrl": "https://cdn.../thumb.jpg",
  "stats": {
    "viewCount": 1523,
    "favoriteCount": 89,
    "ratingSum": 356,
    "ratingCount": 82
  },
  "aiEnabled": true,
  "embeddings": [0.123, 0.456, ...],  // Vector for semantic search
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-06-20T15:45:00Z"
}
```

#### 4.1.2 Microsoft Fabric (Analytics)

**Data Flow to Fabric:**

```
Cosmos DB ──► Change Feed ──► Event Hubs ──► Data Factory ──► OneLake
                                                                  │
                                                                  ▼
                                                            ┌─────────────┐
                                                            │  Lakehouse  │
                                                            │  (Delta)    │
                                                            └──────┬──────┘
                                                                   │
                              ┌────────────────────────────────────┼────────────┐
                              │                                    │            │
                              ▼                                    ▼            ▼
                       ┌─────────────┐                    ┌─────────────┐ ┌──────────┐
                       │   Synapse   │                    │  Power BI   │ │   ML     │
                       │   Analytics │                    │  Dashboards │ │ Notebooks│
                       └─────────────┘                    └─────────────┘ └──────────┘
```

**Delta Lake Tables:**

```sql
-- Books Fact Table (append-only, partitioned)
CREATE TABLE bronze.books_events (
    event_id STRING,
    event_type STRING,  -- 'created', 'updated', 'deleted', 'viewed'
    book_id STRING,
    user_id STRING,
    timestamp TIMESTAMP,
    payload STRING  -- JSON
)
USING DELTA
PARTITIONED BY (date(timestamp))
TBLPROPERTIES (delta.autoOptimize.optimizeWrite = true);

-- Silver Layer (curated)
CREATE TABLE silver.books (
    book_id STRING,
    owner_id STRING,
    title STRING,
    author STRING,
    category STRING,
    visibility STRING,
    view_count BIGINT,
    favorite_count BIGINT,
    rating_avg DOUBLE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
USING DELTA;

-- Gold Layer (aggregated)
CREATE TABLE gold.daily_book_stats (
    date DATE,
    category STRING,
    new_books BIGINT,
    total_views BIGINT,
    unique_readers BIGINT,
    avg_reading_time_minutes DOUBLE
)
USING DELTA;
```

### 4.2 Search Architecture

#### 4.2.1 Azure AI Search

**Index Configuration:**

```json
{
  "name": "books-index",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true},
    {"name": "title", "type": "Edm.String", "searchable": true, "analyzer": "standard.lucene"},
    {"name": "author", "type": "Edm.String", "searchable": true, "filterable": true},
    {"name": "description", "type": "Edm.String", "searchable": true},
    {"name": "category", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "language", "type": "Edm.String", "filterable": true},
    {"name": "visibility", "type": "Edm.String", "filterable": true},
    {"name": "ownerId", "type": "Edm.String", "filterable": true},
    {"name": "viewCount", "type": "Edm.Int64", "sortable": true},
    {"name": "rating", "type": "Edm.Double", "sortable": true},
    {"name": "contentVector", "type": "Collection(Edm.Single)",
     "dimensions": 1536, "vectorSearchProfile": "default"}
  ],
  "vectorSearch": {
    "profiles": [{"name": "default", "algorithm": "hnsw"}],
    "algorithms": [{"name": "hnsw", "kind": "hnsw",
                   "hnswParameters": {"m": 4, "efConstruction": 400, "efSearch": 500}}]
  },
  "semantic": {
    "configurations": [{
      "name": "semantic-config",
      "prioritizedFields": {
        "titleField": {"fieldName": "title"},
        "contentFields": [{"fieldName": "description"}],
        "keywordsFields": [{"fieldName": "author"}, {"fieldName": "category"}]
      }
    }]
  }
}
```

### 4.3 Caching Strategy

#### 4.3.1 Cache Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CACHING ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  L1: In-Memory (Service)     L2: Redis           L3: Database               │
│  ┌─────────────────────┐     ┌─────────────────┐  ┌─────────────────┐       │
│  │ - Request scope     │ ──► │ - Session data  │ ─►│ - Source of     │       │
│  │ - 100ms TTL         │     │ - Hot data      │  │   truth         │       │
│  │ - LRU eviction      │     │ - 5-60min TTL   │  │ - Persistent    │       │
│  └─────────────────────┘     └─────────────────┘  └─────────────────┘       │
│                                                                              │
│  Cache Key Patterns:                                                         │
│  - user:{userId}:profile                                                     │
│  - book:{bookId}:metadata                                                    │
│  - book:{bookId}:stats                                                       │
│  - search:{queryHash}:results                                                │
│  - club:{clubId}:members                                                     │
│  - rate:{userId}:api:{minute}                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.3.2 Cache Invalidation

```javascript
// Event-driven invalidation
const cacheInvalidation = {
  "book.updated": ["book:{bookId}:*", "search:*"],
  "book.deleted": ["book:{bookId}:*", "user:{ownerId}:books", "search:*"],
  "user.updated": ["user:{userId}:*"],
  "club.memberAdded": ["club:{clubId}:members", "user:{userId}:clubs"],
  "rating.created": ["book:{bookId}:stats"]
};
```

### 4.4 File Storage Architecture

#### 4.4.1 Azure Blob Storage Structure

```
ilm-red-storage/
├── books/
│   └── {userId}/
│       └── {bookId}/
│           ├── source.pdf                  # Original uploaded file
│           ├── source.epub                 # Or other formats
│           ├── cover.jpg                   # Auto-generated from page 1
│           ├── cover-custom.{ext}          # User-uploaded custom cover
│           ├── thumbnail.jpg               # 150px thumbnail for lists
│           ├── text/
│           │   ├── extracted.txt           # Full text extraction
│           │   └── chunks.json             # Chunked text for AI context
│           └── pages/
│               ├── thumb/                  # 150px width - navigation
│               │   ├── 1.jpg
│               │   ├── 2.jpg
│               │   └── ...
│               ├── med/                    # 800px width - mobile
│               │   ├── 1.jpg
│               │   ├── 2.jpg
│               │   └── ...
│               ├── high/                   # 1600px width - desktop
│               │   ├── 1.jpg
│               │   ├── 2.jpg
│               │   └── ...
│               └── ultra/                  # 3200px width - zoom/print
│                   ├── 1.jpg
│                   ├── 2.jpg
│                   └── ...
├── avatars/
│   └── {userId}/
│       └── avatar.{ext}
└── clubs/
    └── {clubId}/
        └── cover.{ext}
```

#### 4.4.2 Storage Tiers & Lifecycle Policies

```json
{
  "rules": [
    {
      "name": "page-images-hot",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "prefixMatch": ["books/"],
          "blobTypes": ["blockBlob"],
          "blobIndexMatch": [
            {"name": "ContentType", "op": "==", "value": "image/jpeg"}
          ]
        },
        "actions": {
          "baseBlob": {
            "tierToCool": {"daysAfterLastAccessTimeGreaterThan": 90},
            "tierToArchive": {"daysAfterLastAccessTimeGreaterThan": 365}
          }
        }
      }
    },
    {
      "name": "source-files-archive",
      "enabled": true,
      "type": "Lifecycle",
      "definition": {
        "filters": {
          "prefixMatch": ["books/"],
          "blobTypes": ["blockBlob"],
          "blobIndexMatch": [
            {"name": "FileType", "op": "==", "value": "source"}
          ]
        },
        "actions": {
          "baseBlob": {
            "tierToCool": {"daysAfterLastAccessTimeGreaterThan": 30},
            "tierToArchive": {"daysAfterLastAccessTimeGreaterThan": 180}
          }
        }
      }
    }
  ]
}
```

#### 4.4.3 CDN Configuration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CDN CACHING STRATEGY                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Page Images (*/pages/*):                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Cache-Control: public, max-age=31536000, immutable                 │    │
│  │  TTL: 1 year (content-addressed, never changes)                     │    │
│  │  Edge Locations: All Azure CDN POPs                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Thumbnails (*/thumbnail.jpg):                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Cache-Control: public, max-age=86400                               │    │
│  │  TTL: 24 hours (may be regenerated)                                 │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Covers (*/cover*.jpg):                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Cache-Control: public, max-age=3600                                │    │
│  │  TTL: 1 hour (user may upload custom)                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Source Files (*/source.*):                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Cache-Control: private, no-cache                                   │    │
│  │  Access: Signed URLs only (1-hour expiry)                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 4.4.4 Signed URL Generation

```typescript
// Secure access to files via SAS tokens
interface SignedUrlOptions {
  expiresIn: number;        // seconds
  permissions: 'r' | 'rw';
  ipRange?: string;         // optional IP restriction
}

async function getSignedUrl(
  blobPath: string,
  options: SignedUrlOptions
): Promise<string> {
  const sasToken = generateSasToken({
    containerName: 'ilm-red-storage',
    blobName: blobPath,
    permissions: options.permissions,
    expiresOn: addSeconds(new Date(), options.expiresIn),
    startsOn: new Date(),
    ipRange: options.ipRange
  });

  return `https://ilmred.blob.core.windows.net/ilm-red-storage/${blobPath}?${sasToken}`;
}

// URL Expiry by Content Type
const URL_EXPIRY = {
  pageImages: 3600,        // 1 hour (cached at CDN anyway)
  sourceFile: 3600,        // 1 hour for downloads
  coverUpload: 600,        // 10 min for upload operations
};
```

---

## 5. API Design

### 5.1 API Versioning Strategy

```
Base URL: https://api.ilm-red.com/v1

Versioning: URL-based (/v1, /v2)
Deprecation: 12-month notice with sunset headers
```

### 5.2 Authentication Flow

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Client    │     │   API Gateway   │     │   Auth Service  │
└──────┬──────┘     └────────┬────────┘     └────────┬────────┘
       │                     │                       │
       │  POST /auth/login   │                       │
       │────────────────────►│                       │
       │                     │  Validate Credentials │
       │                     │──────────────────────►│
       │                     │                       │
       │                     │  JWT + Refresh Token  │
       │                     │◄──────────────────────│
       │  {access, refresh}  │                       │
       │◄────────────────────│                       │
       │                     │                       │
       │  GET /books         │                       │
       │  Authorization: Bearer {jwt}                │
       │────────────────────►│                       │
       │                     │  Validate JWT         │
       │                     │──────────────────────►│
       │                     │  {valid, claims}      │
       │                     │◄──────────────────────│
       │  {books: [...]}     │                       │
       │◄────────────────────│                       │
```

### 5.3 Rate Limiting

| Tier | Requests/min | Burst | AI Tokens/day |
|------|--------------|-------|---------------|
| Free | 60 | 100 | 10,000 |
| Premium | 300 | 500 | 100,000 |
| Enterprise | 1,000 | 2,000 | Unlimited |

### 5.4 Error Response Format

```json
{
  "error": {
    "code": "BOOK_NOT_FOUND",
    "message": "The requested book does not exist or you don't have access",
    "details": {
      "bookId": "abc123",
      "reason": "deleted"
    },
    "requestId": "req_xyz789",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

---

## 6. Scalability Patterns

### 6.1 Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AUTO-SCALING CONFIGURATION                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  API Services (Container Apps):                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Min Replicas: 2                                                     │    │
│  │  Max Replicas: 100                                                   │    │
│  │  Scale Rules:                                                        │    │
│  │    - HTTP Requests > 100/sec → Scale Up                              │    │
│  │    - CPU > 70% → Scale Up                                            │    │
│  │    - Memory > 80% → Scale Up                                         │    │
│  │  Scale Down: 5 min cooldown                                          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Database (Cosmos DB):                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Provisioned Mode: 10,000 - 1,000,000 RU/s                           │    │
│  │  Autoscale: Enabled with max RU/s                                    │    │
│  │  Global Distribution: East US, West Europe, Southeast Asia           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Search (Azure AI Search):                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Tier: Standard S2 (scalable)                                        │    │
│  │  Replicas: 2-12 (auto-scale based on QPS)                            │    │
│  │  Partitions: 1-12 (manual based on index size)                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Event-Driven Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVENT-DRIVEN PROCESSING                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Synchronous (Critical Path):                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • User authentication                                               │    │
│  │  • Book metadata retrieval                                           │    │
│  │  • Permission checks                                                 │    │
│  │  • Search queries                                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Asynchronous (Background):                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  Events:                              Workers:                       │    │
│  │  • book.uploaded          ────►       Text Extractor                 │    │
│  │  • book.uploaded          ────►       Embedding Generator            │    │
│  │  • book.uploaded          ────►       Search Indexer                 │    │
│  │  • book.uploaded          ────►       Page Generation Trigger        │    │
│  │  • pages.generation.queued ────►      Page Image Worker              │    │
│  │  • pages.generation.completed ────►   Thumbnail Updater              │    │
│  │  • book.cover.updated     ────►       CDN Cache Invalidator          │    │
│  │  • user.action            ────►       Analytics Writer               │    │
│  │  • ai.chat                ────►       Billing Calculator             │    │
│  │  • club.invite            ────►       Email Sender                   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 CQRS Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMMAND QUERY RESPONSIBILITY SEGREGATION                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Commands (Write Path):                 Queries (Read Path):                 │
│  ┌─────────────────────────┐           ┌─────────────────────────┐          │
│  │  POST /books            │           │  GET /books             │          │
│  │  PUT /books/{id}        │           │  GET /books/{id}        │          │
│  │  DELETE /books/{id}     │           │  GET /search            │          │
│  │         │               │           │         │               │          │
│  │         ▼               │           │         ▼               │          │
│  │  ┌─────────────┐        │           │  ┌─────────────┐        │          │
│  │  │ Cosmos DB   │        │           │  │ Redis Cache │        │          │
│  │  │ (Write)     │        │           │  │ AI Search   │        │          │
│  │  └──────┬──────┘        │           │  └─────────────┘        │          │
│  │         │               │           │                         │          │
│  │         ▼               │           │                         │          │
│  │  ┌─────────────┐        │           │                         │          │
│  │  │ Event Hub   │ ─────────────────────► Sync to Read Store    │          │
│  │  └─────────────┘        │           │                         │          │
│  └─────────────────────────┘           └─────────────────────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Security Architecture

### 7.1 Defense in Depth

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SECURITY LAYERS                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Layer 1: Edge Security                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • Azure Front Door (DDoS protection)                                │    │
│  │  • Web Application Firewall (WAF)                                    │    │
│  │  • TLS 1.3 encryption                                                │    │
│  │  • Geographic restrictions                                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Layer 2: API Gateway                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • JWT validation                                                    │    │
│  │  • API key authentication                                            │    │
│  │  • Rate limiting per user/IP                                         │    │
│  │  • Request/response validation                                       │    │
│  │  • IP allowlisting for admin APIs                                    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Layer 3: Application                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • Input validation (Zod schemas)                                    │    │
│  │  • Output encoding                                                   │    │
│  │  • RBAC permission checks                                            │    │
│  │  • Audit logging                                                     │    │
│  │  • Secrets in Azure Key Vault                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  Layer 4: Data                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  • Encryption at rest (AES-256)                                      │    │
│  │  • Encryption in transit (TLS)                                       │    │
│  │  • Row-level security in queries                                     │    │
│  │  • PII data masking                                                  │    │
│  │  • Data residency compliance                                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Authentication & Authorization

```typescript
// JWT Token Structure
interface JWTPayload {
  sub: string;          // User ID
  email: string;
  roles: string[];      // ['user', 'premium', 'admin']
  permissions: string[]; // ['books:read', 'books:write', ...]
  iat: number;          // Issued at
  exp: number;          // Expires (15 min for access, 7 days for refresh)
  iss: string;          // Issuer
  aud: string;          // Audience
}

// RBAC Permission Matrix
const permissions = {
  'user': ['books:read:own', 'books:write:own', 'progress:*'],
  'premium': ['...user', 'ai:chat', 'clubs:create'],
  'moderator': ['...premium', 'books:read:all', 'reports:view'],
  'admin': ['...moderator', 'users:manage', 'system:config'],
  'super_admin': ['*']
};
```

---

## 8. Deployment Architecture

### 8.1 Multi-Region Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       GLOBAL DEPLOYMENT TOPOLOGY                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                        ┌─────────────────┐                                   │
│                        │  Azure Traffic  │                                   │
│                        │  Manager        │                                   │
│                        │  (Global LB)    │                                   │
│                        └────────┬────────┘                                   │
│                                 │                                            │
│         ┌───────────────────────┼───────────────────────┐                   │
│         │                       │                       │                   │
│         ▼                       ▼                       ▼                   │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│  │  East US    │         │ West Europe │         │ SE Asia     │           │
│  │  (Primary)  │         │ (Secondary) │         │ (Secondary) │           │
│  └──────┬──────┘         └──────┬──────┘         └──────┬──────┘           │
│         │                       │                       │                   │
│         ▼                       ▼                       ▼                   │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│  │ Container   │         │ Container   │         │ Container   │           │
│  │ Apps Env    │         │ Apps Env    │         │ Apps Env    │           │
│  └─────────────┘         └─────────────┘         └─────────────┘           │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    COSMOS DB (Global Distribution)                   │    │
│  │  Write Region: East US                                               │    │
│  │  Read Regions: West Europe, SE Asia                                  │    │
│  │  Consistency: Session (default), Strong (for critical ops)          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 CI/CD Pipeline

```yaml
# Azure DevOps / GitHub Actions
stages:
  - name: Build
    steps:
      - lint & type-check
      - unit tests
      - build container images
      - security scan (Trivy)

  - name: Test
    steps:
      - deploy to staging
      - integration tests
      - load tests (k6)
      - security tests (OWASP ZAP)

  - name: Deploy
    steps:
      - blue-green deployment
      - smoke tests
      - gradual traffic shift (10% → 50% → 100%)
      - automatic rollback on errors
```

---

## 9. Monitoring & Observability

### 9.1 Observability Stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        OBSERVABILITY ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Azure Application Insights                        │    │
│  │  • Distributed tracing (correlation IDs)                             │    │
│  │  • Request/dependency tracking                                       │    │
│  │  • Live metrics stream                                               │    │
│  │  • Smart detection (anomaly detection)                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Azure Monitor                                     │    │
│  │  • Metrics: CPU, memory, requests, latency                           │    │
│  │  • Alerts: Threshold-based, dynamic thresholds                       │    │
│  │  • Dashboards: Real-time operational views                           │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Log Analytics                                     │    │
│  │  • Centralized logging (KQL queries)                                 │    │
│  │  • Log-based alerts                                                  │    │
│  │  • Retention: 90 days (hot), 2 years (archive)                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Microsoft Fabric                                  │    │
│  │  • Business metrics and KPIs                                         │    │
│  │  • Usage analytics                                                   │    │
│  │  • Power BI dashboards                                               │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Key Metrics (SLIs)

| Category | Metric | Target |
|----------|--------|--------|
| Availability | API Uptime | 99.9% |
| Latency | P50 Response Time | < 100ms |
| Latency | P99 Response Time | < 500ms |
| Error Rate | 5xx Errors | < 0.1% |
| Throughput | Requests/sec | 10,000+ |
| Search | Query Latency P99 | < 200ms |
| AI | Chat Response Time | < 3s |

---

## 10. Cost Optimization

### 10.1 Cost Model

| Component | Scaling Factor | Optimization Strategy |
|-----------|----------------|----------------------|
| Cosmos DB | RU/s consumed | Reserved capacity, autoscale |
| Container Apps | vCPU hours | Scale to zero, spot instances |
| AI Search | Documents indexed | Tiered indexing, archive old |
| Blob Storage | TB stored | Lifecycle policies, tiers |
| AI (OpenAI) | Tokens consumed | Caching, prompt optimization |
| Event Hubs | Throughput units | Batch events, compression |

### 10.2 Estimated Monthly Costs

| Scale | Users | Books | Est. Cost/month |
|-------|-------|-------|-----------------|
| Startup | 1,000 | 10,000 | $500-1,000 |
| Growth | 50,000 | 500,000 | $5,000-10,000 |
| Scale | 500,000 | 5,000,000 | $30,000-50,000 |
| Enterprise | 500,000+ | 10,000,000+ | Custom |

---

## 11. Migration Strategy

### 11.1 Supabase to Azure Migration

```
Phase 1: Setup (Week 1-2)
├── Provision Azure resources
├── Set up networking and security
├── Configure CI/CD pipelines
└── Deploy API services (staging)

Phase 2: Data Migration (Week 3-4)
├── Export Supabase data
├── Transform to Cosmos DB format
├── Import to Cosmos DB
├── Verify data integrity
└── Migrate files to Blob Storage

Phase 3: Parallel Running (Week 5-6)
├── Run both systems in parallel
├── Sync writes to both databases
├── Validate consistency
└── Performance testing

Phase 4: Cutover (Week 7-8)
├── DNS cutover to Azure
├── Monitor closely
├── Decommission Supabase
└── Documentation and training
```

---

## 12. Appendix

### A. Glossary

| Term | Definition |
|------|------------|
| RU/s | Request Units per second (Cosmos DB throughput) |
| CQRS | Command Query Responsibility Segregation |
| Delta Lake | Open-source storage layer for data lakes |
| OneLake | Microsoft Fabric's unified data lake |
| HNSW | Hierarchical Navigable Small World (vector search algorithm) |

### B. References

- [Microsoft Fabric Documentation](https://learn.microsoft.com/fabric/)
- [Azure Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/)
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [OpenAPI 3.1 Specification](https://spec.openapis.org/oas/v3.1.0)
