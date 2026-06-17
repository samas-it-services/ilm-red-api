# Agent Coordination Plan

## Project Status Overview
- **Backend (API):** 
  - ✅ Phase 5 Part 1: Personalized Recommendations (Complete)
  - ✅ Phase 5 Part 2: Book Extras (Endpoints implemented: `BookExtra` model, repository, service, API)
  - ✅ Phase 6: Annotations (Endpoints implemented: Bookmarks, Highlights, Notes)
  - ✅ Web Backend Migration: `ilm-red-unbound` migrated from Supabase to API client.
- **Frontend (Mobile):**
  - 🚧 Phase 5 Part 2: Book Extras UI (Pending)
  - 🚧 Phase 6: Annotations UI (Pending)
- **Frontend (Web):**
  - 🚧 Phase 5 Part 2: Book Extras UI (Pending)
  - 🚧 Phase 6: Annotations UI (Pending)

## Strategic Roadmap & Priorities

### 1. 🚀 Priority 1: Mobile UI for Book Extras (Phase 5 Closure)
**Rationale:** The backend for "Book Extras" (flashcards, quizzes, etc.) is ready. Completing the mobile UI closes Phase 5 completely and delivers a tangible learning feature to users.
**Task:**
- Create `BookExtra` components in React Native.
- Integrate `GET /books/{id}/extras` to fetch content.
- Implement specialized views for each extra type (Flashcard Deck, Quiz View, Audio Player).
- Update Book Detail screen to show available extras.

### 2. Priority 2: Mobile UI for Annotations (Phase 6 Closure)
**Rationale:** "Read, Chat, Understand" is the motto. Annotations (highlights/notes) are core to "Understand". Backend is ready.
**Task:**
- Update PDF Reader to support text selection and coordinate capture.
- Integrate `POST /books/{id}/highlights` and `POST /books/{id}/notes`.
- Display highlights overlay on PDF pages.
- Add "My Notes" side panel or modal.

### 3. Priority 3: Web UI Parity (Extras & Annotations)
**Rationale:** Ensure feature parity across platforms.
**Task:**
- Port Book Extras UI to React (Web).
- Update Web Reader for annotations.

### 4. Priority 4: Offline Reading (Phase 7)
**Rationale:** Major architectural change for mobile. Better to attempt after UI features are stable.
**Task:**
- Implement `expo-file-system` for local book storage.
- Create local SQLite database for offline metadata sync.
- Implement sync engine for offline annotations/progress.

## Next Recommended Agent Task

**Agent Name:** `implement-mobile-book-extras`
**Description:** Implement the mobile user interface for Book Extras (flashcards, quizzes) to consume the newly created API endpoints.
**Input:** `ilm-red-mobile-app` codebase.
**Goal:** Users can view and interact with flashcards and quizzes associated with a book on the mobile app.
