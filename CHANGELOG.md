# **Changelog**

All notable changes to this project will be documented in this file.

## Format
- **Reverse chronological order** (newest at top)
- **Header format:** `YYYY-MM-DD | <category>: <title>`
- **Categories:**
  - 🚀 **feat**
  - 🐛 **fix**
  - 📘 **docs**
  - 🧹 **chore**
- **Sections included in every entry:**
  - 📄 **Summary**
  - 📁 **Files Changed**
  - 🧠 **Rationale**
  - 🔄 **Behavior / Compatibility Implications**
  - 🧪 **Testing Recommendations**
  - 📌 **Follow‑ups**

---

## 2026-01-07 | 🚀 feat: Phase 2 Books CRUD, Multi-Vendor AI, and Local Dev Setup

### 📄 **Summary**
Major release implementing Phase 2 (Books CRUD + File Storage), Phase 2.5 (Multi-Vendor AI Model Support), local development tooling, and comprehensive documentation updates. This release adds full book management capabilities, support for 6 AI vendors with intelligent model routing, and streamlined developer experience.

### 📁 **Files Changed**

#### Books CRUD + File Storage (Phase 2)
| File | Change Type | Description |
|------|-------------|-------------|
| `app/models/book.py` | Added | Book, Rating, Favorite SQLAlchemy models |
| `app/models/__init__.py` | Modified | Export new book models |
| `app/db/migrations/versions/20250107_0002_books.py` | Added | Books table migration with indexes |
| `app/schemas/book.py` | Added | Book request/response Pydantic schemas |
| `app/schemas/rating.py` | Added | Rating schemas |
| `app/schemas/__init__.py` | Modified | Export new schemas |
| `app/storage/base.py` | Added | Abstract StorageProvider interface |
| `app/storage/local.py` | Added | Local filesystem storage implementation |
| `app/storage/azure_blob.py` | Added | Azure Blob Storage implementation |
| `app/storage/__init__.py` | Modified | Storage provider factory |
| `app/repositories/book_repo.py` | Added | Book data access layer |
| `app/repositories/__init__.py` | Modified | Export book repository |
| `app/services/book_service.py` | Added | Book business logic |
| `app/services/__init__.py` | Modified | Export book service |
| `app/api/v1/books.py` | Modified | Complete books CRUD endpoints |
| `tests/integration/test_books.py` | Added | Book integration tests |

#### Multi-Vendor AI Model Support (Phase 2.5)
| File | Change Type | Description |
|------|-------------|-------------|
| `app/ai/base.py` | Added | AIProvider abstract base class, ModelConfig, ChatMessage, ChatResponse |
| `app/ai/__init__.py` | Modified | Model registry (17 models) and provider factory |
| `app/ai/providers/openai_provider.py` | Added | OpenAI GPT implementation |
| `app/ai/providers/qwen_provider.py` | Added | Qwen/Alibaba DashScope implementation |
| `app/ai/providers/anthropic_provider.py` | Added | Anthropic Claude implementation |
| `app/ai/providers/google_provider.py` | Added | Google Gemini implementation |
| `app/ai/providers/xai_provider.py` | Added | xAI Grok implementation |
| `app/ai/providers/deepseek_provider.py` | Added | DeepSeek implementation |
| `app/services/ai_model_router.py` | Added | Model routing based on book visibility |
| `app/config.py` | Modified | Added AI provider keys and model defaults |
| `app/schemas/user.py` | Modified | Added AIPreferences for user model selection |

#### Local Development Setup
| File | Change Type | Description |
|------|-------------|-------------|
| `scripts/dev.sh` | Added | Comprehensive local dev setup script |
| `.env.example` | Modified | Added all AI provider keys and model defaults |
| `README.md` | Modified | Fixed tech stack (Python/FastAPI), added Quick Start |

#### Documentation & Project Config
| File | Change Type | Description |
|------|-------------|-------------|
| `.gitignore` | Added | Python gitignore (pycache, venv, .env, etc.) |
| `CLAUDE.md` | Added | Project guidance for Claude Code |
| `CHANGELOG.md` | Added | This changelog file |
| `docs/PRICING.md` | Modified | Multi-vendor AI pricing tables |
| `docs/PRD.md` | Modified | Updated FR-AI-003 with multi-vendor requirements |
| `openapi/api-v1.yaml` | Modified | Added vendor field, expanded model enums |
| `pyproject.toml` | Modified | Added google-generativeai dependency |

### 🧠 **Rationale**

**Books CRUD:**
- Core feature required for all book-related functionality
- Storage abstraction enables local dev and cloud deployment
- Separation of concerns: models → repositories → services → API

**Multi-Vendor AI:**
- **Cost optimization**: Qwen ($0.40/1M) vs GPT-4o-mini ($0.75/1M) for public content
- **User choice**: Premium users can select preferred model
- **Vendor diversity**: Reduces single-provider dependency
- **Abstraction**: Easy to add new providers

**Local Dev Setup:**
- README was outdated (showed Node.js, actual stack is Python/FastAPI)
- Developers needed simple one-command setup
- `scripts/dev.sh` handles prerequisites, Docker, migrations, server startup

### 🔄 **Behavior / Compatibility Implications**

| Change | Impact |
|--------|--------|
| New book endpoints | Non-breaking - new functionality |
| AI model routing | Public books now use Qwen by default (cost savings) |
| User preferences | New `ai` field in user preferences (backward compatible) |
| Storage abstraction | Supports both local and Azure Blob |
| API spec | New `vendor` field in AI model responses |

### 🧪 **Testing Recommendations**

```bash
# 1. Test local dev setup
./scripts/dev.sh

# 2. Verify health
curl http://localhost:8000/health

# 3. Test books CRUD
TOKEN="<jwt-token>"

# Upload book
curl -X POST http://localhost:8000/v1/books \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.pdf" \
  -F "title=Test Book" \
  -F "category=technology"

# List books
curl http://localhost:8000/v1/books

# 4. Test AI model listing
curl http://localhost:8000/v1/ai/models

# 5. Run automated tests
./scripts/dev.sh test
```

### 📌 **Follow‑ups**
- [ ] Add integration tests for each AI provider
- [ ] Implement AI fallback when primary provider unavailable
- [ ] Add book processing worker (PDF text extraction, chunking)
- [ ] Implement semantic search with pgvector embeddings
- [ ] Add Windows PowerShell equivalent of dev.sh
- [ ] Add CI/CD workflow to validate dev script
