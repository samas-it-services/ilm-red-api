#!/bin/bash
# scripts/dev-with-data.sh - Start local development with seeded data
#
# This script:
# 1. Starts PostgreSQL and Redis in Docker
# 2. Waits for the database to be ready
# 3. Runs database migrations
# 4. Imports seed data
# 5. Starts the API server
#
# Usage:
#   ./scripts/dev-with-data.sh [--reset]
#
# Options:
#   --reset: Clear existing data and re-import fresh seeds
#   --no-seed: Skip importing seed data
#   --db-only: Only start database, don't run API
#
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

# Parse arguments
RESET=false
SKIP_SEED=false
DB_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --reset)
            RESET=true
            ;;
        --no-seed)
            SKIP_SEED=true
            ;;
        --db-only)
            DB_ONLY=true
            ;;
    esac
done

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║         ILM Red API - Local Development                   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Change to docker directory
cd "$DOCKER_DIR"

# Step 1: Start database services
echo -e "${BLUE}[1/5]${NC} Starting PostgreSQL and Redis..."
docker compose up -d db redis

# Step 2: Wait for PostgreSQL
echo -e "${BLUE}[2/5]${NC} Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker compose exec -T db pg_isready -U postgres -d ilmred &> /dev/null; then
        echo -e "${GREEN}  PostgreSQL is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "  Waiting... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: PostgreSQL did not start in time${NC}"
    exit 1
fi

# Step 3: Run migrations
echo -e "${BLUE}[3/5]${NC} Running database migrations..."
cd "$PROJECT_ROOT"

if ! poetry run alembic upgrade head 2>/dev/null; then
    # Try with docker if poetry not available
    cd "$DOCKER_DIR"
    docker compose run --rm api alembic upgrade head
    cd "$PROJECT_ROOT"
fi

echo -e "${GREEN}  Migrations complete${NC}"

# Step 4: Import seed data
if [ "$SKIP_SEED" = false ]; then
    echo -e "${BLUE}[4/5]${NC} Importing seed data..."

    # Check if seeds exist
    if [ -d "$PROJECT_ROOT/seeds" ] && [ -f "$PROJECT_ROOT/seeds/books.json" ]; then
        if [ "$RESET" = true ]; then
            poetry run python scripts/import_test_data.py --clear 2>/dev/null || \
                docker compose -f "$DOCKER_DIR/docker-compose.yml" run --rm api python scripts/import_test_data.py --clear
        else
            poetry run python scripts/import_test_data.py 2>/dev/null || \
                docker compose -f "$DOCKER_DIR/docker-compose.yml" run --rm api python scripts/import_test_data.py
        fi
        echo -e "${GREEN}  Seed data imported${NC}"
    else
        echo -e "${YELLOW}  No seed data found. Run 'python scripts/export_test_data.py' first${NC}"
    fi
else
    echo -e "${BLUE}[4/5]${NC} Skipping seed data import"
fi

# Step 5: Start API
if [ "$DB_ONLY" = true ]; then
    echo -e "${BLUE}[5/5]${NC} Database ready (--db-only mode)"
    echo ""
    echo -e "${GREEN}Database is running!${NC}"
    echo ""
    echo "Connection details:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: ilmred"
    echo "  User: postgres"
    echo "  Password: postgres"
    echo ""
    echo "Redis:"
    echo "  Host: localhost"
    echo "  Port: 6379"
    echo ""
    echo "To start the API manually:"
    echo "  poetry run uvicorn app.main:app --reload"
    exit 0
fi

echo -e "${BLUE}[5/5]${NC} Starting API server..."
echo ""
echo -e "${GREEN}Development environment ready!${NC}"
echo ""
echo "API Endpoints:"
echo "  Health:  http://localhost:8000/v1/health"
echo "  Swagger: http://localhost:8000/docs"
echo "  ReDoc:   http://localhost:8000/redoc"
echo ""
echo "Services:"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start API with hot reload
cd "$PROJECT_ROOT"
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
