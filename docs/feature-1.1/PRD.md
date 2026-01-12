## API PRD: “Home Feed (HN-style) + Activity + Privacy + Performance” (built on current OpenAPI)

### TL;DR for your Product Manager

* We will add a **fast, cacheable “Home Feed” API** that surfaces **reading activity** (started reading, progress milestones, likes/favorites, ratings, AI highlights) in an HN-style list.
* We will add **privacy controls** (per-user + per-book) to ensure the feed only shows what users intend.
* We will design for **speed + reliability**: CDN-friendly responses, pagination, ETag, cursoring, and server-side aggregation.
* We will keep “annotations/bookmarks” explicitly **out of MVP** (separate feature), and focus on **activity + discovery**.
* Existing primitives we’ll reuse:

  * Favorites endpoints exist (`/v1/books/{book_id}/favorite`, `/v1/books/me/favorites`) 
  * Ratings endpoints exist (book ratings CRUD) 
  * Page browsing exists (`/v1/books/{book_id}/pages`, `/pages/{page_number}`, `/pages/generate`) 
  * SSE streaming chat exists (`/v1/chats/{session_id}/stream`) 
  * Rate limiting is defined by tier (Free 60 rpm / Premium 300 rpm / Enterprise 1000 rpm) and standard headers are specified 

---

# 1) Problem Statement

Your app wants a “news” home page like HN where users can quickly browse what’s happening—without loading entire documents—and without making the home page slow. Current API supports core reading actions (pages, favorites, ratings, chat), but **does not yet provide a unified “feed” surface** that’s:

* privacy-aware (what’s shared vs private),
* fast (single call for a home timeline),
* cache-friendly (ETag/cursors),
* resilient to scraping/DDoS patterns.

The PRD.md already calls out “Reading Progress” as planned (history endpoint spec exists in PRD) , but it’s not clearly present in the current `api-v1.yaml` excerpts we’ve seen—so we’ll specify it as part of this “activity” foundation.

---

# 2) Goals / Non-Goals

## Goals

1. **HN-style Home Feed**: a single endpoint the mobile/web client can call to render “news”.
2. **Privacy-first activity**: user controls what activities are visible.
3. **Performance**: low latency, stable pagination, CDN- and cache-friendly responses.
4. **Ease of adaptation**: simple event model that can evolve (new event types, new ranking).
5. **Anti-abuse**: reduce scraping and DDoS impact, especially on media/page delivery.

## Non-Goals (explicitly out of this PRD)

* Bookmarks/annotations endpoints (you asked to treat them separately).
* Full “social network” (comments/threads) beyond minimal “open activity detail” support.
* Full semantic search (already planned elsewhere in PRD).

---

# 3) Key Concepts

## 3.1 Activity Event (core primitive)

An “event” is a record like:

* `user_started_book`
* `user_progress_updated` (milestones: 10%, 25%, 50%, completed)
* `user_favorited_book` (uses existing favorite endpoints) 
* `user_rated_book` (uses existing rating endpoints) 
* `user_created_chat` or `user_asked_ai_about_book` (ties to chat sessions/stream) 

## 3.2 Feed Item (what the home page renders)

A feed item is an event + derived metadata for rendering:

* actor (public profile fields),
* book summary (title/author/cover),
* “why it matters” snippet (e.g., “reached 50%”, “favorited”, “asked AI: …”),
* timestamps,
* privacy flags,
* optional “preview” objects (small, not heavy).

---

# 4) Proposed API Additions

## 4.1 Feed API (new)

### `GET /v1/feed/home`

**Purpose**: Home timeline, HN-like list.

**Query params**

* `cursor` (opaque string, preferred over page/limit for stability)
* `limit` (default 30, max 100)
* `mode` = `following` | `global` | `friends` (start with `following` + `global`)
* `since` (optional ISO time; allows “pull to refresh”)
* `ranking` = `recent` | `hot` (hot = time decay + engagement)

**Response**

```json
{
  "data": [
    {
      "id": "evt_...",
      "type": "user_favorited_book",
      "created_at": "2026-01-10T16:03:12Z",
      "actor": { "id": "...", "display_name": "...", "avatar_url": "..." },
      "book": { "id": "...", "title": "...", "author": "...", "cover_url": "..." },
      "payload": { "note": null },
      "privacy": { "visibility": "followers" },
      "stats": { "likes": 3, "comments": 0 }
    }
  ],
  "next_cursor": "opaque...",
  "server_time": "..."
}
```

**Caching**

* For `mode=global`: CDN-cacheable for short TTL (e.g., 15–30s) with **ETag** and `stale-while-revalidate`.
* For `mode=following`: user-specific → not CDN-cacheable broadly, but still uses **ETag** and app-level caching.

---

## 4.2 Activity API (new)

### `POST /v1/activity/events`

**Purpose**: Allow the platform to record user actions not already captured by existing endpoints, and unify event creation for the feed.

**But**: Prefer **server-side event emission** from existing endpoints wherever possible (favorites, ratings, progress, chat), so clients don’t spoof activity. This endpoint is mainly for:

* “started reading” (when opening a book)
* “opened page range” (optional)
* “shared highlight” (future)

**Security**: authenticated only; server validates the action.

---

## 4.3 Progress API (bring into OpenAPI as real endpoints)

PRD describes progress/history requirements ; implement them as API that also emits events.

### `PUT /v1/progress/{bookId}`

* Updates progress and emits `user_progress_updated` event when crossing milestones.

### `GET /v1/progress/{bookId}`

* Returns current progress state.

### `GET /v1/progress/history`

* Returns “recently read” list for profile + feed seeding (PRD calls this out) 

---

## 4.4 Privacy Controls (new + extend existing)

### Extend `PATCH /v1/users/me` preferences

Your OpenAPI already supports updating preferences in profile . Add fields:

* `privacy.profile_visibility`: `public | followers | private`
* `privacy.activity_visibility_default`: `public | followers | private`
* `privacy.show_currently_reading`: boolean
* `privacy.show_favorites`: boolean
* `privacy.show_ratings`: boolean
* `privacy.show_ai_activity`: boolean

### Per-book override

Add either:

* `PATCH /v1/books/{book_id}` with `visibility` and `activity_visibility_override`
  or
* `PUT /v1/books/{book_id}/privacy`

This matters because a user may read private documents but still want a public profile.

---

# 5) Performance & Caching Requirements

## 5.1 Home Feed latency targets

* **p50 < 150ms**, **p95 < 400ms** (excluding network), since it’s called on app launch.
* Avoid fan-out by aggregating feed items in one query, with pre-joined minimal book/user fields.

## 5.2 Pagination strategy

* Feed endpoints must use **cursor-based pagination** (stable under inserts).
* Maintain ordering by `(created_at desc, id desc)`.

## 5.3 Response shaping (prevent overfetch)

Add `fields=` query param (sparse fieldsets), e.g.

* `fields=actor,book,payload,stats` default
* `fields=...` optional

## 5.4 Media/page browsing performance (ties to your “pages not whole doc” goal)

You already have:

* list pages with thumbnails 
* get page details with signed URLs 

Add:

* `GET /v1/books/{book_id}/pages:manifest`

  * returns page count + resolutions + CDN base path + hash version
* ensure `GET /pages/{page_number}` returns **cacheable metadata** while signed URLs remain short-lived.

---

# 6) Security & Abuse Resistance (DDoS + scraping)

You already define tiered rate limits and standard headers  and a RateLimited response schema . For this PRD:

## 6.1 Threats

1. **Feed scraping**: bots pulling `/feed/home` rapidly.
2. **Media scraping**: iterating pages and downloading all images/PDFs.
3. **Credential stuffing**: brute forcing `/auth/login`.
4. **SSE abuse**: keeping many `/chats/{id}/stream` connections open .
5. **Hotlinking**: sharing signed URLs publicly.

## 6.2 Mitigations (best-practice set)

* **Rate limit by key + IP + user** (layered):

  * Separate buckets: auth, feed, pages, chat/SSE.
* **Signed URL hardening**

  * very short TTL for page images (e.g., 60–300s),
  * include `book_id`, `page_number`, `resolution`, `exp`, and a signature,
  * optionally bind to `user_id` (prevents sharing) if your CDN supports it.
* **CDN + WAF**

  * cache thumbnails aggressively,
  * WAF rules for common bot patterns,
  * block excessive 4xx from same IP.
* **Robots / anti-scraping signals**

  * require auth for most media access (already implied by pages endpoints being secured) 
* **SSE connection caps**

  * max concurrent streams per user/IP; idle timeout; heartbeat.

---

# 7) MVP Scope for these new API features

### Must-have (to ship a compelling HN-style home page)

1. `GET /v1/feed/home` (global + following)
2. Progress endpoints (GET/PUT + history) and event emission
3. Privacy settings (user-level defaults + per-book override)
4. Aggregated “feed item shape” with minimal fields
5. Cache headers + cursor pagination

### Nice-to-have (still small, but increases engagement)

* `GET /v1/feed/notifications` (someone followed you / liked your activity)
* “hot ranking” (simple decay + engagement)
* Basic “follow” endpoints if not already in API (PRD mentions friends) 

---

# 8) Acceptance Criteria

**Feed correctness**

* If a user sets `activity_visibility_default=private`, their actions never appear in global/following feeds.
* If a book is private, no event referencing it appears for non-authorized viewers.

**Performance**

* Home feed returns in <400ms p95 at moderate load.
* Feed supports cursor pagination without duplicates or gaps.

**Abuse resistance**

* Rate limit headers present everywhere (consistent with spec) 
* Excessive calls get standardized RateLimited response 

---

# 9) Critique of your stated direction (speed, reliability, easy adaptation, pages/chunks, signed URLs, DDoS)

You’re aiming at the right fundamentals, but a few sharp edges to watch:

1. **“Most logic in the API” is correct** for consistency and anti-cheat, but:

   * it increases backend complexity; you’ll need strict contracts + versioning so mobile/web don’t break.
2. **“Pages + chunks both”** is ideal, but:

   * you must define which is canonical for citations and progress (usually pages for UX, chunks for AI).
3. **Signed URLs** help, but:

   * they don’t stop scraping if the attacker is authenticated; you still need layered rate limits + anomaly detection.
4. **Home feed performance** will fail if it fan-outs (N queries per item):

   * treat feed as an aggregated read model (materialized view or precomputed timeline).

---

If you want, I can also produce:

* a matching **TDD for these new API endpoints** (schemas, indexes, caching headers, event outbox pattern),
* and then a **mobile PRD/TDD** that consumes `/v1/feed/home` with React Query + prefetching.
