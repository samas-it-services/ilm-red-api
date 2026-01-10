# ILM Red Admin API Documentation

**Version:** 1.1.0
**Date:** 2026-01-10
**Status:** Production
**Base URL:** `https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [User Management API](#3-user-management-api)
4. [Book Management API](#4-book-management-api)
5. [Chat Session Management API](#5-chat-session-management-api)
6. [Cache Management API](#6-cache-management-api)
7. [System Statistics API](#7-system-statistics-api)
8. [Error Handling](#8-error-handling)
9. [Rate Limits](#9-rate-limits)
10. [Webhooks](#10-webhooks)
11. [SDK Examples](#11-sdk-examples)

---

## 1. Overview

### 1.1 Purpose

The ILM Red Admin API provides administrative capabilities for managing users, books, chat sessions, and system resources. It is designed for:

- **System Administrators** - Full platform management
- **Content Moderators** - User and content moderation
- **Support Staff** - User assistance and issue resolution
- **DevOps Engineers** - System monitoring and cache management

### 1.2 Admin Panel Features

| Feature | Description | Endpoint Prefix |
|---------|-------------|-----------------|
| **User Management** | List, view, edit, disable users | `/v1/admin/users` |
| **Book Management** | View all books, trigger processing | `/v1/admin/books` |
| **Chat Management** | View and delete chat sessions | `/v1/admin/chats` |
| **Cache Management** | Redis stats, invalidation, flush | `/v1/cache` |
| **System Statistics** | Dashboard metrics | `/v1/admin/stats` |

### 1.3 API Documentation

| Documentation | URL |
|---------------|-----|
| **Admin Swagger UI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/admin/docs |
| **Main Swagger UI** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/docs |
| **OpenAPI JSON** | https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/openapi.json |

---

## 2. Authentication & Authorization

### 2.1 Requirements

All admin endpoints require:
1. **Valid JWT Token** - Bearer authentication
2. **Admin Role** - User must have `admin` or `super_admin` role

### 2.2 Authorization Header

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2.3 Role Hierarchy

| Role | User Mgmt | Book Mgmt | Chat Mgmt | Cache | Stats |
|------|-----------|-----------|-----------|-------|-------|
| `user` | - | - | - | - | - |
| `moderator` | Read | Read | Read/Delete | - | Read |
| `admin` | Read/Write | Read/Write | Read/Delete | Read | Read |
| `super_admin` | Full | Full | Full | Full | Full |

### 2.4 Error Responses

```json
// 401 Unauthorized - Invalid or expired token
{
  "detail": "Could not validate credentials"
}

// 403 Forbidden - Insufficient permissions
{
  "detail": "Admin access required"
}
```

---

## 3. User Management API

### 3.1 List Users

Retrieve a paginated list of all users with optional filtering.

```http
GET /v1/admin/users
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |
| `search` | string | - | Search by email, username, display_name |
| `status` | string | - | Filter by status: `active`, `suspended`, `deleted` |
| `role` | string | - | Filter by role: `user`, `admin`, etc. |
| `sort` | string | `-created_at` | Sort field (prefix `-` for desc) |

**Response:**

```json
{
  "data": [
    {
      "id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
      "email": "user@example.com",
      "username": "johndoe",
      "display_name": "John Doe",
      "avatar_url": null,
      "bio": "Book enthusiast",
      "roles": ["user"],
      "status": "active",
      "extra_data": {
        "full_name": "John Michael Doe",
        "city": "San Francisco",
        "country": "USA"
      },
      "created_at": "2026-01-10T10:30:00Z",
      "updated_at": "2026-01-10T15:45:00Z",
      "last_login_at": "2026-01-10T14:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20,
  "total_pages": 8
}
```

### 3.2 Get User Details

Retrieve detailed information about a specific user.

```http
GET /v1/admin/users/{user_id}
```

**Response:**

```json
{
  "id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
  "email": "user@example.com",
  "username": "johndoe",
  "display_name": "John Doe",
  "avatar_url": null,
  "bio": "Book enthusiast",
  "roles": ["user"],
  "status": "active",
  "extra_data": {
    "full_name": "John Michael Doe",
    "city": "San Francisco",
    "state_province": "California",
    "country": "USA",
    "date_of_birth": "1990-05-15"
  },
  "preferences": {
    "theme": "dark",
    "language": "en",
    "notifications": {
      "email": true,
      "push": true
    }
  },
  "stats": {
    "books_uploaded": 12,
    "books_read": 45,
    "chat_sessions": 23,
    "total_ai_tokens": 150000
  },
  "created_at": "2026-01-10T10:30:00Z",
  "updated_at": "2026-01-10T15:45:00Z",
  "last_login_at": "2026-01-10T14:00:00Z"
}
```

### 3.3 Update User

Update user information including roles and status.

```http
PATCH /v1/admin/users/{user_id}
```

**Request Body:**

```json
{
  "display_name": "John Doe Updated",
  "roles": ["user", "moderator"],
  "status": "active",
  "extra_data": {
    "notes": "Promoted to moderator on 2026-01-10"
  }
}
```

**Response:** Returns updated user object.

### 3.4 Disable User

Disable a user account (soft delete).

```http
POST /v1/admin/users/{user_id}/disable
```

**Request Body:**

```json
{
  "reason": "Violation of terms of service",
  "notify_user": true
}
```

**Response:**

```json
{
  "success": true,
  "message": "User disabled successfully",
  "user_id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad"
}
```

---

## 4. Book Management API

### 4.1 List All Books

Retrieve all books across all users with filtering options.

```http
GET /v1/admin/books
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page (max 100) |
| `search` | string | - | Search by title, author |
| `status` | string | - | `pending`, `processing`, `ready`, `failed` |
| `category` | string | - | Filter by category |
| `visibility` | string | - | `public`, `private` |
| `owner_id` | string | - | Filter by owner |

**Response:**

```json
{
  "data": [
    {
      "id": "e6142920-cc96-42f8-a950-265bf9e7890e",
      "title": "Introduction to Machine Learning",
      "author": "Jane Smith",
      "description": "A comprehensive guide...",
      "category": "technology",
      "visibility": "public",
      "owner_id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
      "owner_name": "John Doe",
      "page_count": 350,
      "processing_status": "ready",
      "cover_url": "https://storage.../covers/e6142920.jpg",
      "average_rating": 4.5,
      "ratings_count": 23,
      "created_at": "2026-01-10T10:30:00Z"
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 20,
  "total_pages": 25
}
```

### 4.2 Get Book Details

Retrieve detailed book information including processing status.

```http
GET /v1/admin/books/{book_id}
```

**Response:**

```json
{
  "id": "e6142920-cc96-42f8-a950-265bf9e7890e",
  "title": "Introduction to Machine Learning",
  "author": "Jane Smith",
  "description": "A comprehensive guide to ML concepts...",
  "category": "technology",
  "visibility": "public",
  "owner": {
    "id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
    "username": "johndoe",
    "display_name": "John Doe"
  },
  "file": {
    "path": "books/62e6c9ad/e6142920.pdf",
    "size_bytes": 15728640,
    "mime_type": "application/pdf",
    "sha256": "abc123def456..."
  },
  "processing": {
    "status": "ready",
    "pages_generated": 350,
    "pages_failed": 0,
    "thumbnails_generated": true,
    "embeddings_generated": true,
    "chunks_count": 120,
    "last_processed_at": "2026-01-10T12:00:00Z"
  },
  "stats": {
    "view_count": 1523,
    "favorite_count": 89,
    "download_count": 45,
    "chat_sessions": 12
  },
  "average_rating": 4.5,
  "ratings_count": 23,
  "created_at": "2026-01-10T10:30:00Z",
  "updated_at": "2026-01-10T15:45:00Z"
}
```

### 4.3 Trigger Page Generation

Regenerate page images from a book's PDF.

```http
POST /v1/admin/books/{book_id}/generate-pages
```

**Request Body (Optional):**

```json
{
  "force": true,
  "resolutions": ["thumbnail", "medium", "high"]
}
```

**Response:**

```json
{
  "success": true,
  "job_id": "job_abc123",
  "message": "Page generation started",
  "estimated_time_seconds": 120
}
```

### 4.4 Regenerate Thumbnails

Regenerate book cover and page thumbnails.

```http
POST /v1/admin/books/{book_id}/generate-thumbnails
```

**Response:**

```json
{
  "success": true,
  "job_id": "job_def456",
  "message": "Thumbnail generation started"
}
```

### 4.5 Process AI (Embeddings & Chunks)

Trigger AI processing to generate text chunks and embeddings for RAG.

```http
POST /v1/admin/books/{book_id}/process-ai
```

**Request Body (Optional):**

```json
{
  "chunk_size": 500,
  "chunk_overlap": 50,
  "regenerate": true
}
```

**Response:**

```json
{
  "success": true,
  "job_id": "job_ghi789",
  "message": "AI processing started",
  "estimated_chunks": 120
}
```

### 4.6 Delete Book

Permanently delete a book and all associated data.

```http
DELETE /v1/admin/books/{book_id}
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `permanent` | bool | false | Permanent delete vs soft delete |

**Response:**

```json
{
  "success": true,
  "message": "Book deleted successfully",
  "book_id": "e6142920-cc96-42f8-a950-265bf9e7890e"
}
```

---

## 5. Chat Session Management API

### 5.1 List Chat Sessions

Retrieve all chat sessions across all users.

```http
GET /v1/admin/chats
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `per_page` | int | 20 | Items per page |
| `user_id` | string | - | Filter by user |
| `book_id` | string | - | Filter by book |
| `sort` | string | `-updated_at` | Sort field |

**Response:**

```json
{
  "data": [
    {
      "id": "chat_abc123",
      "user_id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
      "user_display_name": "John Doe",
      "book_id": "e6142920-cc96-42f8-a950-265bf9e7890e",
      "book_title": "Introduction to Machine Learning",
      "message_count": 15,
      "total_tokens": 5000,
      "total_cost_cents": 12,
      "created_at": "2026-01-10T10:30:00Z",
      "last_message_at": "2026-01-10T15:45:00Z"
    }
  ],
  "total": 230,
  "page": 1,
  "per_page": 20,
  "total_pages": 12
}
```

### 5.2 Get Chat Session Details

Retrieve a chat session with all messages.

```http
GET /v1/admin/chats/{chat_id}
```

**Response:**

```json
{
  "id": "chat_abc123",
  "user": {
    "id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
    "username": "johndoe",
    "display_name": "John Doe"
  },
  "book": {
    "id": "e6142920-cc96-42f8-a950-265bf9e7890e",
    "title": "Introduction to Machine Learning"
  },
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "What is the main topic of chapter 3?",
      "created_at": "2026-01-10T10:30:00Z"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "Chapter 3 covers supervised learning algorithms...",
      "model": "gpt-4o-mini",
      "tokens_input": 150,
      "tokens_output": 200,
      "cost_cents": 1,
      "created_at": "2026-01-10T10:30:05Z"
    }
  ],
  "stats": {
    "message_count": 15,
    "total_tokens": 5000,
    "total_cost_cents": 12
  },
  "created_at": "2026-01-10T10:30:00Z",
  "updated_at": "2026-01-10T15:45:00Z"
}
```

### 5.3 Delete Chat Session

Delete a chat session and all messages.

```http
DELETE /v1/admin/chats/{chat_id}
```

**Response:**

```json
{
  "success": true,
  "message": "Chat session deleted successfully",
  "chat_id": "chat_abc123"
}
```

---

## 6. Cache Management API

### 6.1 Get Cache Statistics

Retrieve Redis cache statistics.

```http
GET /v1/cache/stats
```

**Response:**

```json
{
  "connected": true,
  "memory": {
    "used_bytes": 52428800,
    "used_formatted": "50 MB",
    "peak_bytes": 104857600,
    "peak_formatted": "100 MB",
    "fragmentation_ratio": 1.2
  },
  "stats": {
    "total_connections_received": 1500,
    "total_commands_processed": 2500000,
    "keyspace_hits": 2000000,
    "keyspace_misses": 500000,
    "hit_rate": 0.80
  },
  "keys": {
    "total": 15000,
    "expires": 12000,
    "avg_ttl_seconds": 3600
  },
  "uptime_seconds": 86400,
  "uptime_formatted": "1 day"
}
```

### 6.2 Get Cache Health

Check Redis connectivity and health.

```http
GET /v1/cache/health
```

**Response:**

```json
{
  "status": "healthy",
  "connected": true,
  "latency_ms": 2,
  "version": "7.2.0",
  "mode": "cluster"
}
```

### 6.3 Invalidate Cache by Pattern

Delete cache entries matching a pattern.

```http
POST /v1/cache/invalidate
```

**Request Body:**

```json
{
  "pattern": "books:*",
  "confirm": true
}
```

**Response:**

```json
{
  "success": true,
  "keys_deleted": 150,
  "pattern": "books:*"
}
```

**Common Patterns:**

| Pattern | Description |
|---------|-------------|
| `books:*` | All book-related cache |
| `users:*` | All user-related cache |
| `search:*` | Search result cache |
| `session:*` | Session cache |
| `book:e6142920:*` | Specific book cache |
| `user:62e6c9ad:*` | Specific user cache |

### 6.4 Delete Specific Keys

Delete specific cache keys.

```http
DELETE /v1/cache/keys
```

**Request Body:**

```json
{
  "keys": [
    "book:e6142920:detail",
    "book:e6142920:pages",
    "user:62e6c9ad:profile"
  ]
}
```

**Response:**

```json
{
  "success": true,
  "keys_deleted": 3
}
```

### 6.5 Flush All Cache

Delete all cache entries (use with caution).

```http
POST /v1/cache/flush
```

**Request Body:**

```json
{
  "confirm": true
}
```

**Response:**

```json
{
  "success": true,
  "message": "Cache flushed successfully"
}
```

**Warning:** This operation deletes ALL cache entries and may impact performance temporarily.

---

## 7. System Statistics API

### 7.1 Get System Statistics

Retrieve overall system statistics.

```http
GET /v1/admin/stats
```

**Response:**

```json
{
  "users": {
    "total": 1500,
    "active": 1200,
    "suspended": 50,
    "new_today": 25,
    "new_this_week": 150,
    "new_this_month": 500
  },
  "books": {
    "total": 5000,
    "public": 3500,
    "private": 1500,
    "processing": 10,
    "failed": 5,
    "new_today": 50,
    "new_this_week": 300
  },
  "storage": {
    "total_bytes": 107374182400,
    "total_formatted": "100 GB",
    "books_bytes": 85899345920,
    "thumbnails_bytes": 10737418240,
    "pages_bytes": 10737418240
  },
  "ai": {
    "total_sessions": 2500,
    "total_messages": 50000,
    "total_tokens": 10000000,
    "total_cost_cents": 25000,
    "sessions_today": 100
  },
  "cache": {
    "hit_rate": 0.85,
    "memory_used_formatted": "50 MB",
    "keys_count": 15000
  },
  "api": {
    "requests_today": 50000,
    "requests_this_week": 300000,
    "average_latency_ms": 45
  },
  "generated_at": "2026-01-10T16:00:00Z"
}
```

---

## 8. Error Handling

### 8.1 Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE",
  "request_id": "req_abc123",
  "timestamp": "2026-01-10T16:00:00Z"
}
```

### 8.2 Error Codes

| HTTP Status | Error Code | Description |
|-------------|------------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request parameters |
| 400 | `INVALID_PATTERN` | Invalid cache pattern |
| 401 | `UNAUTHORIZED` | Missing or invalid token |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 403 | `ADMIN_REQUIRED` | Admin role required |
| 404 | `USER_NOT_FOUND` | User does not exist |
| 404 | `BOOK_NOT_FOUND` | Book does not exist |
| 404 | `CHAT_NOT_FOUND` | Chat session does not exist |
| 409 | `USER_ALREADY_DISABLED` | User is already disabled |
| 409 | `PROCESSING_IN_PROGRESS` | Processing already running |
| 500 | `INTERNAL_ERROR` | Internal server error |
| 503 | `CACHE_UNAVAILABLE` | Redis connection failed |

---

## 9. Rate Limits

### 9.1 Admin API Rate Limits

| Role | Requests/min | Requests/hour |
|------|--------------|---------------|
| `admin` | 300 | 10,000 |
| `super_admin` | 600 | 30,000 |

### 9.2 Rate Limit Headers

```http
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 298
X-RateLimit-Reset: 1704067200
```

### 9.3 Rate Limit Exceeded Response

```json
{
  "detail": "Rate limit exceeded. Try again in 45 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 45
}
```

---

## 10. Webhooks

### 10.1 Admin Webhook Events

| Event | Description | Payload |
|-------|-------------|---------|
| `admin.user.disabled` | User was disabled | User object |
| `admin.user.role_changed` | User roles updated | User + changes |
| `admin.book.deleted` | Book was deleted | Book ID + admin |
| `admin.chat.deleted` | Chat session deleted | Chat ID + admin |
| `admin.cache.flushed` | Cache was flushed | Admin + timestamp |

### 10.2 Webhook Payload Example

```json
{
  "event": "admin.user.disabled",
  "timestamp": "2026-01-10T16:00:00Z",
  "admin": {
    "id": "admin_xyz",
    "username": "admin"
  },
  "data": {
    "user_id": "62e6c9ad-d142-4dc9-aa53-3def2b5052ad",
    "reason": "Terms of service violation"
  }
}
```

---

## 11. SDK Examples

### 11.1 Python Example

```python
import requests

BASE_URL = "https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io"
TOKEN = "your_admin_jwt_token"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# List users
response = requests.get(
    f"{BASE_URL}/v1/admin/users",
    headers=headers,
    params={"page": 1, "per_page": 20, "status": "active"}
)
users = response.json()

# Trigger page generation
response = requests.post(
    f"{BASE_URL}/v1/admin/books/{book_id}/generate-pages",
    headers=headers,
    json={"force": True}
)
result = response.json()

# Get system stats
response = requests.get(
    f"{BASE_URL}/v1/admin/stats",
    headers=headers
)
stats = response.json()
```

### 11.2 JavaScript/TypeScript Example

```typescript
const BASE_URL = "https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io";
const TOKEN = "your_admin_jwt_token";

const headers = {
  Authorization: `Bearer ${TOKEN}`,
  "Content-Type": "application/json",
};

// List users
const usersResponse = await fetch(
  `${BASE_URL}/v1/admin/users?page=1&per_page=20&status=active`,
  { headers }
);
const users = await usersResponse.json();

// Trigger AI processing
const processResponse = await fetch(
  `${BASE_URL}/v1/admin/books/${bookId}/process-ai`,
  {
    method: "POST",
    headers,
    body: JSON.stringify({ regenerate: true }),
  }
);
const result = await processResponse.json();

// Invalidate cache
const cacheResponse = await fetch(`${BASE_URL}/v1/cache/invalidate`, {
  method: "POST",
  headers,
  body: JSON.stringify({ pattern: "books:*", confirm: true }),
});
const cacheResult = await cacheResponse.json();
```

### 11.3 cURL Examples

```bash
# Set token
TOKEN="your_admin_jwt_token"
BASE_URL="https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io"

# List users
curl -X GET "$BASE_URL/v1/admin/users?page=1&per_page=20" \
  -H "Authorization: Bearer $TOKEN"

# Get user details
curl -X GET "$BASE_URL/v1/admin/users/62e6c9ad-d142-4dc9-aa53-3def2b5052ad" \
  -H "Authorization: Bearer $TOKEN"

# Update user roles
curl -X PATCH "$BASE_URL/v1/admin/users/62e6c9ad-d142-4dc9-aa53-3def2b5052ad" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"roles": ["user", "moderator"]}'

# Disable user
curl -X POST "$BASE_URL/v1/admin/users/62e6c9ad-d142-4dc9-aa53-3def2b5052ad/disable" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Violation of terms", "notify_user": true}'

# List all books
curl -X GET "$BASE_URL/v1/admin/books?status=ready&page=1" \
  -H "Authorization: Bearer $TOKEN"

# Trigger page generation
curl -X POST "$BASE_URL/v1/admin/books/e6142920-cc96-42f8-a950-265bf9e7890e/generate-pages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": true}'

# Get system stats
curl -X GET "$BASE_URL/v1/admin/stats" \
  -H "Authorization: Bearer $TOKEN"

# Get cache stats
curl -X GET "$BASE_URL/v1/cache/stats" \
  -H "Authorization: Bearer $TOKEN"

# Invalidate cache
curl -X POST "$BASE_URL/v1/cache/invalidate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pattern": "books:*", "confirm": true}'
```

---

## Related Documentation

- [Product Requirements (PRD)](./PRD.md)
- [Technical Design (TDD)](./TDD.md)
- [API Swagger Docs](https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/docs)
- [Changelog](../CHANGELOG.md)

---

*Document maintained by saMas IT Services, Milpitas, California*
*Website: samas.tech*
