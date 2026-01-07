# ILM Red API - Pricing & Cost Analysis

## Subscription Tiers

### Free Tier
| Feature | Limit |
|---------|-------|
| Book uploads | 5 books |
| AI Chat sessions | 3/month |
| AI tokens | 10,000/day |
| Book summaries | None |
| Flashcard generation | None |
| Multi-book chat | No |
| Export to PDF | No |

### Premium Tier - $5/month
| Feature | Limit |
|---------|-------|
| Book uploads | Unlimited |
| AI Chat sessions | Unlimited |
| AI tokens | 100,000/day |
| Book summaries | 10/month |
| Flashcard generation | Unlimited |
| Quiz generation | Unlimited |
| Multi-book chat | Yes |
| Export to PDF | Yes |
| Ad-free reading | Yes |
| Priority support | Email |

### Enterprise Tier - Custom Pricing
| Feature | Limit |
|---------|-------|
| Everything in Premium | Yes |
| AI tokens | Unlimited |
| API requests | 1,000/min |
| Custom integrations | Yes |
| SLA guarantee | 99.9% |
| Dedicated support | Yes |

---

## AI Cost Analysis

### Multi-Vendor Model Pricing (Per 1M Tokens)

ILM Red supports multiple AI vendors for flexibility and cost optimization:

#### Qwen (Alibaba) - Default for Public Books
| Model | Input Cost | Output Cost | Context | Best For |
|-------|------------|-------------|---------|----------|
| qwen-turbo | $0.10 | $0.30 | 8K | **Default for public books** |
| qwen-plus | $0.40 | $1.20 | 32K | Better quality |
| qwen-max | $2.00 | $6.00 | 32K | Premium quality |

#### OpenAI - Default for Private Books
| Model | Input Cost | Output Cost | Context | Best For |
|-------|------------|-------------|---------|----------|
| gpt-4o-mini | $0.15 | $0.60 | 128K | **Default for private books** |
| gpt-4o | $2.50 | $10.00 | 128K | Complex analysis, vision |
| gpt-4-turbo | $10.00 | $30.00 | 128K | Most capable |
| o1-preview | $15.00 | $60.00 | 128K | Advanced reasoning |
| o1-mini | $3.00 | $12.00 | 128K | Efficient reasoning |

#### Anthropic (Claude)
| Model | Input Cost | Output Cost | Context | Best For |
|-------|------------|-------------|---------|----------|
| claude-3-haiku | $0.25 | $1.25 | 200K | Quick responses |
| claude-3-5-sonnet | $3.00 | $15.00 | 200K | Long-form content |
| claude-3-opus | $15.00 | $75.00 | 200K | Most capable |

#### Google (Gemini)
| Model | Input Cost | Output Cost | Context | Best For |
|-------|------------|-------------|---------|----------|
| gemini-1.5-flash | $0.075 | $0.30 | 1M | Fast, long context |
| gemini-1.5-pro | $1.25 | $5.00 | 2M | Best quality |
| gemini-2.0-flash | $0.10 | $0.40 | 1M | Experimental |

#### xAI (Grok)
| Model | Input Cost | Output Cost | Context | Best For |
|-------|------------|-------------|---------|----------|
| grok-beta | $0.50 | $1.50 | 131K | Alternative |
| grok-2 | $0.50 | $1.50 | 131K | Latest version |

#### DeepSeek
| Model | Input Cost | Output Cost | Context | Best For |
|-------|------------|-------------|---------|----------|
| deepseek-chat | $0.14 | $0.28 | 64K | Cost-effective alternative |
| deepseek-coder | $0.14 | $0.28 | 64K | Code-focused tasks |

#### Embedding Models
| Model | Vendor | Cost per 1M | Dimensions | Best For |
|-------|--------|-------------|------------|----------|
| text-embedding-3-small | OpenAI | $0.02 | 1536 | Default embeddings |
| text-embedding-3-large | OpenAI | $0.13 | 3072 | Higher quality |
| text-embedding-004 | Google | $0.025 | 768 | Alternative |

### Model Routing Strategy

**Public Books:** Use Qwen (qwen-turbo) by default
- Reason: Cost-effective at $0.40/1M tokens (combined)
- Accessible to all users including anonymous
- Good quality for general Q&A

**Private Books:** User's preferred model (default: gpt-4o-mini)
- Reason: Better quality for personal content
- Users can set their preferred model in preferences
- Premium users have access to all models

### Free vs Premium Model Access

| Model | Free Tier | Premium Tier |
|-------|-----------|--------------|
| qwen-turbo | Yes | Yes |
| gpt-4o-mini | Yes | Yes |
| gemini-1.5-flash | Yes | Yes |
| deepseek-chat | Yes | Yes |
| claude-3-haiku | Yes | Yes |
| All other models | No | Yes |

### Feature Costs

| Feature | Tokens/Use | Cost (GPT-4o-mini) |
|---------|------------|---------------------|
| Chat message | ~3,500 | $0.002 |
| Chapter summary | ~5,500 | $0.003 |
| Full book summary | ~53,000 | $0.03 |
| 20 Flashcards | ~10,000 | $0.005 |
| 10-question Quiz | ~9,000 | $0.005 |
| PDF Export | N/A | $0.0001 |

### Monthly Cost per User Type

| User Type | AI Cost | Infra Cost | Total | Profit at $5 |
|-----------|---------|------------|-------|--------------|
| Light (10 chats) | $0.03 | $0.10 | $0.13 | $4.87 (97%) |
| Average (50 chats) | $0.14 | $0.15 | $0.29 | $4.71 (94%) |
| Heavy (200 chats) | $0.53 | $0.25 | $0.78 | $4.22 (84%) |
| Power (500 chats) | $2.00 | $0.50 | $2.50 | $2.50 (50%) |

---

## Infrastructure Costs

### Startup Phase (1,000 users)

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Database | Cosmos DB (serverless) | $25 |
| Cache | Azure Redis (Basic) | $16 |
| Search | Azure AI Search (Free) | $0 |
| Storage | Blob Storage (10 GB) | $2 |
| CDN | Azure CDN (50 GB) | $4 |
| Compute | Container Apps | $15 |
| AI APIs | Multi-vendor (Qwen + OpenAI) | $40 |
| **Total** | | **$102** |

### Growth Phase (10,000 users)

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Database | Cosmos DB (4,000 RU/s) | $250 |
| Cache | Azure Redis (Standard) | $80 |
| Search | Azure AI Search (Basic) | $75 |
| Storage | Blob Storage (100 GB) | $20 |
| CDN | Azure CDN (500 GB) | $40 |
| Compute | Container Apps (2x) | $120 |
| AI APIs | Multi-vendor (Qwen primary) | $100 |
| Monitoring | App Insights | $30 |
| **Total** | | **$715** |

### Scale Phase (100,000 users)

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Database | Cosmos DB (geo-replicated) | $2,500 |
| Cache | Azure Redis (Premium) | $500 |
| Search | Azure AI Search (S2) | $500 |
| Storage | Blob Storage (1 TB) | $200 |
| CDN | Azure CDN (5 TB) | $400 |
| Compute | AKS Cluster | $800 |
| AI APIs | Multi-vendor (Qwen + premium mix) | $2,500 |
| Monitoring | Full suite | $300 |
| Security | WAF, DDoS | $200 |
| **Total** | | **$7,900** |

---

## Revenue Projections

| Scale | Total Users | Premium (10%) | Monthly Revenue | Costs | Profit | Margin |
|-------|-------------|---------------|-----------------|-------|--------|--------|
| Startup | 1,000 | 100 | $500 | $102 | $398 | 80% |
| Growth | 10,000 | 1,500 | $7,500 | $715 | $6,785 | 90% |
| Scale | 100,000 | 25,000 | $125,000 | $7,900 | $117,100 | 94% |

---

## Billing Implementation

### Token Tracking
Every AI request tracks:
- `promptTokens` - Input tokens consumed
- `completionTokens` - Output tokens generated
- `totalTokens` - Sum of both
- `costUsd` - Calculated cost with 40% markup

### Cost Calculation
```typescript
const calculateCost = (model: string, promptTokens: number, completionTokens: number) => {
  const pricing = MODEL_PRICING[model];
  const baseCost = (promptTokens / 1_000_000) * pricing.inputCost +
                   (completionTokens / 1_000_000) * pricing.outputCost;
  const markup = 1.4; // 40% platform margin
  return baseCost * markup;
};
```

### Daily Limits Enforcement
```typescript
const checkDailyLimit = async (userId: string, tier: 'free' | 'premium') => {
  const limits = { free: 10_000, premium: 100_000 };
  const todayUsage = await getTodayTokenUsage(userId);
  return todayUsage < limits[tier];
};
```

---

## Competitor Comparison

| App | Price | Key Differentiator |
|-----|-------|-------------------|
| Readwise | $8/mo | Highlights sync |
| Blinkist | $15/mo | Book summaries |
| Kindle Unlimited | $12/mo | Book access |
| Audible | $15/mo | Audiobooks |
| **ILM Red** | **$5/mo** | **AI chat + summaries + study tools** |

---

## Payment Integration

### Stripe Configuration
- Product: `ilm_plus_monthly`
- Price: $5.00/month
- Trial: 7 days free
- Currency: USD (multi-currency support planned)

### Webhook Events
- `checkout.session.completed` - Upgrade user to premium
- `invoice.payment_failed` - Send reminder, grace period
- `customer.subscription.deleted` - Downgrade to free tier

### API Endpoints
```
POST /v1/billing/subscribe     - Create subscription
POST /v1/billing/portal        - Access billing portal
GET  /v1/billing/subscription  - Get subscription status
POST /v1/billing/cancel        - Cancel subscription
```
