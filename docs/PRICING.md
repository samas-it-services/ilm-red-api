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

### Provider Costs (Per 1M Tokens)

| Model | Input Cost | Output Cost | Best For |
|-------|------------|-------------|----------|
| GPT-4o-mini | $0.15 | $0.60 | Default chat, summaries |
| GPT-4o | $2.50 | $10.00 | Complex analysis |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Long-form content |
| Claude 3 Haiku | $0.25 | $1.25 | Quick responses |
| text-embedding-3-small | $0.02 | N/A | Vector embeddings |

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
| AI APIs | OpenAI (pay-per-use) | $50 |
| **Total** | | **$112** |

### Growth Phase (10,000 users)

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Database | Cosmos DB (4,000 RU/s) | $250 |
| Cache | Azure Redis (Standard) | $80 |
| Search | Azure AI Search (Basic) | $75 |
| Storage | Blob Storage (100 GB) | $20 |
| CDN | Azure CDN (500 GB) | $40 |
| Compute | Container Apps (2x) | $120 |
| AI APIs | OpenAI | $150 |
| Monitoring | App Insights | $30 |
| **Total** | | **$765** |

### Scale Phase (100,000 users)

| Component | Service | Monthly Cost |
|-----------|---------|--------------|
| Database | Cosmos DB (geo-replicated) | $2,500 |
| Cache | Azure Redis (Premium) | $500 |
| Search | Azure AI Search (S2) | $500 |
| Storage | Blob Storage (1 TB) | $200 |
| CDN | Azure CDN (5 TB) | $400 |
| Compute | AKS Cluster | $800 |
| AI APIs | OpenAI | $3,750 |
| Monitoring | Full suite | $300 |
| Security | WAF, DDoS | $200 |
| **Total** | | **$9,150** |

---

## Revenue Projections

| Scale | Total Users | Premium (10%) | Monthly Revenue | Costs | Profit | Margin |
|-------|-------------|---------------|-----------------|-------|--------|--------|
| Startup | 1,000 | 100 | $500 | $112 | $388 | 78% |
| Growth | 10,000 | 1,500 | $7,500 | $765 | $6,735 | 90% |
| Scale | 100,000 | 25,000 | $125,000 | $9,150 | $115,850 | 93% |

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
