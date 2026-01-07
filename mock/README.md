# ILM Red API Mock Server

This directory contains mock API infrastructure for testing the ILM Red API.

## Quick Start

### Prerequisites

```bash
# Install dependencies
npm install
```

### Option 1: Prism Mock Server (Recommended)

Prism reads the OpenAPI specification and returns example responses.

```bash
# Start Prism mock server on port 4010
npm run mock

# Or with dynamic response generation
npm run mock:dynamic
```

**Test endpoints:**
```bash
# List books
curl http://localhost:4010/v1/books

# Get single book
curl http://localhost:4010/v1/books/ffe66482-4ee7-4de8-8c94-38d5414c1d17

# Get book ratings
curl http://localhost:4010/v1/books/ffe66482-4ee7-4de8-8c94-38d5414c1d17/ratings

# Health check
curl http://localhost:4010/health
```

### Option 2: JSON Server (For CRUD Testing)

JSON Server allows full CRUD operations against mock data.

```bash
# Start JSON Server on port 4011
npm run mock:json-server
```

**Test CRUD operations:**
```bash
# GET all books
curl http://localhost:4011/v1/books

# GET single book
curl http://localhost:4011/v1/books/ffe66482-4ee7-4de8-8c94-38d5414c1d17

# POST new book
curl -X POST http://localhost:4011/v1/books \
  -H "Content-Type: application/json" \
  -d '{"title":"New Book","author":"Author Name","category":"fiction"}'

# PATCH update book
curl -X PATCH http://localhost:4011/v1/books/ffe66482-4ee7-4de8-8c94-38d5414c1d17 \
  -H "Content-Type: application/json" \
  -d '{"title":"Updated Title"}'

# DELETE book
curl -X DELETE http://localhost:4011/v1/books/ffe66482-4ee7-4de8-8c94-38d5414c1d17
```

## Directory Structure

```
mock/
├── data/                    # Transformed mock data (API format)
│   ├── books.json          # 100 books (camelCase)
│   ├── book-details.json   # Extended book data
│   ├── ratings.json        # 22 ratings with reviews
│   └── users.json          # 18 generated users
├── db.json                 # JSON Server database
├── routes.json             # JSON Server route mappings
└── README.md               # This file
```

## Data Transformation

Mock data is transformed from Supabase export format (snake_case) to API format (camelCase).

```bash
# Re-run transformation if source data changes
npm run transform:data
```

**Transformation mappings:**
- `user_id` → `userId`
- `uploaded_at` → `createdAt`
- `view_count` → `stats.viewCount`
- `thumbnail_path` → `thumbnailUrl` (with CDN URL)

## Sample Data

**Books (100 records):**
- "Charlie and the Chocolate Factory" - children, English
- "Wings in the Night" - horror, English
- "Aik-Chadar-Maili-si" - literature, Urdu
- Various categories: children, horror, technology, literature, religion, etc.

**Ratings (22 records):**
- Ratings 1-5 with review text
- Real feedback like "Highly Recommended!" and "This is fantastic"

**Users (18 profiles):**
- Generated from unique user IDs in book and rating data
- Includes username, displayName, email, bio

## Swagger UI

When using Prism, access Swagger UI documentation at:
```
http://localhost:4010/docs
```

## Comparison: Prism vs JSON Server

| Feature | Prism | JSON Server |
|---------|-------|-------------|
| Read-only | Yes | No |
| CRUD operations | No | Yes |
| OpenAPI validation | Yes | No |
| Dynamic responses | Optional | No |
| Persistence | No | Yes (db.json) |
| Best for | Documentation testing | Integration testing |
