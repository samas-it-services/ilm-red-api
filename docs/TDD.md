# ILM Red API - Technical Design Document (TDD)

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 2.0.0 |
| **Last Updated** | January 2026 |
| **Status** | Active |
| **Related PRD** | [PRD.md](./PRD.md) |
| **Architecture** | [ARCHITECTURE.md](./ARCHITECTURE.md) |

---

## 1. Introduction

### 1.1 Purpose

This Technical Design Document provides detailed technical specifications for implementing the ILM Red API platform. It covers system architecture, service design, data models, and implementation guidelines.

### 1.2 Scope

- Backend API services (12 microservices)
- Database schema and data access patterns
- Authentication and authorization implementation
- Caching and search infrastructure
- Event-driven processing
- Deployment and operations

### 1.3 Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Runtime** | Node.js 20 LTS | TypeScript ecosystem, async I/O |
| **Framework** | Fastify | Performance, schema validation |
| **Language** | TypeScript 5.x | Type safety, developer experience |
| **Database** | Azure Cosmos DB | Global scale, multi-model |
| **Cache** | Azure Cache for Redis | Session, hot data |
| **Search** | Azure AI Search | Full-text, vector, semantic |
| **Storage** | Azure Blob Storage | Files, CDN integration |
| **Events** | Azure Event Hubs | High-throughput streaming |
| **Analytics** | Microsoft Fabric | Delta Lake, Power BI |
| **AI** | Azure OpenAI | GPT models, embeddings |
| **API Gateway** | Azure API Management | Rate limiting, auth |
| **Containers** | Azure Container Apps | Serverless, auto-scale |

---

## 2. System Architecture

### 2.1 Service Decomposition

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│                        (Azure API Management)                                │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │           │           │           │           │       │
        ▼           ▼           ▼           ▼           ▼       ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ...
   │  Auth   │ │  Books  │ │  Users  │ │  Search │ │   AI    │
   │ Service │ │ Service │ │ Service │ │ Service │ │ Service │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │           │
        └───────────┴───────────┴─────┬─────┴───────────┘
                                      │
                          ┌───────────┴───────────┐
                          │    Shared Services    │
                          ├───────────────────────┤
                          │ • Database Layer      │
                          │ • Cache Layer         │
                          │ • Event Publisher     │
                          │ • Logger              │
                          └───────────────────────┘
```

### 2.2 Services Overview

| Service | Responsibility | Port |
|---------|---------------|------|
| `auth-service` | Authentication, tokens, sessions | 3001 |
| `books-service` | Book CRUD, metadata, files | 3002 |
| `users-service` | Profiles, preferences, social | 3003 |
| `search-service` | Full-text, semantic, autocomplete | 3004 |
| `ai-service` | Chat sessions, model routing | 3005 |
| `clubs-service` | Book clubs, membership | 3006 |
| `progress-service` | Reading progress, sync | 3007 |
| `billing-service` | AI credits, transactions | 3008 |
| `analytics-service` | Metrics, reports | 3009 |
| `admin-service` | Moderation, audit logs | 3010 |
| `webhook-service` | Event delivery | 3011 |
| `worker-service` | Background jobs | 3012 |

### 2.3 Communication Patterns

```typescript
// Synchronous: Service-to-Service (gRPC/REST)
interface ServiceClient {
  // Used for real-time operations
  getUser(userId: string): Promise<User>;
  validateToken(token: string): Promise<TokenPayload>;
}

// Asynchronous: Event-Driven (Event Hubs)
interface EventPublisher {
  // Used for non-critical operations
  publish(event: DomainEvent): Promise<void>;
}

// Event Types
type DomainEvent =
  | { type: 'book.created'; data: BookCreatedPayload }
  | { type: 'book.updated'; data: BookUpdatedPayload }
  | { type: 'user.registered'; data: UserRegisteredPayload }
  | { type: 'progress.updated'; data: ProgressUpdatedPayload }
  | { type: 'ai.session.completed'; data: AISessionPayload };
```

---

## 3. Data Models

### 3.1 Core Entities

#### 3.1.1 User

```typescript
interface User {
  // Identity
  id: string;                    // UUID v4
  email: string;                 // Unique, lowercase
  emailVerified: boolean;

  // Profile
  username: string;              // Unique, URL-safe
  displayName: string;
  avatarUrl?: string;
  bio?: string;

  // Settings
  preferences: UserPreferences;

  // Roles & Permissions
  roles: UserRole[];
  permissions: string[];

  // Metadata
  status: 'active' | 'suspended' | 'deleted';
  createdAt: Date;
  updatedAt: Date;
  lastLoginAt?: Date;
}

interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;              // ISO 639-1
  timezone: string;              // IANA timezone
  notifications: NotificationSettings;
  privacy: PrivacySettings;
}

type UserRole = 'user' | 'premium' | 'moderator' | 'admin' | 'super_admin';
```

**Cosmos DB Container: `users`**
```json
{
  "id": "user_abc123",
  "partitionKey": "user_abc123",
  "type": "user",
  "email": "john@example.com",
  "username": "johndoe",
  "displayName": "John Doe",
  "roles": ["user", "premium"],
  "createdAt": "2024-01-15T10:30:00Z",
  "_ts": 1705314600
}
```

#### 3.1.2 Book

```typescript
interface Book {
  // Identity
  id: string;                    // UUID v4
  ownerId: string;               // User ID

  // Metadata
  title: string;
  author?: string;
  description?: string;
  category: BookCategory;
  language: string;              // ISO 639-1
  isbn?: string;
  publisher?: string;
  publishedYear?: number;

  // File Info
  file: FileInfo;
  thumbnail?: ThumbnailInfo;

  // Settings
  visibility: Visibility;
  aiEnabled: boolean;

  // Stats (denormalized for performance)
  stats: BookStats;

  // Vector embedding for semantic search
  embedding?: number[];          // 1536 dimensions

  // Metadata
  status: 'processing' | 'active' | 'deleted';
  createdAt: Date;
  updatedAt: Date;
}

interface FileInfo {
  path: string;                  // Blob storage path
  size: number;                  // Bytes
  mimeType: string;
  sha256: string;                // Integrity hash
  pageCount?: number;
  wordCount?: number;
}

interface BookStats {
  viewCount: number;
  favoriteCount: number;
  ratingSum: number;
  ratingCount: number;
  downloadCount: number;
}

type BookCategory =
  | 'religion' | 'islamic_studies' | 'quran_studies' | 'hadith'
  | 'fiqh' | 'history' | 'biography' | 'philosophy'
  | 'science' | 'technology' | 'education' | 'self_help'
  | 'fiction' | 'children' | 'languages' | 'other';

type Visibility = 'public' | 'private' | 'friends' | 'club';
```

**Cosmos DB Container: `books`**
```json
{
  "id": "book_xyz789",
  "partitionKey": "user_abc123",
  "type": "book",
  "ownerId": "user_abc123",
  "title": "Introduction to Machine Learning",
  "author": "Jane Smith",
  "category": "technology",
  "visibility": "public",
  "file": {
    "path": "books/user_abc123/book_xyz789.pdf",
    "size": 15728640,
    "mimeType": "application/pdf",
    "sha256": "abc123..."
  },
  "stats": {
    "viewCount": 1523,
    "favoriteCount": 89,
    "ratingSum": 356,
    "ratingCount": 82
  },
  "createdAt": "2024-01-15T10:30:00Z"
}
```

#### 3.1.3 Book Club

```typescript
interface BookClub {
  id: string;
  ownerId: string;

  // Details
  name: string;
  description?: string;
  coverImageUrl?: string;

  // Settings
  visibility: 'public' | 'private';
  joinPolicy: 'open' | 'approval' | 'invite_only';

  // Stats
  memberCount: number;
  bookCount: number;

  // Metadata
  createdAt: Date;
  updatedAt: Date;
}

interface ClubMembership {
  id: string;
  clubId: string;
  userId: string;
  role: 'owner' | 'admin' | 'moderator' | 'member';
  joinedAt: Date;
}
```

#### 3.1.4 AI Session

```typescript
interface AISession {
  id: string;
  userId: string;
  bookId: string;

  // Session State
  modelId: string;
  status: 'active' | 'completed' | 'archived';

  // Context
  contextChunks: string[];       // Relevant book excerpts

  // Usage
  totalTokens: number;
  totalCostUsd: number;

  // Metadata
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
}

interface AIMessage {
  id: string;
  sessionId: string;

  role: 'user' | 'assistant' | 'system';
  content: string;

  // For assistant messages
  citations?: Citation[];

  // Token usage
  promptTokens: number;
  completionTokens: number;
  costUsd: number;

  createdAt: Date;
}

interface Citation {
  page?: number;
  chapter?: string;
  excerpt: string;
  confidence: number;
}
```

#### 3.1.5 Reading Progress

```typescript
interface ReadingProgress {
  id: string;

  // Composite key
  userId: string;
  bookId: string;

  // Position
  currentPage: number;
  totalPages: number;
  percentage: number;

  // View settings
  scale: number;
  scrollPosition?: { x: number; y: number };

  // Stats
  readingTimeMinutes: number;
  completed: boolean;
  completedAt?: Date;

  // Sync metadata
  deviceId: string;
  updatedAt: Date;
}
```

### 3.2 Database Schema

#### 3.2.1 Cosmos DB Containers

| Container | Partition Key | Purpose |
|-----------|--------------|---------|
| `users` | `/id` | User profiles, preferences |
| `books` | `/ownerId` | Books (co-located with owner) |
| `clubs` | `/id` | Book clubs, membership |
| `progress` | `/userId` | Reading progress |
| `ai_sessions` | `/userId` | AI chat sessions |
| `ai_messages` | `/sessionId` | Chat messages |
| `events` | `/type` | Audit events (TTL: 90 days) |

#### 3.2.2 Indexing Policy

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {"path": "/title/?"},
    {"path": "/author/?"},
    {"path": "/category/?"},
    {"path": "/visibility/?"},
    {"path": "/createdAt/?"},
    {"path": "/stats/viewCount/?"}
  ],
  "excludedPaths": [
    {"path": "/description/*"},
    {"path": "/embedding/*"},
    {"path": "/_*"}
  ],
  "compositeIndexes": [
    [
      {"path": "/ownerId", "order": "ascending"},
      {"path": "/createdAt", "order": "descending"}
    ],
    [
      {"path": "/category", "order": "ascending"},
      {"path": "/stats/viewCount", "order": "descending"}
    ]
  ],
  "vectorIndexes": [
    {
      "path": "/embedding",
      "type": "quantizedFlat"
    }
  ]
}
```

### 3.3 Azure AI Search Index

```json
{
  "name": "books-index",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true, "filterable": true},
    {"name": "ownerId", "type": "Edm.String", "filterable": true},
    {"name": "title", "type": "Edm.String", "searchable": true, "analyzer": "standard.lucene"},
    {"name": "author", "type": "Edm.String", "searchable": true, "filterable": true, "facetable": true},
    {"name": "description", "type": "Edm.String", "searchable": true},
    {"name": "category", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "language", "type": "Edm.String", "filterable": true, "facetable": true},
    {"name": "visibility", "type": "Edm.String", "filterable": true},
    {"name": "tags", "type": "Collection(Edm.String)", "searchable": true, "filterable": true},
    {"name": "viewCount", "type": "Edm.Int64", "sortable": true, "filterable": true},
    {"name": "rating", "type": "Edm.Double", "sortable": true, "filterable": true},
    {"name": "createdAt", "type": "Edm.DateTimeOffset", "sortable": true, "filterable": true},
    {"name": "contentVector", "type": "Collection(Edm.Single)",
     "searchable": true, "dimensions": 1536, "vectorSearchProfile": "default"}
  ],
  "vectorSearch": {
    "profiles": [
      {"name": "default", "algorithm": "hnsw-algorithm"}
    ],
    "algorithms": [
      {
        "name": "hnsw-algorithm",
        "kind": "hnsw",
        "hnswParameters": {
          "m": 4,
          "efConstruction": 400,
          "efSearch": 500,
          "metric": "cosine"
        }
      }
    ]
  },
  "semantic": {
    "configurations": [
      {
        "name": "semantic-config",
        "prioritizedFields": {
          "titleField": {"fieldName": "title"},
          "contentFields": [{"fieldName": "description"}],
          "keywordsFields": [{"fieldName": "author"}, {"fieldName": "category"}]
        }
      }
    ]
  }
}
```

---

## 4. Service Implementations

### 4.1 Auth Service

#### 4.1.1 Authentication Flows

```typescript
// OAuth 2.0 Authorization Code Flow with PKCE
class AuthService {
  // Step 1: Generate authorization URL
  async getAuthorizationUrl(
    provider: 'google' | 'microsoft' | 'github',
    state: string,
    codeChallenge: string
  ): Promise<string> {
    const config = this.providerConfigs[provider];
    return `${config.authUrl}?` + new URLSearchParams({
      client_id: config.clientId,
      redirect_uri: config.redirectUri,
      response_type: 'code',
      scope: config.scopes.join(' '),
      state,
      code_challenge: codeChallenge,
      code_challenge_method: 'S256'
    });
  }

  // Step 2: Exchange code for tokens
  async exchangeCode(
    provider: string,
    code: string,
    codeVerifier: string
  ): Promise<TokenPair> {
    // Exchange with provider
    const providerTokens = await this.exchangeWithProvider(provider, code, codeVerifier);

    // Get or create user
    const userInfo = await this.getUserInfo(provider, providerTokens.accessToken);
    const user = await this.findOrCreateUser(userInfo);

    // Generate our tokens
    return this.generateTokenPair(user);
  }

  // Token generation
  async generateTokenPair(user: User): Promise<TokenPair> {
    const accessToken = await this.jwt.sign(
      {
        sub: user.id,
        email: user.email,
        roles: user.roles,
        permissions: user.permissions
      },
      { expiresIn: '15m' }
    );

    const refreshToken = await this.generateRefreshToken(user.id);

    return { accessToken, refreshToken };
  }

  // Token refresh
  async refreshTokens(refreshToken: string): Promise<TokenPair> {
    const stored = await this.cache.get(`refresh:${hash(refreshToken)}`);
    if (!stored) {
      throw new UnauthorizedError('Invalid refresh token');
    }

    // Rotate refresh token
    await this.cache.delete(`refresh:${hash(refreshToken)}`);

    const user = await this.userService.getById(stored.userId);
    return this.generateTokenPair(user);
  }
}
```

#### 4.1.2 API Key Management

```typescript
class APIKeyService {
  // Generate new API key
  async create(userId: string, name: string, permissions: string[]): Promise<APIKey> {
    // Generate key with prefix
    const keyValue = `ilm_${this.env}_${crypto.randomBytes(32).toString('hex')}`;
    const keyHash = await argon2.hash(keyValue);

    const apiKey: APIKey = {
      id: uuid(),
      userId,
      name,
      keyPrefix: keyValue.substring(0, 12),
      keyHash,
      permissions,
      lastUsedAt: null,
      createdAt: new Date()
    };

    await this.db.create('api_keys', apiKey);

    // Return full key only once
    return { ...apiKey, key: keyValue };
  }

  // Validate API key
  async validate(keyValue: string): Promise<APIKeyValidation> {
    const prefix = keyValue.substring(0, 12);
    const candidates = await this.db.query('api_keys', {
      filter: { keyPrefix: prefix }
    });

    for (const candidate of candidates) {
      if (await argon2.verify(candidate.keyHash, keyValue)) {
        // Update last used
        await this.db.update('api_keys', candidate.id, {
          lastUsedAt: new Date(),
          usageCount: candidate.usageCount + 1
        });

        return {
          valid: true,
          userId: candidate.userId,
          permissions: candidate.permissions
        };
      }
    }

    return { valid: false };
  }
}
```

### 4.2 Books Service

#### 4.2.1 Book Upload Flow

```typescript
class BooksService {
  async uploadBook(
    userId: string,
    file: UploadedFile,
    metadata: BookMetadata
  ): Promise<Book> {
    // 1. Validate file
    await this.validateFile(file);

    // 2. Check user limits
    await this.checkUploadLimits(userId);

    // 3. Calculate hash for deduplication
    const sha256 = await this.calculateHash(file.buffer);
    const existing = await this.findByHash(userId, sha256);
    if (existing) {
      throw new ConflictError('File already uploaded');
    }

    // 4. Upload to blob storage
    const blobPath = `books/${userId}/${uuid()}${extname(file.name)}`;
    await this.storage.upload(blobPath, file.buffer, {
      contentType: file.mimeType,
      metadata: { userId, sha256 }
    });

    // 5. Create book record
    const book: Book = {
      id: uuid(),
      ownerId: userId,
      title: metadata.title,
      author: metadata.author,
      description: metadata.description,
      category: metadata.category || 'other',
      language: this.detectLanguage(file.name),
      visibility: metadata.visibility || 'private',
      aiEnabled: true,
      file: {
        path: blobPath,
        size: file.size,
        mimeType: file.mimeType,
        sha256
      },
      stats: {
        viewCount: 0,
        favoriteCount: 0,
        ratingSum: 0,
        ratingCount: 0,
        downloadCount: 0
      },
      status: 'processing',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    await this.db.create('books', book);

    // 6. Publish event for async processing
    await this.events.publish({
      type: 'book.created',
      data: {
        bookId: book.id,
        userId,
        blobPath,
        mimeType: file.mimeType
      }
    });

    return book;
  }

  // Async processing (triggered by event)
  async processBook(bookId: string): Promise<void> {
    const book = await this.getById(bookId);

    // Generate thumbnail
    const thumbnailUrl = await this.thumbnailService.generate(book.file.path);

    // Extract text for search
    const text = await this.textExtractor.extract(book.file.path);

    // Generate embedding for semantic search
    const embedding = await this.aiService.generateEmbedding(text);

    // Get page count
    const pageCount = await this.pdfService.getPageCount(book.file.path);

    // Update book
    await this.db.update('books', bookId, {
      thumbnail: { url: thumbnailUrl },
      file: { ...book.file, pageCount },
      embedding,
      status: 'active'
    });

    // Index in search
    await this.searchService.indexBook(book.id);
  }
}
```

#### 4.2.2 Book Query Patterns

```typescript
class BooksQueryService {
  // Get books with filters
  async getBooks(userId: string, options: GetBooksOptions): Promise<PaginatedResult<Book>> {
    const { visibility, category, language, sort, page, limit } = options;

    // Build query based on visibility
    const query = this.buildVisibilityQuery(userId, visibility);

    if (category) {
      query.filter.category = { $in: category };
    }
    if (language) {
      query.filter.language = language;
    }

    // Sort
    const sortMap: Record<string, object> = {
      'createdAt': { createdAt: -1 },
      'title': { title: 1 },
      'rating': { 'stats.ratingSum': -1 },
      'views': { 'stats.viewCount': -1 }
    };
    query.sort = sortMap[sort] || sortMap.createdAt;

    // Execute with pagination
    const [items, total] = await Promise.all([
      this.db.query('books', query, { skip: (page - 1) * limit, limit }),
      this.db.count('books', query.filter)
    ]);

    return {
      data: items,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasMore: page * limit < total
      }
    };
  }

  private buildVisibilityQuery(userId: string, requestedVisibility?: string) {
    // Base: user's own books
    const ownBooks = { ownerId: userId };

    // Public books
    const publicBooks = { visibility: 'public' };

    // Friends' books (if requesting friends visibility)
    // TODO: Implement friends lookup

    return {
      filter: {
        $or: [ownBooks, publicBooks]
      }
    };
  }
}
```

### 4.3 Search Service

#### 4.3.1 Multi-Type Search

```typescript
class SearchService {
  async search(query: string, options: SearchOptions): Promise<SearchResults> {
    const { types = ['books', 'users', 'clubs'], limit = 10 } = options;

    // Parallel search across types
    const results = await Promise.all([
      types.includes('books') ? this.searchBooks(query, limit) : [],
      types.includes('users') ? this.searchUsers(query, limit) : [],
      types.includes('clubs') ? this.searchClubs(query, limit) : []
    ]);

    return {
      books: results[0],
      users: results[1],
      clubs: results[2],
      query,
      took: Date.now() - startTime
    };
  }

  async searchBooks(query: string, limit: number): Promise<BookSearchResult[]> {
    // Try cache first
    const cacheKey = `search:books:${hash(query)}:${limit}`;
    const cached = await this.cache.get(cacheKey);
    if (cached) return cached;

    // Azure AI Search
    const searchResults = await this.aiSearch.search('books-index', {
      search: query,
      searchMode: 'all',
      queryType: 'semantic',
      semanticConfiguration: 'semantic-config',
      top: limit,
      select: ['id', 'title', 'author', 'category', 'thumbnailUrl', 'rating'],
      orderby: '@search.score desc, viewCount desc'
    });

    const results = searchResults.results.map(r => ({
      id: r.document.id,
      title: r.document.title,
      author: r.document.author,
      category: r.document.category,
      thumbnailUrl: r.document.thumbnailUrl,
      rating: r.document.rating,
      score: r['@search.score'],
      highlights: r['@search.highlights']
    }));

    // Cache for 5 minutes
    await this.cache.set(cacheKey, results, 300);

    return results;
  }

  // Semantic search with vectors
  async semanticSearch(query: string, limit: number): Promise<BookSearchResult[]> {
    // Generate embedding for query
    const queryEmbedding = await this.aiService.generateEmbedding(query);

    // Vector search in Azure AI Search
    const results = await this.aiSearch.search('books-index', {
      vectors: [{
        value: queryEmbedding,
        fields: 'contentVector',
        k: limit
      }],
      select: ['id', 'title', 'author', 'description']
    });

    return results.results.map(r => ({
      ...r.document,
      score: r['@search.score']
    }));
  }
}
```

### 4.4 AI Service

#### 4.4.1 Chat Implementation

```typescript
class AIService {
  private readonly models: Map<string, ModelConfig> = new Map([
    ['gpt-4o', { provider: 'openai', model: 'gpt-4o', inputCost: 5, outputCost: 15 }],
    ['gpt-4o-mini', { provider: 'openai', model: 'gpt-4o-mini', inputCost: 0.15, outputCost: 0.60 }],
    ['claude-3-sonnet', { provider: 'anthropic', model: 'claude-3-sonnet-20240229', inputCost: 3, outputCost: 15 }]
  ]);

  async chat(
    sessionId: string,
    userMessage: string,
    modelId: string = 'gpt-4o-mini'
  ): Promise<AIResponse> {
    const session = await this.getSession(sessionId);
    const modelConfig = this.models.get(modelId);

    // Get relevant context from book
    const context = await this.getRelevantContext(session.bookId, userMessage);

    // Build messages
    const messages = [
      {
        role: 'system',
        content: this.buildSystemPrompt(session.bookId, context)
      },
      ...await this.getMessageHistory(sessionId),
      { role: 'user', content: userMessage }
    ];

    // Call AI provider
    const response = await this.callProvider(modelConfig, messages);

    // Extract citations
    const citations = this.extractCitations(response.content, context);

    // Calculate cost with 40% markup
    const costUsd = this.calculateCost(
      response.usage.promptTokens,
      response.usage.completionTokens,
      modelConfig
    ) * 1.4;

    // Save message
    const message: AIMessage = {
      id: uuid(),
      sessionId,
      role: 'assistant',
      content: response.content,
      citations,
      promptTokens: response.usage.promptTokens,
      completionTokens: response.usage.completionTokens,
      costUsd,
      createdAt: new Date()
    };

    await this.saveMessage(message);
    await this.updateSessionUsage(sessionId, message);
    await this.billUser(session.userId, costUsd);

    return {
      message,
      usage: response.usage
    };
  }

  private async getRelevantContext(bookId: string, query: string): Promise<string[]> {
    // Get book text chunks
    const chunks = await this.bookService.getTextChunks(bookId);

    // Generate query embedding
    const queryEmbedding = await this.generateEmbedding(query);

    // Find most relevant chunks using cosine similarity
    const ranked = chunks
      .map(chunk => ({
        chunk,
        similarity: this.cosineSimilarity(queryEmbedding, chunk.embedding)
      }))
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, 5);

    return ranked.map(r => r.chunk.text);
  }

  private buildSystemPrompt(bookId: string, context: string[]): string {
    return `You are an AI assistant helping users understand and discuss a book.

Use the following excerpts from the book to answer questions. Always cite the relevant
passages when making claims about the book's content.

Book Context:
${context.map((c, i) => `[${i + 1}] ${c}`).join('\n\n')}

Guidelines:
- Answer based on the provided context when possible
- If the context doesn't contain the answer, say so
- Provide page numbers or chapter references when citing
- Be concise but thorough`;
  }
}
```

### 4.5 Event Processing

#### 4.5.1 Event Publisher

```typescript
class EventPublisher {
  private readonly eventHub: EventHubProducerClient;

  async publish(event: DomainEvent): Promise<void> {
    const eventData: EventData = {
      body: JSON.stringify({
        id: uuid(),
        type: event.type,
        timestamp: new Date().toISOString(),
        data: event.data
      }),
      properties: {
        eventType: event.type,
        version: '1.0'
      }
    };

    await this.eventHub.sendBatch([eventData]);

    // Also update real-time analytics
    await this.updateRealTimeMetrics(event);
  }

  private async updateRealTimeMetrics(event: DomainEvent): Promise<void> {
    const hourKey = `metrics:${event.type}:${format(new Date(), 'yyyy-MM-dd-HH')}`;
    await this.cache.incr(hourKey);
    await this.cache.expire(hourKey, 86400); // 24 hours
  }
}
```

#### 4.5.2 Event Consumers

```typescript
class EventConsumer {
  private readonly handlers: Map<string, EventHandler> = new Map([
    ['book.created', new BookCreatedHandler()],
    ['book.updated', new BookUpdatedHandler()],
    ['user.registered', new UserRegisteredHandler()],
    ['ai.session.completed', new AISessionCompletedHandler()]
  ]);

  async start(): Promise<void> {
    const consumer = new EventHubConsumerClient(
      '$Default',
      connectionString,
      eventHubName
    );

    consumer.subscribe({
      processEvents: async (events) => {
        for (const event of events) {
          try {
            const parsed = JSON.parse(event.body.toString());
            const handler = this.handlers.get(parsed.type);

            if (handler) {
              await handler.handle(parsed.data);
            }
          } catch (error) {
            this.logger.error('Event processing failed', { event, error });
            // Dead letter queue for failed events
            await this.dlq.send(event);
          }
        }
      },
      processError: async (err) => {
        this.logger.error('Event Hub error', { error: err });
      }
    });
  }
}

// Handler implementations
class BookCreatedHandler implements EventHandler {
  async handle(data: BookCreatedPayload): Promise<void> {
    // 1. Generate thumbnail
    await this.thumbnailService.generate(data.bookId);

    // 2. Extract text
    await this.textExtractor.process(data.bookId);

    // 3. Generate embeddings
    await this.embeddingService.generate(data.bookId);

    // 4. Index for search
    await this.searchService.index(data.bookId);

    // 5. Send to Fabric for analytics
    await this.fabricSink.send({
      eventType: 'book_created',
      bookId: data.bookId,
      userId: data.userId,
      timestamp: new Date()
    });
  }
}
```

### 4.6 Page Image Service

#### 4.6.1 Data Models

```typescript
interface PageImage {
  id: string;                    // UUID v4
  bookId: string;
  pageNumber: number;            // 1-indexed

  // Original dimensions
  originalWidth: number;
  originalHeight: number;
  aspectRatio: number;

  // Storage paths (relative to blob container)
  paths: {
    thumbnail: string;           // 150px width
    medium: string;              // 800px width
    highRes: string;             // 1600px width
    ultra: string;               // 3200px width
  };

  // File sizes in bytes
  fileSizes: {
    thumbnail: number;
    medium: number;
    highRes: number;
    ultra: number;
  };

  // Processing status
  status: 'pending' | 'processing' | 'completed' | 'failed';
  errorMessage?: string;

  // Metadata
  createdAt: Date;
  updatedAt: Date;
}

interface PageGenerationJob {
  id: string;                    // UUID v4
  bookId: string;
  userId: string;

  // Progress
  status: 'queued' | 'processing' | 'completed' | 'partial' | 'failed';
  totalPages: number;
  completedPages: number;
  failedPages: number;

  // Error tracking
  errors: Array<{
    pageNumber: number;
    message: string;
    timestamp: Date;
  }>;

  // Timing
  queuedAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  estimatedCompletion?: Date;
}

interface BookCover {
  id: string;                    // UUID v4
  bookId: string;

  // Cover source
  isCustom: boolean;             // true = user uploaded, false = auto from page 1
  path: string;                  // Blob storage path

  // Image properties
  mimeType: string;              // image/jpeg, image/png, image/webp
  width: number;
  height: number;
  fileSize: number;              // bytes

  // Metadata
  uploadedAt: Date;
  updatedAt: Date;
}
```

#### 4.6.2 Resolution Specifications

| Resolution | Width | Quality | Format | Use Case | Typical Size |
|------------|-------|---------|--------|----------|--------------|
| thumbnail  | 150px | 70%     | JPEG   | Navigation, grids, lists | 10-25 KB |
| medium     | 800px | 85%     | JPEG   | Mobile reading, preview | 60-120 KB |
| high-res   | 1600px| 92%     | JPEG   | Desktop reading, normal zoom | 180-350 KB |
| ultra      | 3200px| 95%     | JPEG   | High-DPI, deep zoom, print | 500-1000 KB |

```typescript
const RESOLUTION_CONFIG = {
  thumbnail: { width: 150, quality: 70, suffix: 'thumb' },
  medium: { width: 800, quality: 85, suffix: 'med' },
  highRes: { width: 1600, quality: 92, suffix: 'high' },
  ultra: { width: 3200, quality: 95, suffix: 'ultra' }
} as const;

type Resolution = keyof typeof RESOLUTION_CONFIG;
```

#### 4.6.3 Page Image Service Implementation

```typescript
import { createCanvas } from 'canvas';
import * as pdfjs from 'pdfjs-dist';

class PageImageService {
  private readonly storage: StorageProvider;
  private readonly db: DatabaseProvider;
  private readonly events: EventPublisher;

  // Generate all page images for a book
  async generatePages(bookId: string, userId: string): Promise<PageGenerationJob> {
    const book = await this.db.findById('books', bookId);
    if (!book) throw new NotFoundError('Book not found');

    // Create job record
    const job: PageGenerationJob = {
      id: uuid(),
      bookId,
      userId,
      status: 'queued',
      totalPages: 0,
      completedPages: 0,
      failedPages: 0,
      errors: [],
      queuedAt: new Date()
    };

    await this.db.create('page_generation_jobs', job);

    // Publish event for async processing
    await this.events.publish({
      type: 'book.pages.generation.queued',
      data: { jobId: job.id, bookId, userId }
    });

    return job;
  }

  // Process pages (called by worker)
  async processPages(jobId: string): Promise<void> {
    const job = await this.db.findById('page_generation_jobs', jobId);
    if (!job) throw new NotFoundError('Job not found');

    // Update status to processing
    await this.updateJobStatus(jobId, 'processing', { startedAt: new Date() });

    // Emit started event
    await this.events.publish({
      type: 'book.pages.generation.started',
      data: { jobId, bookId: job.bookId }
    });

    try {
      // Load PDF
      const book = await this.db.findById('books', job.bookId);
      const pdfBuffer = await this.storage.download(book.file.path);
      const pdf = await pdfjs.getDocument({ data: pdfBuffer }).promise;

      const totalPages = pdf.numPages;
      await this.db.update('page_generation_jobs', jobId, { totalPages });

      // Process in batches for memory efficiency
      const BATCH_SIZE = 10;
      for (let batch = 0; batch < Math.ceil(totalPages / BATCH_SIZE); batch++) {
        const startPage = batch * BATCH_SIZE + 1;
        const endPage = Math.min(startPage + BATCH_SIZE - 1, totalPages);

        await this.processBatch(jobId, job.bookId, pdf, startPage, endPage);

        // Emit progress event
        const progress = await this.getJobProgress(jobId);
        if (progress.percentage % 10 === 0) {
          await this.events.publish({
            type: 'book.pages.generation.progress',
            data: { jobId, bookId: job.bookId, progress }
          });
        }
      }

      // Final status
      const finalJob = await this.db.findById('page_generation_jobs', jobId);
      const finalStatus = finalJob.failedPages > 0 ? 'partial' : 'completed';

      await this.updateJobStatus(jobId, finalStatus, { completedAt: new Date() });

      await this.events.publish({
        type: 'book.pages.generation.completed',
        data: { jobId, bookId: job.bookId, status: finalStatus }
      });

    } catch (error) {
      await this.updateJobStatus(jobId, 'failed', {
        completedAt: new Date(),
        errors: [...job.errors, { pageNumber: 0, message: error.message, timestamp: new Date() }]
      });

      await this.events.publish({
        type: 'book.pages.generation.failed',
        data: { jobId, bookId: job.bookId, error: error.message }
      });
    }
  }

  private async processBatch(
    jobId: string,
    bookId: string,
    pdf: pdfjs.PDFDocumentProxy,
    startPage: number,
    endPage: number
  ): Promise<void> {
    for (let pageNum = startPage; pageNum <= endPage; pageNum++) {
      try {
        await this.processPage(bookId, pdf, pageNum);
        await this.db.update('page_generation_jobs', jobId, {
          completedPages: { $inc: 1 }
        });
      } catch (error) {
        await this.db.update('page_generation_jobs', jobId, {
          failedPages: { $inc: 1 },
          errors: { $push: { pageNumber: pageNum, message: error.message, timestamp: new Date() } }
        });
      }
    }
  }

  private async processPage(
    bookId: string,
    pdf: pdfjs.PDFDocumentProxy,
    pageNumber: number
  ): Promise<PageImage> {
    const page = await pdf.getPage(pageNumber);
    const viewport = page.getViewport({ scale: 1.0 });

    // Get original dimensions
    const originalWidth = viewport.width;
    const originalHeight = viewport.height;
    const aspectRatio = originalWidth / originalHeight;

    const paths: PageImage['paths'] = {} as PageImage['paths'];
    const fileSizes: PageImage['fileSizes'] = {} as PageImage['fileSizes'];

    // Render at each resolution
    for (const [key, config] of Object.entries(RESOLUTION_CONFIG)) {
      const resolution = key as Resolution;
      const { buffer, size } = await this.renderPage(page, viewport, config);

      // Upload to storage
      const blobPath = `books/${bookId}/pages/${config.suffix}/${pageNumber}.jpg`;
      await this.storage.upload(blobPath, buffer, {
        contentType: 'image/jpeg',
        cacheControl: 'public, max-age=31536000, immutable'
      });

      paths[resolution] = blobPath;
      fileSizes[resolution] = size;
    }

    // Create page record
    const pageImage: PageImage = {
      id: uuid(),
      bookId,
      pageNumber,
      originalWidth,
      originalHeight,
      aspectRatio,
      paths,
      fileSizes,
      status: 'completed',
      createdAt: new Date(),
      updatedAt: new Date()
    };

    await this.db.create('page_images', pageImage);

    // Generate cover from page 1
    if (pageNumber === 1) {
      await this.generateAutoCover(bookId, paths.medium);
    }

    return pageImage;
  }

  private async renderPage(
    page: pdfjs.PDFPageProxy,
    viewport: pdfjs.PageViewport,
    config: { width: number; quality: number }
  ): Promise<{ buffer: Buffer; size: number }> {
    // Calculate scale to achieve target width
    const scale = config.width / viewport.width;
    const scaledViewport = page.getViewport({ scale });

    // Create canvas
    const canvas = createCanvas(scaledViewport.width, scaledViewport.height);
    const context = canvas.getContext('2d');

    // Render PDF page to canvas
    await page.render({
      canvasContext: context as any,
      viewport: scaledViewport
    }).promise;

    // Convert to JPEG
    const buffer = canvas.toBuffer('image/jpeg', { quality: config.quality / 100 });

    return { buffer, size: buffer.length };
  }

  // Generate thumbnail from page 1
  private async generateThumbnail(bookId: string): Promise<void> {
    const page1 = await this.db.findOne('page_images', { bookId, pageNumber: 1 });
    if (page1) {
      await this.db.update('books', bookId, {
        thumbnail: {
          url: page1.paths.thumbnail,
          width: 150,
          height: Math.round(150 / page1.aspectRatio)
        }
      });
    }
  }

  // Auto-generate cover from page 1
  private async generateAutoCover(bookId: string, sourcePath: string): Promise<void> {
    // Check if custom cover exists
    const existingCover = await this.db.findOne('book_covers', { bookId, isCustom: true });
    if (existingCover) return;

    // Copy medium resolution as cover
    const coverPath = `books/${bookId}/cover.jpg`;
    await this.storage.copy(sourcePath, coverPath);

    const cover: BookCover = {
      id: uuid(),
      bookId,
      isCustom: false,
      path: coverPath,
      mimeType: 'image/jpeg',
      width: 800,
      height: 0, // Will be updated from source
      fileSize: 0,
      uploadedAt: new Date(),
      updatedAt: new Date()
    };

    await this.db.upsert('book_covers', { bookId }, cover);

    await this.events.publish({
      type: 'book.cover.updated',
      data: { bookId, isCustom: false }
    });
  }
}
```

#### 4.6.4 Cover Service Implementation

```typescript
class CoverService {
  // Upload custom cover
  async uploadCover(bookId: string, userId: string, file: UploadedFile): Promise<BookCover> {
    // Validate ownership
    const book = await this.db.findById('books', bookId);
    if (book.ownerId !== userId) throw new ForbiddenError('Not your book');

    // Validate file
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.mimeType)) {
      throw new ValidationError('Invalid image format');
    }
    if (file.size > 10 * 1024 * 1024) {
      throw new ValidationError('Cover exceeds 10MB limit');
    }

    // Get image dimensions
    const dimensions = await this.getImageDimensions(file.buffer);

    // Resize to standard width if needed
    let finalBuffer = file.buffer;
    if (dimensions.width > 800) {
      finalBuffer = await this.resizeImage(file.buffer, 800);
    }

    // Upload to storage
    const coverPath = `books/${bookId}/cover-custom.${this.getExtension(file.mimeType)}`;
    await this.storage.upload(coverPath, finalBuffer, {
      contentType: file.mimeType,
      cacheControl: 'public, max-age=3600'
    });

    // Create/update cover record
    const cover: BookCover = {
      id: uuid(),
      bookId,
      isCustom: true,
      path: coverPath,
      mimeType: file.mimeType,
      width: Math.min(dimensions.width, 800),
      height: dimensions.height * (Math.min(dimensions.width, 800) / dimensions.width),
      fileSize: finalBuffer.length,
      uploadedAt: new Date(),
      updatedAt: new Date()
    };

    await this.db.upsert('book_covers', { bookId }, cover);

    await this.events.publish({
      type: 'book.cover.updated',
      data: { bookId, isCustom: true }
    });

    return cover;
  }

  // Delete custom cover (reverts to auto)
  async deleteCover(bookId: string, userId: string): Promise<void> {
    const book = await this.db.findById('books', bookId);
    if (book.ownerId !== userId) throw new ForbiddenError('Not your book');

    const cover = await this.db.findOne('book_covers', { bookId });
    if (!cover?.isCustom) {
      throw new ValidationError('No custom cover to delete');
    }

    // Delete custom cover from storage
    await this.storage.delete(cover.path);

    // Revert to auto-generated cover
    const page1 = await this.db.findOne('page_images', { bookId, pageNumber: 1 });
    if (page1) {
      await this.generateAutoCover(bookId, page1.paths.medium);
    } else {
      await this.db.delete('book_covers', { bookId });
    }

    await this.events.publish({
      type: 'book.cover.updated',
      data: { bookId, isCustom: false }
    });
  }

  // Get cover with signed URL
  async getCover(bookId: string): Promise<{ cover: BookCover; url: string }> {
    const cover = await this.db.findOne('book_covers', { bookId });
    if (!cover) throw new NotFoundError('Cover not found');

    const url = await this.storage.getSignedUrl(cover.path, 3600);

    return { cover, url };
  }
}
```

#### 4.6.5 Page Query Service

```typescript
class PageQueryService {
  // List all pages for a book
  async listPages(
    bookId: string,
    options: { page?: number; limit?: number; resolution?: Resolution }
  ): Promise<PaginatedResult<PageImageWithUrl>> {
    const { page = 1, limit = 50, resolution } = options;

    // Verify book access
    const book = await this.db.findById('books', bookId);
    if (!book) throw new NotFoundError('Book not found');

    // Query pages
    const query = { bookId, status: 'completed' };
    const [pages, total] = await Promise.all([
      this.db.query('page_images', query, {
        sort: { pageNumber: 1 },
        skip: (page - 1) * limit,
        limit
      }),
      this.db.count('page_images', query)
    ]);

    // Generate signed URLs
    const pagesWithUrls = await Promise.all(
      pages.map(async (p) => ({
        ...p,
        urls: resolution
          ? { [resolution]: await this.storage.getSignedUrl(p.paths[resolution], 3600) }
          : await this.getAllSignedUrls(p.paths)
      }))
    );

    // Get generation status
    const job = await this.db.findOne('page_generation_jobs', { bookId }, { sort: { queuedAt: -1 } });

    return {
      data: pagesWithUrls,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasMore: page * limit < total
      },
      metadata: {
        totalPages: book.file.pageCount || total,
        generationStatus: job?.status || 'unknown'
      }
    };
  }

  // Get specific page
  async getPage(
    bookId: string,
    pageNumber: number,
    resolution?: Resolution
  ): Promise<PageImageWithUrl> {
    const page = await this.db.findOne('page_images', { bookId, pageNumber });
    if (!page) throw new NotFoundError('Page not found');

    const urls = resolution
      ? { [resolution]: await this.storage.getSignedUrl(page.paths[resolution], 3600) }
      : await this.getAllSignedUrls(page.paths);

    return { ...page, urls };
  }

  private async getAllSignedUrls(
    paths: PageImage['paths']
  ): Promise<Record<Resolution, string>> {
    const entries = await Promise.all(
      Object.entries(paths).map(async ([key, path]) => [
        key,
        await this.storage.getSignedUrl(path, 3600)
      ])
    );
    return Object.fromEntries(entries);
  }
}
```

#### 4.6.6 Cosmos DB Container Configuration

**Container: `page_images`**
```json
{
  "id": "page_images",
  "partitionKey": { "paths": ["/bookId"] },
  "indexingPolicy": {
    "automatic": true,
    "includedPaths": [
      { "path": "/pageNumber/?" },
      { "path": "/status/?" },
      { "path": "/createdAt/?" }
    ],
    "excludedPaths": [
      { "path": "/paths/*" },
      { "path": "/fileSizes/*" }
    ]
  },
  "defaultTtl": -1
}
```

**Container: `page_generation_jobs`**
```json
{
  "id": "page_generation_jobs",
  "partitionKey": { "paths": ["/bookId"] },
  "defaultTtl": 604800
}
```

**Container: `book_covers`**
```json
{
  "id": "book_covers",
  "partitionKey": { "paths": ["/bookId"] }
}
```

---

## 5. Caching Strategy

### 5.1 Cache Layers

```typescript
class CacheService {
  private readonly redis: Redis;
  private readonly localCache: LRUCache<string, any>;

  // L1: Local memory cache (100ms TTL, hot path)
  // L2: Redis distributed cache (5-60 min TTL)
  // L3: Database (source of truth)

  async get<T>(key: string, options?: CacheOptions): Promise<T | null> {
    // L1: Check local cache
    const local = this.localCache.get(key);
    if (local) {
      return local as T;
    }

    // L2: Check Redis
    const cached = await this.redis.get(key);
    if (cached) {
      const value = JSON.parse(cached);
      // Populate L1
      this.localCache.set(key, value);
      return value as T;
    }

    return null;
  }

  async set<T>(key: string, value: T, ttlSeconds: number = 300): Promise<void> {
    // Set in both L1 and L2
    this.localCache.set(key, value);
    await this.redis.setex(key, ttlSeconds, JSON.stringify(value));
  }

  async invalidate(pattern: string): Promise<void> {
    // Clear local cache
    this.localCache.clear();

    // Clear Redis by pattern
    const keys = await this.redis.keys(pattern);
    if (keys.length > 0) {
      await this.redis.del(...keys);
    }
  }
}
```

### 5.2 Cache Key Patterns

| Pattern | TTL | Purpose |
|---------|-----|---------|
| `user:{id}` | 5 min | User profile |
| `user:{id}:books` | 2 min | User's book list |
| `book:{id}` | 5 min | Book metadata |
| `book:{id}:stats` | 1 min | View/rating counts |
| `search:{hash}` | 5 min | Search results |
| `rate:{userId}:{minute}` | 2 min | Rate limit counter |
| `session:{token}` | 15 min | Auth session |

---

## 6. Security Implementation

### 6.1 Input Validation

```typescript
// Using Zod for runtime validation
const BookCreateSchema = z.object({
  title: z.string().min(1).max(500),
  author: z.string().max(200).optional(),
  description: z.string().max(5000).optional(),
  category: z.enum(BOOK_CATEGORIES),
  visibility: z.enum(['public', 'private', 'friends']).default('private'),
  language: z.string().length(2).optional()
});

// Fastify plugin for validation
fastify.addHook('preValidation', async (request) => {
  if (request.routerMethod === 'POST' && request.url.includes('/books')) {
    const result = BookCreateSchema.safeParse(request.body);
    if (!result.success) {
      throw new ValidationError(result.error.issues);
    }
    request.body = result.data;
  }
});
```

### 6.2 Rate Limiting

```typescript
class RateLimiter {
  async check(userId: string, endpoint: string): Promise<RateLimitResult> {
    const tier = await this.getUserTier(userId);
    const limits = RATE_LIMITS[tier];

    const minute = Math.floor(Date.now() / 60000);
    const key = `rate:${userId}:${endpoint}:${minute}`;

    const current = await this.cache.incr(key);
    await this.cache.expire(key, 120);

    if (current > limits[endpoint]) {
      return {
        allowed: false,
        limit: limits[endpoint],
        remaining: 0,
        resetAt: (minute + 1) * 60000
      };
    }

    return {
      allowed: true,
      limit: limits[endpoint],
      remaining: limits[endpoint] - current,
      resetAt: (minute + 1) * 60000
    };
  }
}

const RATE_LIMITS = {
  free: { default: 60, search: 30, ai: 10 },
  premium: { default: 300, search: 100, ai: 50 },
  enterprise: { default: 1000, search: 500, ai: 200 }
};
```

### 6.3 Audit Logging

```typescript
class AuditLogger {
  async log(event: AuditEvent): Promise<void> {
    const log: AuditLog = {
      id: uuid(),
      timestamp: new Date(),
      userId: event.userId,
      action: event.action,
      resourceType: event.resourceType,
      resourceId: event.resourceId,
      changes: event.changes,
      metadata: {
        ipAddress: event.ipAddress,
        userAgent: event.userAgent,
        requestId: event.requestId
      }
    };

    // Write to database
    await this.db.create('audit_logs', log);

    // Send to Fabric for long-term storage
    await this.fabricSink.send({
      table: 'audit_logs',
      data: log
    });

    // Alert on sensitive actions
    if (SENSITIVE_ACTIONS.includes(event.action)) {
      await this.alertService.send({
        type: 'sensitive_action',
        data: log
      });
    }
  }
}
```

---

## 7. Testing Strategy

### 7.1 Test Pyramid

```
                    ┌─────────────────┐
                    │    E2E Tests    │  10%
                    │   (Playwright)  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │     Integration Tests       │  20%
              │    (Supertest + TestDb)     │
              └──────────────┬──────────────┘
                             │
       ┌─────────────────────┴─────────────────────┐
       │              Unit Tests                    │  70%
       │          (Vitest + Mocks)                  │
       └───────────────────────────────────────────┘
```

### 7.2 Test Examples

```typescript
// Unit Test
describe('BooksService', () => {
  describe('uploadBook', () => {
    it('should reject files exceeding size limit', async () => {
      const service = new BooksService(mockDb, mockStorage, mockEvents);
      const largeFile = createMockFile({ size: 600 * 1024 * 1024 }); // 600MB

      await expect(service.uploadBook('user1', largeFile, {}))
        .rejects.toThrow('File exceeds maximum size');
    });

    it('should detect duplicate files by hash', async () => {
      mockDb.findOne.mockResolvedValue({ id: 'existing' });

      const file = createMockFile({ content: 'test content' });

      await expect(service.uploadBook('user1', file, {}))
        .rejects.toThrow('File already uploaded');
    });
  });
});

// Integration Test
describe('Books API', () => {
  beforeAll(async () => {
    await setupTestDatabase();
  });

  afterAll(async () => {
    await teardownTestDatabase();
  });

  describe('POST /v1/books', () => {
    it('should create book and return 201', async () => {
      const response = await request(app)
        .post('/v1/books')
        .set('Authorization', `Bearer ${testUserToken}`)
        .attach('file', 'test/fixtures/sample.pdf')
        .field('title', 'Test Book')
        .field('category', 'technology');

      expect(response.status).toBe(201);
      expect(response.body.id).toBeDefined();
      expect(response.body.title).toBe('Test Book');
      expect(response.body.status).toBe('processing');
    });
  });
});

// E2E Test
test('user can upload, search, and read a book', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('[name="email"]', 'test@example.com');
  await page.click('button[type="submit"]');

  // Upload book
  await page.goto('/books/upload');
  const fileInput = await page.$('input[type="file"]');
  await fileInput.setInputFiles('test/fixtures/sample.pdf');
  await page.fill('[name="title"]', 'E2E Test Book');
  await page.click('button[type="submit"]');

  // Wait for processing
  await page.waitForSelector('[data-status="active"]', { timeout: 30000 });

  // Search for book
  await page.fill('[name="search"]', 'E2E Test');
  await page.click('[data-testid="search-button"]');

  // Verify book appears
  await expect(page.locator('text=E2E Test Book')).toBeVisible();

  // Open and read
  await page.click('text=E2E Test Book');
  await expect(page.locator('[data-testid="pdf-viewer"]')).toBeVisible();
});
```

### 7.3 Load Testing

```javascript
// k6 load test script
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 100 },   // Ramp up
    { duration: '5m', target: 100 },   // Sustain
    { duration: '1m', target: 500 },   // Spike
    { duration: '5m', target: 500 },   // Sustain spike
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(99)<500'],  // 99% under 500ms
    http_req_failed: ['rate<0.01'],    // Error rate under 1%
  },
};

export default function () {
  // Search endpoint
  const searchRes = http.get('https://api.ilm-red.com/v1/search?q=javascript', {
    headers: { 'Authorization': `Bearer ${__ENV.API_TOKEN}` }
  });

  check(searchRes, {
    'search status is 200': (r) => r.status === 200,
    'search has results': (r) => JSON.parse(r.body).books.length > 0,
  });

  sleep(1);
}
```

---

## 8. Deployment & Operations

### 8.1 Infrastructure Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Container Apps                          │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  ilmred-prod-api (0.5 vCPU, 1GB RAM)                        ││
│  │  - Auto-scales 1-10 replicas based on HTTP load             ││
│  │  - Health probes: /v1/health (liveness + readiness)         ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────────┬─────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  PostgreSQL   │    │   Redis Cache    │    │ Azure Blob      │
│  (Flexible)   │    │   (Basic C0)     │    │ Storage         │
│  Burstable B1 │    │   250MB          │    │ Hot tier        │
└───────────────┘    └──────────────────┘    └─────────────────┘
```

### 8.2 Deployment Script

The deployment is handled by `scripts/deploy-azure.sh`:

```bash
# Full deployment (infrastructure + app)
./scripts/deploy-azure.sh prod

# Infrastructure only (Bicep templates)
./scripts/deploy-azure.sh prod --infra-only

# App only (Docker build + push + update)
./scripts/deploy-azure.sh prod --app-only

# Skip Docker build (push existing image)
./scripts/deploy-azure.sh prod --app-only --skip-build
```

**Deployment Flow:**
1. Check prerequisites (Azure CLI, Docker, login)
2. Create resource group (`ilmred-prod-rg`)
3. Deploy Bicep templates (`infra/main.bicep`)
4. Build Docker image (`docker/Dockerfile`)
5. Push to Azure Container Registry
6. Update Container App with new image
7. Verify health endpoint (`/v1/health`)

### 8.3 Infrastructure as Code (Bicep)

```
infra/
├── main.bicep              # Main template (orchestrates modules)
├── parameters.json         # Environment-specific values
├── parameters.example.json # Template for parameters
└── modules/
    ├── container-apps.bicep     # Container Apps Environment + App
    ├── container-registry.bicep # Azure Container Registry
    ├── postgresql.bicep         # PostgreSQL Flexible Server
    ├── redis.bicep              # Azure Cache for Redis
    ├── storage.bicep            # Azure Blob Storage
    └── keyvault.bicep           # Azure Key Vault
```

### 8.4 Container Configuration

```dockerfile
# docker/Dockerfile - Multi-stage Python build
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install poetry==2.2.1
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

FROM python:3.12-slim
WORKDIR /app
RUN useradd --create-home appuser
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --chown=appuser:appuser app ./app/
COPY --chown=appuser:appuser docker/entrypoint.sh /app/entrypoint.sh
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/v1/health
ENTRYPOINT ["/app/entrypoint.sh"]
```

**Entrypoint Flow** (`docker/entrypoint.sh`):
1. Run Alembic migrations (`alembic upgrade head`)
2. Start Uvicorn (`uvicorn app.main:app --host 0.0.0.0 --port 8000`)

### 8.5 Scaling Configuration

Edit `infra/parameters.json`:

```json
{
  "containerMinReplicas": { "value": 1 },
  "containerMaxReplicas": { "value": 10 }
}
```

**Scaling Rules** (in `modules/container-apps.bicep`):
- HTTP-based: Scale up when concurrent requests > 50
- Min replicas: Configurable (0-10)
- Max replicas: Configurable (1-30)

| Setting | Behavior | Cost Impact |
|---------|----------|-------------|
| `minReplicas: 0` | Scale to zero when idle | ~$0 when idle, 20-30s cold starts |
| `minReplicas: 1` | Always-on | +$23/mo, no cold starts |
| `minReplicas: 2` | High availability | +$46/mo, HA |

### 8.6 Environment Variables

Configured in `infra/main.bicep` → `containerApps` module:

| Variable | Source | Description |
|----------|--------|-------------|
| `DATABASE_URL` | PostgreSQL module | Connection string |
| `REDIS_URL` | Redis module | Connection string |
| `JWT_SECRET` | parameters.json (secret) | Auth signing key |
| `STORAGE_TYPE` | Hardcoded: `azure` | Use Azure Blob |
| `OPENAI_API_KEY` | parameters.json (secret) | AI provider |
| `ENVIRONMENT` | Hardcoded: `production` | App mode |

### 8.7 Monitoring & Troubleshooting

```bash
# View container logs (real-time)
az containerapp logs show \
  --name ilmred-prod-api \
  --resource-group ilmred-prod-rg \
  --follow

# Check revision status
az containerapp revision list \
  --name ilmred-prod-api \
  --resource-group ilmred-prod-rg \
  -o table

# Get app health state
az containerapp show \
  --name ilmred-prod-api \
  --resource-group ilmred-prod-rg \
  --query "{revision:properties.latestRevisionName,health:properties.latestReadyRevisionName}"

# Execute command in container
az containerapp exec \
  --name ilmred-prod-api \
  --resource-group ilmred-prod-rg \
  --command "alembic current"
```

### 8.8 Cost Management

**Monthly Cost Breakdown (Always-On):**

| Resource | SKU | Cost |
|----------|-----|------|
| Container Apps | 0.5 vCPU, 1GB × 24h × 30d | ~$23 |
| PostgreSQL | Burstable B1ms | ~$15 |
| Redis | Basic C0 (250MB) | ~$16 |
| Container Registry | Basic | ~$5 |
| Storage | Hot tier, minimal usage | ~$1 |
| Key Vault | Standard | ~$0.03 |
| **Total** | | **~$60/mo** |

**Cost Optimization:**
- Set `containerMinReplicas: 0` for dev/staging (scale-to-zero)
- Use `containerMinReplicas: 1` for production (eliminate cold starts)
- PostgreSQL and Redis are fixed costs regardless of traffic

### 8.9 Disaster Recovery

**Backup:**
- PostgreSQL: Automatic backups (7 days retention, local redundancy)
- Redis: Volatile cache (no persistence, can be rebuilt)
- Storage: Azure Blob with local redundancy

**Recovery:**
```bash
# Redeploy from scratch
./scripts/deploy-azure.sh prod

# Restore database (if needed)
az postgres flexible-server backup restore \
  --resource-group ilmred-prod-rg \
  --name ilmred-prod-postgres \
  --restore-time "2024-01-15T10:30:00Z"
```

### 8.10 Security Checklist

- [ ] API keys stored in Key Vault (not in code)
- [ ] JWT secret generated securely (`openssl rand -base64 32`)
- [ ] CORS configured for production domains
- [ ] PostgreSQL firewall allows only Azure services
- [ ] Container runs as non-root user (`appuser`)
- [ ] HTTPS enforced (TLS termination at Container Apps)

---

## 9. Monitoring & Observability

### 9.1 Logging

```typescript
// Structured logging with Pino
const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label })
  },
  base: {
    service: process.env.SERVICE_NAME,
    version: process.env.APP_VERSION
  },
  redact: ['req.headers.authorization', 'password', 'token']
});

// Request logging middleware
fastify.addHook('onRequest', async (request) => {
  request.log = logger.child({
    requestId: request.id,
    method: request.method,
    url: request.url,
    userId: request.user?.id
  });
});

fastify.addHook('onResponse', async (request, reply) => {
  request.log.info({
    statusCode: reply.statusCode,
    responseTime: reply.getResponseTime()
  }, 'Request completed');
});
```

### 9.2 Metrics

```typescript
// Prometheus metrics
const metrics = {
  httpRequestDuration: new Histogram({
    name: 'http_request_duration_seconds',
    help: 'HTTP request duration in seconds',
    labelNames: ['method', 'route', 'status'],
    buckets: [0.01, 0.05, 0.1, 0.5, 1, 5]
  }),

  activeConnections: new Gauge({
    name: 'active_connections',
    help: 'Number of active connections'
  }),

  dbQueryDuration: new Histogram({
    name: 'db_query_duration_seconds',
    help: 'Database query duration',
    labelNames: ['operation', 'collection'],
    buckets: [0.001, 0.01, 0.1, 1]
  }),

  cacheHitRate: new Counter({
    name: 'cache_hits_total',
    help: 'Cache hit count',
    labelNames: ['cache_type']
  })
};
```

### 9.3 Distributed Tracing

```typescript
// OpenTelemetry setup
import { NodeSDK } from '@opentelemetry/sdk-node';
import { AzureMonitorTraceExporter } from '@azure/monitor-opentelemetry-exporter';

const sdk = new NodeSDK({
  traceExporter: new AzureMonitorTraceExporter({
    connectionString: process.env.APPINSIGHTS_CONNECTION_STRING
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': { enabled: true },
      '@opentelemetry/instrumentation-fastify': { enabled: true },
      '@opentelemetry/instrumentation-redis': { enabled: true }
    })
  ]
});

sdk.start();
```

---

## 10. Chat System Design

### 10.1 Overview

The chat system provides persistent multi-turn conversations with AI about books, supporting both synchronous and streaming responses.

### 10.2 Data Models

#### 10.2.1 ChatSession

```sql
-- PostgreSQL Table: chat_sessions
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID REFERENCES books(id) ON DELETE SET NULL,  -- Optional book context
    title VARCHAR(200) NOT NULL,                           -- Auto-generated or user-provided
    message_count INTEGER NOT NULL DEFAULT 0,              -- Denormalized for performance
    last_model VARCHAR(50),                                -- Last model used
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ                                -- NULL = active
);

-- Indexes for common queries
CREATE INDEX idx_chat_sessions_user_archived_updated
    ON chat_sessions(user_id, archived_at, updated_at DESC);
CREATE INDEX idx_chat_sessions_book
    ON chat_sessions(book_id) WHERE book_id IS NOT NULL;
```

```typescript
interface ChatSession {
  id: string;                    // UUID v4
  userId: string;                // FK to users
  bookId?: string;               // Optional book context
  title: string;                 // Session name
  messageCount: number;          // Denormalized count
  lastModel?: string;            // Last model used
  createdAt: Date;
  updatedAt: Date;
  archivedAt?: Date;             // Soft delete
}
```

#### 10.2.2 ChatMessage

```sql
-- PostgreSQL Table: chat_messages
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    tokens_input INTEGER,         -- NULL for user messages
    tokens_output INTEGER,        -- NULL for user messages
    cost_cents INTEGER,           -- NULL for user messages
    model VARCHAR(50),            -- NULL for user messages
    finish_reason VARCHAR(20),    -- 'stop', 'length', 'content_filter'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for message retrieval
CREATE INDEX idx_chat_messages_session_created
    ON chat_messages(session_id, created_at ASC);
```

```typescript
interface ChatMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tokensInput?: number;          // Input tokens (assistant only)
  tokensOutput?: number;         // Output tokens (assistant only)
  costCents?: number;            // Cost in cents (assistant only)
  model?: string;                // Model used (assistant only)
  finishReason?: string;         // Completion reason
  createdAt: Date;
}
```

#### 10.2.3 MessageFeedback

```sql
-- PostgreSQL Table: message_feedback
CREATE TABLE message_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL CHECK (rating IN (-1, 1)),  -- thumbs down/up
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(message_id, user_id)
);
```

### 10.3 SSE Streaming Protocol

#### 10.3.1 Endpoint Specification

```
Endpoint: POST /v1/chats/{session_id}/stream
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
```

#### 10.3.2 Event Types

```
# Content chunk (partial response)
event: chunk
data: {"content": "Chapter"}

event: chunk
data: {"content": " 3 discusses"}

# Token count update (mid-stream)
event: tokens
data: {"input": 50, "output": 25}

# Stream complete
event: done
data: {"finish_reason": "stop", "message_id": "uuid", "total_tokens": 75, "cost_cents": 1}

# Error during stream
event: error
data: {"code": "RATE_LIMITED", "message": "Rate limit exceeded. Retry after 60 seconds."}
```

#### 10.3.3 Client Implementation (React Native)

```typescript
const streamChat = async (sessionId: string, message: string, onChunk: (text: string) => void) => {
  const response = await fetch(`${API_URL}/v1/chats/${sessionId}/stream`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content: message }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.content) {
          onChunk(data.content);
        }
        if (data.finish_reason) {
          return data; // Return final metadata
        }
      }
    }
  }
};
```

### 10.4 Chat Service Implementation

```python
# app/services/chat_service.py
class ChatService:
    async def create_session(
        self,
        user_id: UUID,
        book_id: Optional[UUID] = None,
        title: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            id=uuid4(),
            user_id=user_id,
            book_id=book_id,
            title=title or self._generate_title(book_id),
            message_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        return await self.repo.create(session)

    async def send_message(
        self,
        session_id: UUID,
        content: str,
        model: Optional[str] = None
    ) -> ChatMessage:
        """Send a message and get AI response (non-streaming)."""
        session = await self.repo.get_session(session_id)

        # Check billing
        await self.billing_service.check_balance(session.user_id)
        await self.billing_service.check_limits(session.user_id)

        # Safety check input
        safety_result = await self.safety_service.check_input(content)
        if safety_result.severity == Severity.HIGH:
            raise ContentBlockedError(safety_result.categories)

        # Save user message
        user_message = await self._save_message(session_id, 'user', content)

        # Get context from book if available
        context = []
        if session.book_id:
            context = await self._get_book_context(session.book_id, content)

        # Select model
        selected_model = await self.router.select_model(
            content,
            await self.user_service.get(session.user_id),
            explicit_model=model
        )

        # Get message history
        history = await self.repo.get_messages(session_id, limit=20)

        # Call AI provider
        ai_response = await self.ai_service.chat(
            model=selected_model,
            messages=self._build_messages(history, context, content),
            stream=False
        )

        # Safety check output
        output_safety = await self.safety_service.check_output(ai_response.content)
        final_content = self._apply_safety_filter(ai_response.content, output_safety)

        # Calculate cost
        cost_cents = self._calculate_cost(
            selected_model,
            ai_response.tokens_input,
            ai_response.tokens_output
        )

        # Save assistant message
        assistant_message = await self._save_message(
            session_id=session_id,
            role='assistant',
            content=final_content,
            tokens_input=ai_response.tokens_input,
            tokens_output=ai_response.tokens_output,
            cost_cents=cost_cents,
            model=selected_model,
            finish_reason=ai_response.finish_reason
        )

        # Record billing transaction
        await self.billing_service.record_transaction(
            user_id=session.user_id,
            operation_type='chat',
            operation_id=assistant_message.id,
            model=selected_model,
            tokens_input=ai_response.tokens_input,
            tokens_output=ai_response.tokens_output,
            cost_cents=cost_cents
        )

        # Update session
        await self.repo.update_session(session_id, {
            'message_count': session.message_count + 2,
            'last_model': selected_model,
            'updated_at': datetime.utcnow()
        })

        return assistant_message

    async def stream_message(
        self,
        session_id: UUID,
        content: str,
        model: Optional[str] = None
    ) -> AsyncGenerator[dict, None]:
        """Send a message and stream AI response via SSE."""
        session = await self.repo.get_session(session_id)

        # Pre-checks (billing, safety)
        await self.billing_service.check_balance(session.user_id)
        safety_result = await self.safety_service.check_input(content)
        if safety_result.severity == Severity.HIGH:
            yield {'type': 'error', 'code': 'CONTENT_BLOCKED', 'message': 'Content policy violation'}
            return

        # Save user message
        await self._save_message(session_id, 'user', content)

        # Select model and build context
        selected_model = await self.router.select_model(content, session.user_id, model)
        context = await self._get_book_context(session.book_id, content) if session.book_id else []
        history = await self.repo.get_messages(session_id, limit=20)

        # Stream from AI provider
        full_content = ""
        tokens_input = 0
        tokens_output = 0

        async for chunk in self.ai_service.chat_stream(
            model=selected_model,
            messages=self._build_messages(history, context, content)
        ):
            if chunk.type == 'content':
                full_content += chunk.content
                yield {'type': 'chunk', 'content': chunk.content}
            elif chunk.type == 'usage':
                tokens_input = chunk.input
                tokens_output = chunk.output
                yield {'type': 'tokens', 'input': tokens_input, 'output': tokens_output}

        # Calculate cost and save message
        cost_cents = self._calculate_cost(selected_model, tokens_input, tokens_output)
        message = await self._save_message(
            session_id, 'assistant', full_content,
            tokens_input=tokens_input, tokens_output=tokens_output,
            cost_cents=cost_cents, model=selected_model, finish_reason='stop'
        )

        # Record billing
        await self.billing_service.record_transaction(
            user_id=session.user_id,
            operation_type='chat',
            operation_id=message.id,
            model=selected_model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost_cents=cost_cents
        )

        yield {
            'type': 'done',
            'finish_reason': 'stop',
            'message_id': str(message.id),
            'total_tokens': tokens_input + tokens_output,
            'cost_cents': cost_cents
        }
```

---

## 11. Billing System Design

### 11.1 Overview

The billing system tracks AI usage at a granular level, manages credit balances, and enforces usage limits.

### 11.2 Data Models

#### 11.2.1 UserCredits

```sql
-- PostgreSQL Table: user_credits
CREATE TABLE user_credits (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    balance_cents INTEGER NOT NULL DEFAULT 0,
    lifetime_usage_cents INTEGER NOT NULL DEFAULT 0,
    free_credits_remaining INTEGER NOT NULL DEFAULT 100,  -- $1.00 for free tier
    free_credits_reset_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 month'),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

```typescript
interface UserCredits {
  userId: string;
  balanceCents: number;           // Current balance in cents
  lifetimeUsageCents: number;     // Total ever used
  freeCreditsRemaining: number;   // Monthly free allocation
  freeCreditsResetAt: Date;       // Next reset date
  updatedAt: Date;
}
```

#### 11.2.2 BillingTransaction

```sql
-- PostgreSQL Table: billing_transactions
CREATE TABLE billing_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation_type VARCHAR(20) NOT NULL CHECK (operation_type IN ('chat', 'summary', 'search', 'embedding')),
    operation_id UUID,                 -- Reference to specific message/operation
    model VARCHAR(50) NOT NULL,
    tokens_input INTEGER NOT NULL,
    tokens_output INTEGER NOT NULL,
    cost_cents INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for billing queries
CREATE INDEX idx_billing_transactions_user_created
    ON billing_transactions(user_id, created_at DESC);
```

```typescript
interface BillingTransaction {
  id: string;
  userId: string;
  operationType: 'chat' | 'summary' | 'search' | 'embedding';
  operationId?: string;           // Reference to chat_message, etc.
  model: string;
  tokensInput: number;
  tokensOutput: number;
  costCents: number;
  createdAt: Date;
}
```

#### 11.2.3 UsageLimit

```sql
-- PostgreSQL Table: usage_limits
CREATE TABLE usage_limits (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    daily_tokens_limit INTEGER NOT NULL DEFAULT 10000,
    daily_tokens_used INTEGER NOT NULL DEFAULT 0,
    daily_reset_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 day'),
    monthly_cost_limit_cents INTEGER NOT NULL DEFAULT 100,  -- $1.00
    monthly_cost_used_cents INTEGER NOT NULL DEFAULT 0,
    monthly_reset_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 month')
);
```

### 11.3 Transaction Recording Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Chat Request                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  1. BillingService.check_balance(user_id)                   │
│     - Get user_credits.balance_cents + free_credits         │
│     - If total < estimated_cost → HTTP 402 Payment Required │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  2. BillingService.check_limits(user_id)                    │
│     - Check daily_tokens_used < daily_tokens_limit          │
│     - Check monthly_cost_used < monthly_cost_limit          │
│     - If exceeded → HTTP 429 with X-RateLimit-Reset         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Execute AI Call                                         │
│     - SafetyService.check_input(message)                    │
│     - AIProvider.chat(messages)                             │
│     - SafetyService.check_output(response)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  4. BillingService.record_transaction(                      │
│       user_id, operation_type, model,                       │
│       tokens_input, tokens_output, cost_cents               │
│     )                                                       │
│     - INSERT INTO billing_transactions                      │
│     - Deduct from free_credits first, then balance          │
│     - UPDATE usage_limits SET used += tokens/cost           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  5. Return Response with cost metadata                      │
│     { "content": "...", "tokens": 75, "cost_cents": 1 }     │
└─────────────────────────────────────────────────────────────┘
```

### 11.4 Cost Calculation

```python
# app/services/billing_service.py
from app.ai import MODEL_REGISTRY

def calculate_cost_cents(model: str, tokens_input: int, tokens_output: int) -> int:
    """Calculate cost in cents for an AI operation."""
    model_config = MODEL_REGISTRY.get(model)
    if not model_config:
        raise ValueError(f"Unknown model: {model}")

    # Costs are per 1M tokens, stored as USD
    input_cost = (tokens_input / 1_000_000) * model_config.input_cost_per_1m
    output_cost = (tokens_output / 1_000_000) * model_config.output_cost_per_1m

    total_usd = input_cost + output_cost
    total_cents = int(total_usd * 100)

    # Minimum charge: 1 cent (except for free tier operations)
    return max(total_cents, 1)
```

### 11.5 Billing Service Implementation

```python
# app/services/billing_service.py
class BillingService:
    async def check_balance(self, user_id: UUID) -> None:
        """Check if user has sufficient balance. Raises PaymentRequiredError if not."""
        credits = await self.repo.get_credits(user_id)
        total_available = credits.balance_cents + credits.free_credits_remaining

        if total_available < 1:  # Minimum 1 cent needed
            raise PaymentRequiredError(
                "Insufficient credits. Please top up your account.",
                balance_cents=credits.balance_cents,
                free_remaining=credits.free_credits_remaining
            )

    async def check_limits(self, user_id: UUID) -> LimitStatus:
        """Check usage limits. Returns status with warnings or raises error."""
        limits = await self.repo.get_limits(user_id)
        now = datetime.utcnow()

        # Reset if needed
        if limits.daily_reset_at < now:
            limits = await self.repo.reset_daily_limits(user_id)
        if limits.monthly_reset_at < now:
            limits = await self.repo.reset_monthly_limits(user_id)

        # Check daily tokens
        daily_pct = limits.daily_tokens_used / limits.daily_tokens_limit
        if daily_pct >= 1.0:
            raise RateLimitedError(
                "Daily token limit exceeded",
                reset_at=limits.daily_reset_at
            )

        # Check monthly cost
        monthly_pct = limits.monthly_cost_used_cents / limits.monthly_cost_limit_cents
        if monthly_pct >= 1.0:
            raise RateLimitedError(
                "Monthly cost limit exceeded",
                reset_at=limits.monthly_reset_at
            )

        # Return warning status
        return LimitStatus(
            daily_warning=daily_pct >= 0.8,
            monthly_warning=monthly_pct >= 0.8,
            daily_remaining=limits.daily_tokens_limit - limits.daily_tokens_used,
            monthly_remaining_cents=limits.monthly_cost_limit_cents - limits.monthly_cost_used_cents
        )

    async def record_transaction(
        self,
        user_id: UUID,
        operation_type: str,
        operation_id: Optional[UUID],
        model: str,
        tokens_input: int,
        tokens_output: int,
        cost_cents: int
    ) -> BillingTransaction:
        """Record a billing transaction and update balances."""
        async with self.db.transaction():
            # Create transaction record
            transaction = BillingTransaction(
                id=uuid4(),
                user_id=user_id,
                operation_type=operation_type,
                operation_id=operation_id,
                model=model,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_cents=cost_cents,
                created_at=datetime.utcnow()
            )
            await self.repo.create_transaction(transaction)

            # Deduct from credits (free first, then balance)
            credits = await self.repo.get_credits(user_id)
            if credits.free_credits_remaining >= cost_cents:
                await self.repo.update_credits(user_id, {
                    'free_credits_remaining': credits.free_credits_remaining - cost_cents
                })
            else:
                free_used = credits.free_credits_remaining
                balance_used = cost_cents - free_used
                await self.repo.update_credits(user_id, {
                    'free_credits_remaining': 0,
                    'balance_cents': credits.balance_cents - balance_used,
                    'lifetime_usage_cents': credits.lifetime_usage_cents + cost_cents
                })

            # Update limits
            total_tokens = tokens_input + tokens_output
            await self.repo.increment_limits(user_id, total_tokens, cost_cents)

            return transaction

    async def get_balance(self, user_id: UUID) -> BalanceResponse:
        """Get current balance for API response."""
        credits = await self.repo.get_credits(user_id)
        return BalanceResponse(
            balance_cents=credits.balance_cents,
            free_credits_remaining=credits.free_credits_remaining,
            free_credits_reset_at=credits.free_credits_reset_at,
            total_available=credits.balance_cents + credits.free_credits_remaining
        )

    async def get_usage_summary(
        self,
        user_id: UUID,
        period: str = 'month'
    ) -> UsageSummary:
        """Get usage summary for a period."""
        start_date = self._get_period_start(period)
        transactions = await self.repo.get_transactions(
            user_id,
            since=start_date
        )

        return UsageSummary(
            period=period,
            start_date=start_date,
            total_cost_cents=sum(t.cost_cents for t in transactions),
            total_tokens=sum(t.tokens_input + t.tokens_output for t in transactions),
            transaction_count=len(transactions),
            by_operation={
                op: sum(t.cost_cents for t in transactions if t.operation_type == op)
                for op in ['chat', 'summary', 'search', 'embedding']
            },
            by_model={
                model: sum(t.cost_cents for t in transactions if t.model == model)
                for model in set(t.model for t in transactions)
            }
        )
```

---

## 12. AI Safety System Design

### 12.1 Overview

The AI Safety system protects users from harmful content in both input (user messages) and output (AI responses).

### 12.2 Content Safety Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Message                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SafetyService.check_input(message, user_strictness)        │
│                                                             │
│  1. Call OpenAI Moderation API (primary)                    │
│     - Categories: hate, violence, sexual, self-harm         │
│  2. Fallback: Keyword filtering (if API unavailable)        │
│  3. Return SafetyResult(flagged, categories, severity)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Severity?      │
                    └─────────────────┘
                    /       |        \
                HIGH     MEDIUM      LOW/NONE
                  │         │           │
                  ▼         ▼           ▼
             ┌────────┐ ┌────────┐ ┌────────┐
             │ Block  │ │ Warn + │ │Continue│
             │ + Log  │ │ Allow  │ │        │
             └────────┘ └────────┘ └────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Generation                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  SafetyService.check_output(response, user_strictness)      │
│                                                             │
│  1. Same moderation check as input                          │
│  2. If flagged: redact/filter sensitive content             │
│  3. Log for review if severity >= MEDIUM                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                Return to User                               │
└─────────────────────────────────────────────────────────────┘
```

### 12.3 Safety Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `hate` | Hate speech, discrimination | Slurs, stereotypes, dehumanization |
| `violence` | Violent content, threats | Graphic violence, threats of harm |
| `sexual` | Sexual content, explicit material | Explicit descriptions, NSFW content |
| `self_harm` | Self-harm, suicide content | Instructions for self-injury |
| `illegal` | Illegal activities | Fraud, hacking, drug manufacturing |

### 12.4 Strictness Levels

| Level | HIGH Threshold | MEDIUM Threshold | Behavior |
|-------|----------------|------------------|----------|
| `strict` | 0.3 | 0.1 | Block most flagged content |
| `moderate` | 0.6 | 0.3 | Allow borderline, block clear violations |
| `minimal` | 0.9 | 0.7 | Only block severe violations |

### 12.5 Safety Service Implementation

```python
# app/services/safety_service.py
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional
import httpx

class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SafetyCategory(str, Enum):
    HATE = "hate"
    VIOLENCE = "violence"
    SEXUAL = "sexual"
    SELF_HARM = "self_harm"
    ILLEGAL = "illegal"

@dataclass
class SafetyResult:
    flagged: bool
    categories: List[SafetyCategory]
    severity: Severity
    scores: dict[str, float]
    message: Optional[str] = None

class SafetyService:
    STRICTNESS_THRESHOLDS = {
        "strict": {"high": 0.3, "medium": 0.1},
        "moderate": {"high": 0.6, "medium": 0.3},
        "minimal": {"high": 0.9, "medium": 0.7},
    }

    async def check_input(
        self,
        content: str,
        strictness: str = "moderate"
    ) -> SafetyResult:
        """Check user input for safety violations."""
        try:
            result = await self._call_moderation_api(content)
        except Exception as e:
            # Fallback to keyword filtering
            result = self._keyword_filter(content)

        return self._apply_strictness(result, strictness)

    async def check_output(
        self,
        content: str,
        strictness: str = "moderate"
    ) -> SafetyResult:
        """Check AI output for safety violations."""
        result = await self.check_input(content, strictness)

        # Log flagged outputs for review
        if result.severity in [Severity.MEDIUM, Severity.HIGH]:
            await self._log_flagged_content(content, result, "output")

        return result

    async def _call_moderation_api(self, content: str) -> SafetyResult:
        """Call OpenAI Moderation API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/moderations",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                json={"input": content}
            )
            data = response.json()

            result = data["results"][0]
            categories = []
            scores = {}

            # Map OpenAI categories to our categories
            category_mapping = {
                "hate": SafetyCategory.HATE,
                "violence": SafetyCategory.VIOLENCE,
                "sexual": SafetyCategory.SEXUAL,
                "self-harm": SafetyCategory.SELF_HARM,
            }

            for oai_cat, our_cat in category_mapping.items():
                if result["categories"].get(oai_cat):
                    categories.append(our_cat)
                scores[our_cat.value] = result["category_scores"].get(oai_cat, 0)

            return SafetyResult(
                flagged=result["flagged"],
                categories=categories,
                severity=Severity.NONE,  # Will be set by _apply_strictness
                scores=scores
            )

    def _apply_strictness(
        self,
        result: SafetyResult,
        strictness: str
    ) -> SafetyResult:
        """Apply strictness thresholds to determine severity."""
        thresholds = self.STRICTNESS_THRESHOLDS.get(strictness, self.STRICTNESS_THRESHOLDS["moderate"])

        max_score = max(result.scores.values()) if result.scores else 0

        if max_score >= thresholds["high"]:
            severity = Severity.HIGH
            message = "Content blocked due to policy violation"
        elif max_score >= thresholds["medium"]:
            severity = Severity.MEDIUM
            message = "Content flagged for review"
        elif result.flagged:
            severity = Severity.LOW
            message = None
        else:
            severity = Severity.NONE
            message = None

        return SafetyResult(
            flagged=result.flagged,
            categories=result.categories,
            severity=severity,
            scores=result.scores,
            message=message
        )

    def _keyword_filter(self, content: str) -> SafetyResult:
        """Fallback keyword-based filtering."""
        # Simple keyword matching as fallback
        # In production, use a more sophisticated approach
        flagged = False
        categories = []
        scores = {cat.value: 0.0 for cat in SafetyCategory}

        # Example patterns (would be more comprehensive in production)
        patterns = {
            SafetyCategory.VIOLENCE: ["kill", "murder", "attack"],
            SafetyCategory.HATE: ["slur_placeholder"],
            # ... more patterns
        }

        content_lower = content.lower()
        for category, keywords in patterns.items():
            for keyword in keywords:
                if keyword in content_lower:
                    flagged = True
                    categories.append(category)
                    scores[category.value] = 0.9
                    break

        return SafetyResult(
            flagged=flagged,
            categories=categories,
            severity=Severity.NONE,
            scores=scores
        )

    async def _log_flagged_content(
        self,
        content: str,
        result: SafetyResult,
        direction: str
    ) -> None:
        """Log flagged content for manual review."""
        await self.repo.create_safety_flag(
            content=content[:500],  # Truncate for storage
            direction=direction,
            categories=result.categories,
            severity=result.severity,
            scores=result.scores
        )
```

---

## 13. Smart LLM Router Design

### 13.1 Overview

The Smart LLM Router automatically selects the optimal model based on task type, user tier, and cost optimization.

### 13.2 Task Classification

```python
# app/ai/task_classifier.py
from enum import Enum

class TaskType(str, Enum):
    SUMMARY = "summary"      # Summarize, condense, TLDR
    REASONING = "reasoning"  # Analyze, explain why, compare
    CREATIVE = "creative"    # Write, compose, generate story
    CODE = "code"            # Write code, debug, refactor
    GENERAL = "general"      # Default for unclassified

def classify_task(message: str) -> TaskType:
    """Classify user message into task type using keyword matching + heuristics."""
    message_lower = message.lower()

    # Summary keywords
    if any(kw in message_lower for kw in ['summarize', 'summary', 'tldr', 'condense', 'brief', 'shorten']):
        return TaskType.SUMMARY

    # Code keywords
    if any(kw in message_lower for kw in ['code', 'function', 'implement', 'debug', 'fix bug', 'refactor', 'python', 'javascript']):
        return TaskType.CODE

    # Creative keywords
    if any(kw in message_lower for kw in ['write', 'compose', 'create', 'story', 'poem', 'creative', 'imagine']):
        return TaskType.CREATIVE

    # Reasoning keywords
    if any(kw in message_lower for kw in ['analyze', 'explain', 'why', 'compare', 'difference', 'reason', 'think']):
        return TaskType.REASONING

    return TaskType.GENERAL
```

### 13.3 Model Selection Matrix

```python
# app/ai/model_router.py

MODEL_SELECTION_MATRIX = {
    # (task_type, user_tier) → model_id
    (TaskType.SUMMARY, "free"): "qwen-turbo",
    (TaskType.SUMMARY, "premium"): "qwen-turbo",      # Still cheapest

    (TaskType.REASONING, "free"): "gpt-4o-mini",
    (TaskType.REASONING, "premium"): "gpt-4o",

    (TaskType.CREATIVE, "free"): "claude-3-haiku",
    (TaskType.CREATIVE, "premium"): "claude-3-sonnet",

    (TaskType.CODE, "free"): "deepseek-chat",
    (TaskType.CODE, "premium"): "deepseek-coder",

    (TaskType.GENERAL, "free"): "qwen-turbo",
    (TaskType.GENERAL, "premium"): "gpt-4o-mini",
}

FALLBACK_CHAINS = {
    "openai": ["anthropic", "qwen", "deepseek"],
    "anthropic": ["openai", "qwen", "deepseek"],
    "qwen": ["deepseek", "openai", "anthropic"],
    "deepseek": ["qwen", "openai", "anthropic"],
    "google": ["openai", "anthropic", "qwen"],
    "xai": ["openai", "anthropic", "qwen"],
}
```

### 13.4 Router Implementation

```python
# app/services/ai_model_router.py
from app.ai import MODEL_REGISTRY
from app.ai.task_classifier import classify_task, TaskType

class AIModelRouter:
    async def select_model(
        self,
        message: str,
        user: User,
        explicit_model: Optional[str] = None,
        book: Optional[Book] = None,
    ) -> str:
        """Select optimal model for the request."""

        # 1. User explicit override takes precedence
        if explicit_model:
            if explicit_model not in MODEL_REGISTRY:
                raise ModelNotFoundError(explicit_model)
            if not await self._check_model_available(explicit_model):
                raise ModelNotAvailableError(explicit_model)
            if self._is_premium_model(explicit_model) and not user.is_premium:
                raise PremiumRequiredError(explicit_model)
            return explicit_model

        # 2. Check user's default preference
        if user.preferences and user.preferences.ai and user.preferences.ai.default_model:
            default = user.preferences.ai.default_model
            if await self._check_model_available(default):
                return default

        # 3. Classify task and select from matrix
        task_type = classify_task(message)
        tier = "premium" if user.is_premium else "free"

        # Book visibility affects model selection for cost
        if book and book.visibility == "public" and task_type == TaskType.GENERAL:
            # Use cheapest model for public book queries
            selected = "qwen-turbo"
        else:
            selected = MODEL_SELECTION_MATRIX.get((task_type, tier), "qwen-turbo")

        # 4. Check availability with fallback
        if not await self._check_model_available(selected):
            selected = await self._get_fallback(selected, tier)

        return selected

    async def _check_model_available(self, model_id: str) -> bool:
        """Check if model is currently available and healthy."""
        model_config = MODEL_REGISTRY.get(model_id)
        if not model_config:
            return False

        # Check provider health cache
        cache_key = f"provider_health:{model_config.vendor}"
        cached = await self.cache.get(cache_key)
        if cached is not None:
            return cached

        # Ping provider
        try:
            provider = self._get_provider(model_config.vendor)
            await provider.health_check()
            await self.cache.set(cache_key, True, ttl=60)
            return True
        except Exception:
            await self.cache.set(cache_key, False, ttl=30)
            return False

    async def _get_fallback(self, model_id: str, tier: str) -> str:
        """Get fallback model when primary is unavailable."""
        model_config = MODEL_REGISTRY.get(model_id)
        if not model_config:
            raise AllModelsUnavailableError()

        vendor = model_config.vendor
        fallback_vendors = FALLBACK_CHAINS.get(vendor, [])

        for fallback_vendor in fallback_vendors:
            fallback_model = self._get_default_for_vendor(fallback_vendor, tier)
            if await self._check_model_available(fallback_model):
                return fallback_model

        raise AllModelsUnavailableError()

    def _get_default_for_vendor(self, vendor: str, tier: str) -> str:
        """Get default model for a vendor based on tier."""
        vendor_defaults = {
            ("openai", "free"): "gpt-4o-mini",
            ("openai", "premium"): "gpt-4o",
            ("anthropic", "free"): "claude-3-haiku",
            ("anthropic", "premium"): "claude-3-sonnet",
            ("qwen", "free"): "qwen-turbo",
            ("qwen", "premium"): "qwen-plus",
            ("deepseek", "free"): "deepseek-chat",
            ("deepseek", "premium"): "deepseek-coder",
            ("google", "free"): "gemini-1.5-flash",
            ("google", "premium"): "gemini-1.5-pro",
            ("xai", "free"): "grok-beta",
            ("xai", "premium"): "grok-beta",
        }
        return vendor_defaults.get((vendor, tier), "qwen-turbo")

    def _is_premium_model(self, model_id: str) -> bool:
        """Check if model requires premium tier."""
        premium_models = {
            "gpt-4o", "gpt-4-turbo", "o1-preview", "o1-mini",
            "claude-3-opus", "claude-3-5-sonnet",
            "gemini-1.5-pro",
            "qwen-max",
        }
        return model_id in premium_models

    async def estimate_cost(
        self,
        model_id: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int
    ) -> CostEstimate:
        """Estimate cost for an operation before execution."""
        model_config = MODEL_REGISTRY.get(model_id)
        if not model_config:
            raise ModelNotFoundError(model_id)

        input_cost = (estimated_input_tokens / 1_000_000) * model_config.input_cost_per_1m
        output_cost = (estimated_output_tokens / 1_000_000) * model_config.output_cost_per_1m
        total_usd = input_cost + output_cost
        total_cents = max(int(total_usd * 100), 1)

        return CostEstimate(
            model=model_id,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
            estimated_cost_cents=total_cents,
            model_input_cost_per_1m=model_config.input_cost_per_1m,
            model_output_cost_per_1m=model_config.output_cost_per_1m
        )

    def get_available_models(self, user: User) -> List[ModelInfo]:
        """Get list of models available to user based on tier."""
        models = []
        for model_id, config in MODEL_REGISTRY.items():
            is_premium = self._is_premium_model(model_id)
            if is_premium and not user.is_premium:
                continue

            models.append(ModelInfo(
                id=model_id,
                name=config.name,
                vendor=config.vendor,
                context_window=config.context_window,
                input_cost_per_1m=config.input_cost_per_1m,
                output_cost_per_1m=config.output_cost_per_1m,
                supports_streaming=config.supports_streaming,
                tier="premium" if is_premium else "free"
            ))

        return sorted(models, key=lambda m: m.input_cost_per_1m)
```

---

## 14. Mobile Integration Guide

### 14.1 Authentication

#### 14.1.1 Token Storage
- **iOS**: Keychain Services (encrypted)
- **Android**: EncryptedSharedPreferences

#### 14.1.2 Token Refresh Strategy

```typescript
// React Native - Axios interceptor for automatic token refresh
import AsyncStorage from '@react-native-async-storage/async-storage';

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue the request while refreshing
        return new Promise((resolve) => {
          refreshSubscribers.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(api.request(originalRequest));
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const refreshToken = await AsyncStorage.getItem('refresh_token');
        const response = await api.post('/v1/auth/refresh', { refresh_token: refreshToken });
        const { access_token, refresh_token: newRefreshToken } = response.data;

        await AsyncStorage.setItem('access_token', access_token);
        await AsyncStorage.setItem('refresh_token', newRefreshToken);

        // Notify queued requests
        refreshSubscribers.forEach((callback) => callback(access_token));
        refreshSubscribers = [];

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api.request(originalRequest);
      } catch (refreshError) {
        // Refresh failed - redirect to login
        await AsyncStorage.multiRemove(['access_token', 'refresh_token']);
        // Navigate to login screen
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);
```

### 14.2 Caching Strategy

```typescript
// React Query configuration for mobile
import { QueryClient } from '@tanstack/react-query';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import AsyncStorage from '@react-native-async-storage/async-storage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,      // 5 minutes
      gcTime: 30 * 60 * 1000,        // 30 minutes (formerly cacheTime)
      retry: 3,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 30000),
      networkMode: 'offlineFirst',   // Use cached data when offline
    },
  },
});

// Persist cache to AsyncStorage
const asyncStoragePersister = createAsyncStoragePersister({
  storage: AsyncStorage,
  key: 'REACT_QUERY_OFFLINE_CACHE',
});

// Cache strategies by data type
const CACHE_CONFIG = {
  // User profile - cache longer, doesn't change often
  user: { staleTime: 10 * 60 * 1000, gcTime: 60 * 60 * 1000 },

  // Book list - moderate caching
  books: { staleTime: 5 * 60 * 1000, gcTime: 30 * 60 * 1000 },

  // Chat sessions - shorter cache, more dynamic
  chats: { staleTime: 1 * 60 * 1000, gcTime: 10 * 60 * 1000 },

  // Billing - always fresh
  billing: { staleTime: 0, gcTime: 5 * 60 * 1000 },
};
```

### 14.3 Error Handling

| HTTP Code | Meaning | Mobile Action |
|-----------|---------|---------------|
| 401 | Token expired | Auto-refresh token |
| 402 | Insufficient credits | Show top-up prompt with balance |
| 403 | Forbidden | Show permission error with support link |
| 404 | Not found | Show "not found" UI, clear cache |
| 422 | Validation error | Show field-specific error messages |
| 429 | Rate limited | Show retry countdown timer |
| 500 | Server error | Retry with exponential backoff |
| Network error | Offline | Queue for later, show offline indicator |

```typescript
// Centralized error handler
const handleApiError = (error: AxiosError) => {
  const status = error.response?.status;
  const data = error.response?.data as any;

  switch (status) {
    case 402:
      // Show credit top-up modal
      showModal('TopUpCredits', {
        balance: data.balance_cents,
        required: data.required_cents,
      });
      break;

    case 429:
      // Show rate limit countdown
      const resetAt = new Date(data.reset_at);
      const secondsRemaining = Math.ceil((resetAt.getTime() - Date.now()) / 1000);
      showToast(`Rate limited. Try again in ${secondsRemaining}s`);
      break;

    case 500:
      // Log to error tracking
      Sentry.captureException(error);
      showToast('Server error. Please try again.');
      break;

    default:
      if (!error.response) {
        // Network error
        showToast('No internet connection');
      }
  }
};
```

### 14.4 Offline Support

```typescript
// Offline mutation queue
import NetInfo from '@react-native-community/netinfo';

class OfflineQueue {
  private queue: Array<{
    mutation: () => Promise<any>;
    timestamp: number;
  }> = [];

  async add(mutation: () => Promise<any>) {
    const netState = await NetInfo.fetch();

    if (netState.isConnected) {
      return mutation();
    }

    this.queue.push({ mutation, timestamp: Date.now() });
    await this.persistQueue();
    showToast('Saved offline. Will sync when connected.');
  }

  async processQueue() {
    const netState = await NetInfo.fetch();
    if (!netState.isConnected || this.queue.length === 0) return;

    const mutations = [...this.queue];
    this.queue = [];

    for (const { mutation } of mutations) {
      try {
        await mutation();
      } catch (error) {
        // Re-queue failed mutations
        this.queue.push({ mutation, timestamp: Date.now() });
      }
    }

    await this.persistQueue();
  }

  private async persistQueue() {
    await AsyncStorage.setItem('offline_queue', JSON.stringify(
      this.queue.map(({ timestamp }) => ({ timestamp }))
    ));
  }
}

// Listen for connectivity changes
NetInfo.addEventListener((state) => {
  if (state.isConnected) {
    offlineQueue.processQueue();
  }
});
```

### 14.5 Image Loading Strategy

```typescript
// Adaptive image resolution based on device and network
import { Dimensions, PixelRatio } from 'react-native';
import NetInfo from '@react-native-community/netinfo';

type Resolution = 'thumbnail' | 'medium' | 'highRes' | 'ultra';

const getOptimalResolution = async (): Promise<Resolution> => {
  const screenWidth = Dimensions.get('window').width;
  const pixelRatio = PixelRatio.get();
  const effectiveWidth = screenWidth * pixelRatio;

  const netInfo = await NetInfo.fetch();
  const isSlowConnection = netInfo.type === 'cellular' &&
    netInfo.details?.cellularGeneration !== '4g';

  // On slow connections, use lower resolution
  if (isSlowConnection) {
    return effectiveWidth > 400 ? 'medium' : 'thumbnail';
  }

  // Based on effective screen width
  if (effectiveWidth <= 150) return 'thumbnail';
  if (effectiveWidth <= 800) return 'medium';
  if (effectiveWidth <= 1600) return 'highRes';
  return 'ultra';
};

// Image component with progressive loading
const AdaptiveImage: React.FC<{ pageUrls: Record<Resolution, string> }> = ({ pageUrls }) => {
  const [currentRes, setCurrentRes] = useState<Resolution>('thumbnail');

  useEffect(() => {
    // Load thumbnail immediately
    Image.prefetch(pageUrls.thumbnail);

    // Then load optimal resolution
    getOptimalResolution().then((optimal) => {
      if (optimal !== 'thumbnail') {
        Image.prefetch(pageUrls[optimal]).then(() => {
          setCurrentRes(optimal);
        });
      }
    });
  }, [pageUrls]);

  return (
    <Image
      source={{ uri: pageUrls[currentRes] }}
      style={styles.pageImage}
      resizeMode="contain"
    />
  );
};
```

### 14.6 Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| App cold start | < 2 seconds | Time to interactive |
| App warm start | < 500ms | Time to previous state |
| API response (p95) | < 500ms | Server response time |
| Image load (cached) | < 200ms | From disk to display |
| Image load (network) | < 2 seconds | From request to display |
| Memory usage | < 200MB | Active memory footprint |
| Battery drain | < 5%/hour active | During active reading |

---

## 15. Appendices

### A. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Missing or invalid authentication |
| `TOKEN_EXPIRED` | 401 | Access token has expired |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### B. Configuration Reference

```typescript
interface AppConfig {
  server: {
    port: number;
    host: string;
  };
  database: {
    cosmosEndpoint: string;
    cosmosKey: string;
    databaseName: string;
  };
  cache: {
    redisUrl: string;
    defaultTtl: number;
  };
  storage: {
    blobConnectionString: string;
    containerName: string;
  };
  search: {
    endpoint: string;
    apiKey: string;
    indexName: string;
  };
  ai: {
    openaiApiKey: string;
    defaultModel: string;
    maxTokens: number;
  };
  auth: {
    jwtSecret: string;
    jwtExpiry: string;
    refreshExpiry: string;
  };
}
```

### C. Database Migrations

```typescript
// Migration system
class MigrationRunner {
  async run(): Promise<void> {
    const migrations = await this.loadMigrations();
    const applied = await this.getAppliedMigrations();

    for (const migration of migrations) {
      if (!applied.includes(migration.version)) {
        await this.apply(migration);
      }
    }
  }

  private async apply(migration: Migration): Promise<void> {
    const session = await this.db.startTransaction();
    try {
      await migration.up(this.db);
      await this.recordMigration(migration.version);
      await session.commit();
    } catch (error) {
      await session.abort();
      throw error;
    }
  }
}
```
