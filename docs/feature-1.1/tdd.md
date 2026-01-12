Perfect — below is a **clean, implementation-ready TDD for the API first**, followed by a **mobile PRD + TDD** that consumes it.
This is written so backend can start immediately, and mobile can follow without rework.

I am **anchoring everything to your existing `api-v1.yaml` + PRD**, not inventing a parallel system.

---

# PART 1 — API TDD

## Home Feed (HN-style) + Activity + Privacy + Performance

This TDD translates the **API PRD** into concrete backend design decisions: schemas, indexes, flows, caching, and safeguards.

---

## 1. System Overview (Read Model–First)

**Key architectural choice**
The Home Feed is a **read-optimized model**, not a live query across many tables.

```
User actions
   ↓
Domain events (server-side)
   ↓
Feed event store (append-only)
   ↓
Aggregations + materialized views
   ↓
Feed API (fast, cacheable)
```

This is essential for:

* speed
* cacheability
* privacy enforcement
* future ranking changes

---

## 2. Core Data Models

### 2.1 `activity_events` (append-only)

Purpose: canonical log of user activity that *may* appear in feeds.

```sql
activity_events (
  id UUID PRIMARY KEY,
  event_type TEXT NOT NULL,
  user_id UUID NULL,
  book_id UUID NULL,

  -- privacy snapshot at time of event
  visibility TEXT NOT NULL CHECK (visibility IN ('private','anonymous','named','followers','public')),

  -- optional payload
  payload JSONB NULL,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Indexes**

```sql
CREATE INDEX idx_activity_events_created ON activity_events (created_at DESC);
CREATE INDEX idx_activity_events_book ON activity_events (book_id, created_at DESC);
CREATE INDEX idx_activity_events_visibility ON activity_events (visibility);
```

**Notes**

* Visibility is **snapshotted** so later privacy changes do not retroactively expose data.
* `payload` holds safe metadata only (milestones, rating value, etc.).

---

### 2.2 `feed_items` (materialized read model)

Purpose: what `/v1/feed/home` actually reads from.

```sql
feed_items (
  id UUID PRIMARY KEY,
  event_id UUID NOT NULL REFERENCES activity_events(id),

  type TEXT NOT NULL,
  rank_score FLOAT NOT NULL,

  book_id UUID NOT NULL,
  actor_user_id UUID NULL,        -- nullable for anonymous
  actor_display_name TEXT NULL,

  time_bucket TEXT NOT NULL,      -- today | this_week | this_month
  stats JSONB NULL,               -- aggregated counts

  created_at TIMESTAMPTZ NOT NULL
);
```

**Indexes**

```sql
CREATE INDEX idx_feed_items_rank ON feed_items (rank_score DESC, created_at DESC);
CREATE INDEX idx_feed_items_created ON feed_items (created_at DESC);
```

---

### 2.3 Aggregates (for “trending”)

```sql
book_activity_daily (
  date DATE NOT NULL,
  book_id UUID NOT NULL,

  started_count INT DEFAULT 0,
  finished_count INT DEFAULT 0,
  favorited_count INT DEFAULT 0,

  PRIMARY KEY (date, book_id)
);
```

Used to cheaply compute:

* “X people reading today”
* “Trending this week”

---

### 2.4 User Privacy Settings (extend existing user profile)

```sql
user_privacy_settings (
  user_id UUID PRIMARY KEY,

  feed_sharing TEXT NOT NULL DEFAULT 'private',
  allow_aggregate_metrics BOOLEAN DEFAULT true,

  show_currently_reading BOOLEAN DEFAULT false,
  show_favorites BOOLEAN DEFAULT false,
  show_ratings BOOLEAN DEFAULT false
);
```

---

## 3. Event Emission Rules (Critical)

**Never trust the client to emit feed events.**
All feed events are emitted **server-side** from existing endpoints.

### 3.1 Emit events from existing APIs

| User Action                        | Source Endpoint                       | Event                     |
| ---------------------------------- | ------------------------------------- | ------------------------- |
| Open book first time               | `GET /books/{id}` + no prior progress | `user_started_book`       |
| Update progress crossing milestone | `PUT /progress/{bookId}`              | `user_progress_milestone` |
| Finish book                        | `PUT /progress/{bookId}`              | `user_finished_book`      |
| Favorite book                      | `POST /books/{id}/favorite`           | `user_favorited_book`     |
| Rate book                          | `POST /books/{id}/rating`             | `user_rated_book`         |
| New public book                    | `POST /books` (public)                | `new_public_book`         |

---

### 3.2 Privacy enforcement at emission time

Before emitting:

1. Load user privacy settings
2. Determine visibility:

   * `private` → **do not emit**
   * `anonymous` → emit without user info
   * `named/followers/public` → emit with constraints

Aggregates:

* Respect `allow_aggregate_metrics`
* Aggregates never contain user IDs

---

## 4. Feed Construction Pipeline

### 4.1 Background worker (async)

Triggered by:

* new `activity_events`
* scheduled aggregation job (hourly/daily)

**Responsibilities**

* Normalize event → feed item
* Assign `time_bucket`
* Compute `rank_score`
* Insert into `feed_items`
* Update `book_activity_daily`

---

### 4.2 Ranking (simple, stable, non-addictive)

```text
rank_score =
  base_weight(event_type)
  * time_decay(created_at)
  * diversity_penalty(book_id)
```

No engagement feedback loops.

---

## 5. Feed API Design

### 5.1 `GET /v1/feed/home`

**Execution path**

1. Load cached public feed module (Redis / memory)
2. If authenticated:

   * Load personalized `continue_reading`
3. Merge modules
4. Apply cursor pagination
5. Return shaped response

---

### 5.2 Caching Strategy (mandatory)

#### Public modules

```
Cache-Control: public, max-age=30, stale-while-revalidate=120
ETag enabled
```

#### Authenticated responses

```
Cache-Control: private, max-age=10
ETag enabled
```

**Redis keys**

```
feed:public:v1:{locale}
feed:trending:{window}
```

---

## 6. Cursor Pagination (No Offsets)

```json
{
  "cursor_next": "base64(created_at|id)"
}
```

Prevents:

* duplicates
* missing items
* expensive OFFSET scans

---

## 7. Rate Limiting & Abuse Controls

### 7.1 Limits (per existing tiers)

| Tier      | Feed RPM |
| --------- | -------- |
| Anonymous | 30       |
| Free      | 60       |
| Premium   | 300      |

### 7.2 Defensive rules

* Block cursor probing patterns
* Cap “cursor depth” per minute
* Separate rate buckets for:

  * feed
  * pages
  * chat/SSE

---

## 8. Error Handling

Standard error envelope (reuse existing):

```json
{
  "code": "rate_limited",
  "message": "Too many requests",
  "request_id": "req_..."
}
```

---

## 9. Observability

**Metrics**

* feed cache hit %
* feed build latency
* events/min by type
* privacy suppression count

**Logs**

* event_id only (never raw book titles for private items)

---

## 10. Acceptance Criteria (API)

* Private users never appear in feed
* Aggregates include only opted-in users
* `/feed/home` p95 < 400ms
* Cursor pagination stable under inserts
* CDN serves ≥70% of public feed requests

---
