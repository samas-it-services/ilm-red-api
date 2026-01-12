
# PART 2 — Mobile PRD + TDD

## Home Feed Consumption (Expo / Web)

---

## Mobile PRD — Home Feed

### Objective

Make ilm.red feel **alive but calm**, like Hacker News:

* fast
* text-first
* privacy-respecting
* discovery-driven

---

### Home Screen Layout

1. **Continue Reading (Personal)**

   * Single pinned item
2. **What’s happening**

   * Feed list (HN-style)
3. **Trending today**

   * 3–5 aggregated items

---

### Feed Item UI Rules

* No avatars by default
* No timestamps → use “Today / This week”
* No reactions shown (counts only if aggregate)
* Tap book → book detail
* No infinite scroll dopamine loops (max ~50 items)

---

### Privacy UX

* Inline notice:

  > “Activity respects your privacy”
* Settings:

  * Private / Anonymous / Named
* Toggle applies to future events only

---

## Mobile TDD

### 1. Data Fetching

```ts
useFeedHome({
  limit: 30,
  modules: ['continue','community','trending']
})
```

**React Query config**

```ts
staleTime: 15_000
cacheTime: 300_000
retry: 1
```

### 2. Conditional Requests

* Store `ETag`
* Send `If-None-Match`
* On `304`, reuse cache

---

### 3. Rendering Performance

* `FlashList` / virtualized list
* Keyed by `feed_item.id`
* Skeleton on first load only

---

### 4. Offline / Failure Modes

| Scenario   | UX                        |
| ---------- | ------------------------- |
| Offline    | Show cached feed + banner |
| 429        | “Try again in a moment”   |
| 401        | Silent refresh            |
| Empty feed | Seeded discovery items    |

---

### 5. Security Considerations (Client)

* Never infer privacy
* Never build social context client-side
* All feed items rendered exactly as received

---

## Mobile Acceptance Criteria

* Home loads <500ms perceived
* No UI jump on refresh
* Feed scroll remains 60fps
* Privacy toggles respected instantly (next refresh)
* Works identically on web + mobile

---

## Final Critique (Honest)

You’re doing this **the right way**:

* API-first ✔
* Read-model feed ✔
* Privacy as default ✔
* CDN + cache ✔

The **biggest risk** is scope creep into social mechanics.
This design explicitly prevents that.

---

If you want next, I can:

* Write the **exact OpenAPI YAML additions** for `/v1/feed/home`
* Provide **SQL migration scripts**
* Design **admin moderation tools** for feed safety
* Draft **privacy policy language** matching this behavior

Just tell me the next step.
