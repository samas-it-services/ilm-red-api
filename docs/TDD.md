# ILM Red API - Technical Design Document (TDD)

## Document Information

| Field | Value |
|-------|-------|
| **Version** | 1.0.0 |
| **Last Updated** | January 2025 |
| **Status** | Draft |
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

## 8. Deployment

### 8.1 Container Configuration

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -g 1001 nodejs && adduser -S -u 1001 nodejs
COPY --from=builder --chown=nodejs:nodejs /app/dist ./dist
COPY --from=builder --chown=nodejs:nodejs /app/node_modules ./node_modules
USER nodejs
EXPOSE 3000
CMD ["node", "dist/main.js"]
```

### 8.2 Azure Container Apps Configuration

```yaml
# container-app.yaml
name: books-service
configuration:
  activeRevisionsMode: Multiple
  ingress:
    external: true
    targetPort: 3000
    transport: http
    traffic:
      - revisionName: books-service--v1
        weight: 90
      - revisionName: books-service--v2
        weight: 10
  secrets:
    - name: cosmos-connection
      value: secretref:cosmos-connection
    - name: redis-connection
      value: secretref:redis-connection
template:
  containers:
    - name: books-service
      image: ilmred.azurecr.io/books-service:latest
      resources:
        cpu: 0.5
        memory: 1Gi
      env:
        - name: NODE_ENV
          value: production
        - name: COSMOS_CONNECTION
          secretRef: cosmos-connection
      probes:
        liveness:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 10
        readiness:
          httpGet:
            path: /ready
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5
  scale:
    minReplicas: 2
    maxReplicas: 100
    rules:
      - name: http-rule
        http:
          metadata:
            concurrentRequests: "100"
```

### 8.3 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yaml
name: Deploy to Azure

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm run test:unit
      - run: npm run test:integration

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/docker-login@v1
        with:
          login-server: ilmred.azurecr.io
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      - run: |
          docker build -t ilmred.azurecr.io/books-service:${{ github.sha }} .
          docker push ilmred.azurecr.io/books-service:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - uses: azure/container-apps-deploy-action@v1
        with:
          resourceGroup: ilm-red-prod
          containerAppName: books-service
          imageToDeploy: ilmred.azurecr.io/books-service:${{ github.sha }}
```

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

## 10. Appendices

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
