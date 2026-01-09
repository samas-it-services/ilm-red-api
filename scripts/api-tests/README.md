# ILM Red API Test Scripts

This directory contains shell scripts with curl commands to test all features of the ILM Red API deployed on Azure.

## Azure Deployment Details

| Resource | Value |
|----------|-------|
| **API URL** | `https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io` |
| **Health Endpoint** | `https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/v1/health` |
| **Region** | `westus2` |
| **Resource Group** | `ilmred-prod-rg` |

### Azure Resources

| Resource | Name/URL |
|----------|----------|
| PostgreSQL | `ilmred-prod-postgres.postgres.database.azure.com` |
| Redis | `ilmred-prod-redis.redis.cache.windows.net` |
| Container Registry | `ilmredprodacr.azurecr.io` |
| Storage Account | `ilmredprodstorage` |
| Key Vault | `ilmred-prod-kv-3gfbth` |

## Quick Start

```bash
# 1. Test health endpoint (no auth required)
./01-health/test-health.sh

# 2. Register a test user
./02-auth/test-register.sh

# 3. Login to get access token
./02-auth/test-login.sh

# 4. Test authenticated endpoints
./04-users/test-get-me.sh

# Run all tests in sequence
./run-all-tests.sh
```

## Directory Structure

```
api-tests/
├── README.md                 # This file
├── config.sh                 # Shared configuration
├── run-all-tests.sh          # Master test runner
├── 01-health/
│   └── test-health.sh        # Health check tests
├── 02-auth/
│   ├── test-register.sh      # User registration
│   ├── test-login.sh         # User login
│   ├── test-refresh.sh       # Token refresh
│   └── test-logout.sh        # Logout
├── 03-api-keys/
│   ├── test-create-key.sh    # Create API key
│   ├── test-list-keys.sh     # List API keys
│   └── test-delete-key.sh    # Delete API key
├── 04-users/
│   ├── test-get-me.sh        # Get current user profile
│   ├── test-update-me.sh     # Update user profile
│   └── test-get-user.sh      # Get public user profile
├── 05-books/
│   ├── test-upload-book.sh   # Upload a book
│   ├── test-list-books.sh    # List books
│   ├── test-get-book.sh      # Get book details
│   ├── test-update-book.sh   # Update book metadata
│   ├── test-download-book.sh # Get download URL
│   └── test-delete-book.sh   # Delete a book
├── 06-ratings/
│   ├── test-add-rating.sh    # Rate a book
│   ├── test-list-ratings.sh  # List book ratings
│   └── test-delete-rating.sh # Delete your rating
└── 07-favorites/
    ├── test-add-favorite.sh     # Add book to favorites
    ├── test-list-favorites.sh   # List favorite books
    └── test-remove-favorite.sh  # Remove from favorites
```

## Authentication

### Bearer Token (JWT)
Most endpoints require authentication via JWT token:
```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/v1/users/me
```

### API Key
Alternatively, you can use an API key:
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/v1/users/me
```

## API Endpoints Reference

### Health Check
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/health` | No | Check API health status |

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/auth/register` | No | Register new user |
| POST | `/v1/auth/login` | No | Login and get tokens |
| POST | `/v1/auth/refresh` | No | Refresh access token |
| POST | `/v1/auth/logout` | No | Revoke refresh token |

### API Keys
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/auth/api-keys` | Yes | List your API keys |
| POST | `/v1/auth/api-keys` | Yes | Create new API key |
| DELETE | `/v1/auth/api-keys/{id}` | Yes | Delete an API key |

### Users
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/v1/users/me` | Yes | Get your profile |
| PATCH | `/v1/users/me` | Yes | Update your profile |
| GET | `/v1/users/{id}` | No | Get public profile |

### Books
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/books` | Yes | Upload a book |
| GET | `/v1/books` | Optional | List books |
| GET | `/v1/books/{id}` | Optional | Get book details |
| PATCH | `/v1/books/{id}` | Yes | Update book metadata |
| DELETE | `/v1/books/{id}` | Yes | Delete a book |
| GET | `/v1/books/{id}/download` | Optional | Get download URL |

### Ratings
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/books/{id}/ratings` | Yes | Rate a book |
| GET | `/v1/books/{id}/ratings` | No | Get book ratings |
| DELETE | `/v1/books/{id}/ratings` | Yes | Delete your rating |

### Favorites
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/v1/books/{id}/favorite` | Yes | Add to favorites |
| DELETE | `/v1/books/{id}/favorite` | Yes | Remove from favorites |
| GET | `/v1/books/me/favorites` | Yes | List your favorites |

## Example Responses

### Health Check
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2026-01-08T12:00:00Z",
  "checks": {
    "database": "healthy"
  }
}
```

### Login Response
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "dGhpc2lzYXJlZnJlc2h0b2tlbg==",
  "token_type": "bearer",
  "expires_in": 900
}
```

### User Profile
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "display_name": "John Doe",
  "roles": ["user"],
  "created_at": "2026-01-01T12:00:00Z"
}
```

### Book Response
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Introduction to Islamic Finance",
  "author": "Muhammad Ibn Ahmad",
  "category": "fiqh",
  "visibility": "public",
  "file_type": "pdf",
  "status": "ready",
  "created_at": "2026-01-01T12:00:00Z"
}
```

## Configuration

### Environment Variables
You can override the default configuration:

```bash
# Use a different API URL
export API_BASE_URL="https://your-custom-api.com"

# Enable debug output
export DEBUG=1

# Then run tests
./01-health/test-health.sh
```

### Token Storage
Tokens are stored in `.test-data/tokens.json` after login. This directory is gitignored.

## Prerequisites

- **curl**: HTTP client (pre-installed on most systems)
- **jq**: JSON processor for parsing responses
  ```bash
  # macOS
  brew install jq

  # Ubuntu/Debian
  sudo apt install jq
  ```

## Troubleshooting

### Common HTTP Errors

#### 500 Internal Server Error
This usually indicates a server-side issue. Common causes:

1. **Database migrations not run** - Tables don't exist
   ```bash
   # Check container logs for migration errors
   az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --tail 100

   # Look for errors like:
   # - "relation does not exist"
   # - "UndefinedTable"
   # - "alembic" errors
   ```

2. **Database connection issues**
   ```bash
   # Check if PostgreSQL is accessible
   az postgres flexible-server show --name ilmred-prod-postgres --resource-group ilmred-prod-rg \
     --query "{state:state,version:version}"
   ```

3. **Missing environment variables**
   ```bash
   # Check container app configuration
   az containerapp show --name ilmred-prod-api --resource-group ilmred-prod-rg \
     --query "properties.template.containers[0].env[*].name"
   ```

**Fix**: Restart the container to trigger migrations:
```bash
az containerapp revision restart --name ilmred-prod-api --resource-group ilmred-prod-rg --revision $(az containerapp revision list --name ilmred-prod-api --resource-group ilmred-prod-rg --query "[0].name" -o tsv)
```

#### 401 Unauthorized
Your token may have expired. Login again:
```bash
./02-auth/test-login.sh
```

#### 403 Forbidden
You don't have permission for this action. Check:
- Are you the owner of the resource?
- Do you have the required role?

#### 404 Not Found
- Check the endpoint URL is correct
- Verify the resource ID exists

#### 422 Validation Error
Request data is invalid. Check:
- Required fields are provided
- Data types are correct (e.g., valid email format)
- Values are within allowed ranges

### "Not logged in" Error
Run the login script first:
```bash
./02-auth/test-login.sh
```

### Connection Refused / Timeout
1. Check if API is running:
   ```bash
   curl -v https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io/v1/health
   ```

2. Check Azure Container App status:
   ```bash
   az containerapp show --name ilmred-prod-api --resource-group ilmred-prod-rg \
     --query "{state:properties.runningStatus,replicas:properties.template.scale}"
   ```

3. Check for recent failures:
   ```bash
   az containerapp revision list --name ilmred-prod-api --resource-group ilmred-prod-rg \
     --query "[].{name:name,active:properties.active,healthy:properties.healthState}" -o table
   ```

### Viewing Logs

#### Stream Live Logs
```bash
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --follow
```

#### View Recent Logs
```bash
# Last 100 lines
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --tail 100

# Filter by time (last 30 minutes)
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg \
  --tail 500 --since 30m
```

#### View System Logs (startup, health checks)
```bash
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg \
  --type system --tail 50
```

### Database Operations

#### Check Migration Status
The container runs `alembic upgrade head` on startup via `docker/entrypoint.sh`.
To verify migrations ran, check the logs:
```bash
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --tail 100 | grep -i "migration\|alembic"
```

#### Force Migration Re-run
Restart the container to re-run migrations:
```bash
# Get current revision name
REVISION=$(az containerapp revision list --name ilmred-prod-api --resource-group ilmred-prod-rg --query "[0].name" -o tsv)

# Restart it
az containerapp revision restart --name ilmred-prod-api --resource-group ilmred-prod-rg --revision $REVISION
```

### Container Management

#### Restart the Application
```bash
REVISION=$(az containerapp revision list --name ilmred-prod-api --resource-group ilmred-prod-rg --query "[0].name" -o tsv)
az containerapp revision restart --name ilmred-prod-api --resource-group ilmred-prod-rg --revision $REVISION
```

#### Scale Replicas (prevent cold starts)
```bash
# Scale to 1 minimum replica
az containerapp update --name ilmred-prod-api --resource-group ilmred-prod-rg --min-replicas 1

# Scale back to 0 (cost savings, allows cold starts)
az containerapp update --name ilmred-prod-api --resource-group ilmred-prod-rg --min-replicas 0
```

#### Deploy New Image
```bash
# Login to ACR
az acr login --name ilmredprodacr

# Build and push
docker build -f docker/Dockerfile -t ilmredprodacr.azurecr.io/ilm-red-api:latest .
docker push ilmredprodacr.azurecr.io/ilm-red-api:latest

# Update container app
az containerapp update --name ilmred-prod-api --resource-group ilmred-prod-rg \
  --image ilmredprodacr.azurecr.io/ilm-red-api:latest
```

### Known Issues

1. **Cold Start Latency**: First request after idle period may take 10-30 seconds while container starts
   - Fix: Set `--min-replicas 1` (increases cost)

2. **Token Expiry**: Access tokens expire in 15 minutes
   - Fix: Use refresh token to get new access token, or login again

3. **Rate Limiting**: API may return 429 if too many requests
   - Fix: Add delays between requests or reduce request rate

## Azure Management Commands

```bash
# View Container App logs
az containerapp logs show --name ilmred-prod-api --resource-group ilmred-prod-rg --follow

# Check app status
az containerapp show --name ilmred-prod-api --resource-group ilmred-prod-rg \
  --query "{state:properties.runningStatus,replicas:properties.template.scale}"

# Restart the app
az containerapp revision restart --name ilmred-prod-api --resource-group ilmred-prod-rg

# Scale to 1 replica (prevent cold starts)
az containerapp update --name ilmred-prod-api --resource-group ilmred-prod-rg --min-replicas 1
```

## Cleanup

Remove test data:
```bash
rm -rf .test-data/
```
