# PRD

## ILM Red – High-Performance Page-First Reading Platform

---

## 1. Executive Summary

ILM Red is a **page-first document reading platform** optimized for:

* fast browsing without loading entire documents
* reliable media delivery on mobile networks
* CDN-first architecture using signed URLs
* future AI features via internal chunking (without exposing complexity)

This phase **explicitly excludes annotations and bookmarks** to prioritize performance, stability, and adoption speed.

---

## 2. Core Product Principles

1. **Pages are the browsing unit**

   * Users browse pages, not documents
   * Pages must load independently

2. **Chunks are the intelligence unit**

   * Used internally for AI, search, summaries
   * Not required for initial browsing UX

3. **API orchestrates, storage serves**

   * No large media streamed by API servers
   * CDN + object storage do the heavy lifting

4. **Stateless, cacheable, retry-safe**

   * Every request safe to retry
   * No sticky sessions

---

## 3. Redesign: Page Endpoints for CDN-Friendliness

### Goals

* Maximize cache hits
* Minimize API load
* Support aggressive prefetching
* Work well on flaky networks

---

### 3.1 Page List Endpoint (Metadata Only)

#### Endpoint

```
GET /books/{bookId}/pages
```

#### Behavior

* Returns **metadata only**
* No page content
* Fully cacheable

#### Response (example)

```json
{
  "bookId": "book_123",
  "totalPages": 420,
  "pages": [
    {
      "pageNumber": 1,
      "width": 1240,
      "height": 1754,
      "thumbnailUrl": "https://cdn/.../thumb/1.jpg",
      "hasTextLayer": true
    }
  ],
  "version": "v3"
}
```

#### CDN Strategy

* Cache for 24h
* Invalidate only when book version changes
* `ETag` + `If-None-Match` supported

---

### 3.2 Page Access Endpoint (Signed URL Issuer)

#### Endpoint

```
GET /books/{bookId}/pages/{pageNumber}
```

#### Behavior

* Returns **signed URLs**, not content
* URLs point directly to CDN-backed storage

#### Response

```json
{
  "pageNumber": 12,
  "imageUrl": "https://cdn.example.com/...sig=abc&exp=...",
  "textLayerUrl": "https://cdn.example.com/...sig=xyz&exp=...",
  "expiresAt": "2026-01-09T12:34:56Z"
}
```

#### CDN Strategy

* CDN caches media
* API never streams images or PDFs
* Clients can prefetch next N pages

---

## 4. Signed URL Schema + TTL Strategy

### Goals

* Prevent hotlinking
* Limit blast radius if URLs leak
* Maintain good UX (no frequent refresh)

---

### 4.1 URL Design

Signed URLs must encode:

* resource path
* expiration timestamp
* user scope (hashed)
* HMAC signature

#### Example

```
https://cdn.example.com/books/{bookId}/pages/12.jpg
  ?exp=1704800000
  &uid=hash(userId)
  &sig=hmac_sha256(...)
```

---

### 4.2 TTL Strategy

| Resource Type | TTL       | Rationale                      |
| ------------- | --------- | ------------------------------ |
| Page images   | 10–15 min | Short-lived, prevents scraping |
| Thumbnails    | 1–6 hours | Low sensitivity                |
| PDFs          | 5–10 min  | High-value asset               |
| Text layers   | 10 min    | AI-related                     |

---

### 4.3 Refresh Strategy

* Client requests new signed URL automatically on 403/expired
* API rate-limited but lightweight
* URLs never refreshed silently in background without user intent

---

## 5. Future-Proof Internal Content Model (Pages → Chunks)

> Pages are for **rendering**
> Chunks are for **thinking**

### 5.1 Internal Model (Not Public API)

```
Book
 ├── Pages
 │    ├── pageNumber
 │    ├── imageRef
 │    ├── textRef
 │
 └── Chunks
      ├── chunkId
      ├── text
      ├── pageStart
      ├── pageEnd
      ├── chapterId
      ├── embedding
```

---

### 5.2 Chunking Rules

* Chunks:

  * 300–800 tokens
  * Never cross chapter boundaries
* Each chunk maps to:

  * page range
  * text offsets

This allows future features:

* AI citations → “from page 12”
* Tap-to-jump from AI answer to page
* Semantic search grounded in pages

---

### 5.3 Why This Matters Now

Even if chunks are unused initially:

* page generation must record page ↔ text mapping
* future AI features become additive, not destructive

---

## 6. Page Generation Pipeline (Reliability First)

### Endpoint

```
POST /books/{bookId}/pages/generate
```

### Properties

* Idempotent
* Async
* Safe to retry

### States

```
pending → processing → completed | failed
```

### Guarantees

* No partial success exposed
* Pages only visible when fully generated
* Generation versioned (`v1`, `v2`, …)

---

## 7. Security Threat Model (DDoS + Scraping)

### 7.1 Threats

#### A. Page Enumeration

Attackers crawl `/pages/1..N`

**Mitigation**

* Auth required for page list
* Signed URLs expire quickly
* Access logged per user/IP

---

#### B. Signed URL Sharing

Users share URLs publicly

**Mitigation**

* Short TTL
* User-bound signatures
* Optional watermarking later

---

#### C. API DDoS

Flooding page endpoints

**Mitigation**

* CDN absorbs media traffic
* API rate limits:

  * page list
  * signed URL issuance
* Token bucket per user + IP

---

#### D. Storage Cost Explosion

Malicious prefetching

**Mitigation**

* Prefetch limits per client
* Abnormal access detection
* Hard cap per user/session

---

## 8. Abuse Prevention Controls

### Mandatory

* Per-user request quotas
* Per-IP throttling
* 429 with retry-after
* Bot detection at CDN (WAF)

### Optional (Phase 2)

* Behavioral heuristics
* CAPTCHA on abuse signals
* Paid tier higher limits

---

## 9. Non-Goals (Explicit)

* Annotations
* Bookmarks
* Cross-device reading sync
* Offline caching logic
* Social sharing

These will be layered later **without breaking APIs**.

---

## 10. Success Criteria

### Technical

* Page browsing feels instantaneous
* Zero API crashes from media load
* No storage egress surprises

### Product

* Users can browse large books effortlessly
* Mobile experience works on poor networks
* Platform ready for AI features without redesign

---

## Final CTO-Level Feedback

You’re designing this **the right way**:

* Pages = UX performance
* Chunks = AI power
* Signed URLs + CDN = scalability
* Deferred annotations = speed to market

This architecture will comfortably support:

* $1k/month
* $10k/month
* $100k/month

…without a rewrite.

please enahce the api repo with the following
* Write **exact OpenAPI specs** for these endpoints
* Propose **infra topology (API + CDN + storage)**
* Define **client prefetch strategy**
* Draft a **migration plan from current API**

do all of that and enhace prd, tdd and share impplemenation plan with phases. keep in mind the first principle defined in the prd. if not, put them and refer to them betweeh each phase