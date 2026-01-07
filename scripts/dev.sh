#!/usr/bin/env bash
# scripts/dev.sh - Local development setup and run script for ILM Red API
#
# Usage:
#   ./scripts/dev.sh           # Full setup: start services, run migrations, start API
#   ./scripts/dev.sh setup     # Only setup (no API start)
#   ./scripts/dev.sh start     # Only start API (assumes services running)
#   ./scripts/dev.sh stop      # Stop all Docker services
#   ./scripts/dev.sh reset     # Reset database (destructive!)
#   ./scripts/dev.sh logs      # Show Docker logs
#   ./scripts/dev.sh test      # Run tests
#
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"

# Helper functions
print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing=0

    # Check Docker
    if command_exists docker; then
        print_status "Docker installed: $(docker --version | head -1)"
    else
        print_error "Docker not found. Please install Docker Desktop:"
        print_info "  https://www.docker.com/products/docker-desktop"
        missing=1
    fi

    # Check Docker Compose
    if command_exists docker-compose || docker compose version &> /dev/null; then
        if docker compose version &> /dev/null; then
            print_status "Docker Compose installed: $(docker compose version --short 2>/dev/null || echo 'v2+')"
        else
            print_status "Docker Compose installed: $(docker-compose --version)"
        fi
    else
        print_error "Docker Compose not found."
        missing=1
    fi

    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        print_status "Docker daemon is running"
    else
        print_error "Docker daemon is not running. Please start Docker Desktop."
        missing=1
    fi

    # Check Python
    if command_exists python3; then
        print_status "Python installed: $(python3 --version)"
    else
        print_error "Python 3 not found. Please install Python 3.12+:"
        print_info "  https://www.python.org/downloads/"
        missing=1
    fi

    # Check Poetry
    if command_exists poetry; then
        print_status "Poetry installed: $(poetry --version)"
    else
        print_error "Poetry not found. Please install Poetry:"
        print_info "  curl -sSL https://install.python-poetry.org | python3 -"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        echo ""
        print_error "Missing prerequisites. Please install them and try again."
        exit 1
    fi

    print_status "All prerequisites satisfied!"
}

# Setup environment file
setup_env() {
    print_header "Setting Up Environment"

    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        if [ -f "$PROJECT_ROOT/.env.example" ]; then
            cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
            print_status "Created .env from .env.example"
            print_warning "Please update .env with your API keys (especially AI provider keys)"
            echo ""
            print_info "Required API keys for AI features:"
            print_info "  - OPENAI_API_KEY (recommended)"
            print_info "  - QWEN_API_KEY (default for public books)"
            print_info "  - Optional: ANTHROPIC_API_KEY, GOOGLE_API_KEY, XAI_API_KEY, DEEPSEEK_API_KEY"
        else
            print_error ".env.example not found!"
            exit 1
        fi
    else
        print_status ".env file already exists"
    fi
}

# Install Python dependencies
install_deps() {
    print_header "Installing Python Dependencies"

    cd "$PROJECT_ROOT"

    if [ ! -d ".venv" ] && [ -z "$VIRTUAL_ENV" ]; then
        print_info "Creating virtual environment..."
        poetry install
    else
        print_info "Updating dependencies..."
        poetry install
    fi

    print_status "Dependencies installed"
}

# Docker compose command helper
docker_compose() {
    if docker compose version &> /dev/null; then
        docker compose -f "$DOCKER_DIR/docker-compose.yml" "$@"
    else
        docker-compose -f "$DOCKER_DIR/docker-compose.yml" "$@"
    fi
}

# Start Docker services (db and redis only)
start_services() {
    print_header "Starting Docker Services"

    print_info "Starting PostgreSQL and Redis..."
    docker_compose up -d db redis

    print_status "Docker services started"
}

# Wait for database to be healthy
wait_for_db() {
    print_header "Waiting for Database"

    local max_attempts=30
    local attempt=1

    print_info "Waiting for PostgreSQL to be ready..."

    while [ $attempt -le $max_attempts ]; do
        if docker_compose exec -T db pg_isready -U postgres &> /dev/null; then
            print_status "PostgreSQL is ready!"
            return 0
        fi

        echo -n "."
        sleep 1
        attempt=$((attempt + 1))
    done

    echo ""
    print_error "PostgreSQL failed to start within ${max_attempts} seconds"
    print_info "Check logs with: ./scripts/dev.sh logs"
    exit 1
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    cd "$PROJECT_ROOT"

    print_info "Running Alembic migrations..."
    poetry run alembic upgrade head

    print_status "Migrations completed"
}

# Start the API server
start_api() {
    print_header "Starting API Server"

    cd "$PROJECT_ROOT"

    echo ""
    print_info "Starting FastAPI with hot-reload..."
    print_info "API will be available at:"
    echo ""
    echo -e "    ${GREEN}http://localhost:8000${NC}        - API base URL"
    echo -e "    ${GREEN}http://localhost:8000/docs${NC}   - Swagger UI"
    echo -e "    ${GREEN}http://localhost:8000/redoc${NC}  - ReDoc"
    echo -e "    ${GREEN}http://localhost:8000/health${NC} - Health check"
    echo ""
    print_info "Press Ctrl+C to stop the server"
    echo ""

    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
}

# Stop all services
stop_services() {
    print_header "Stopping Services"

    docker_compose down

    print_status "All services stopped"
}

# Reset database (destructive)
reset_db() {
    print_header "Resetting Database"

    print_warning "This will DELETE all data in the database!"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker_compose down -v
        print_status "Database volumes removed"

        start_services
        wait_for_db
        run_migrations

        print_status "Database reset complete"
    else
        print_info "Reset cancelled"
    fi
}

# Show Docker logs
show_logs() {
    docker_compose logs -f
}

# Run tests
run_tests() {
    print_header "Running Tests"

    cd "$PROJECT_ROOT"

    poetry run pytest "$@"
}

# Main entry point
main() {
    local command="${1:-}"

    case "$command" in
        setup)
            check_prerequisites
            setup_env
            install_deps
            start_services
            wait_for_db
            run_migrations
            print_header "Setup Complete!"
            print_info "Run './scripts/dev.sh start' to start the API server"
            ;;
        start)
            start_api
            ;;
        stop)
            stop_services
            ;;
        reset)
            reset_db
            ;;
        logs)
            show_logs
            ;;
        test)
            shift
            run_tests "$@"
            ;;
        help|--help|-h)
            echo "ILM Red API - Local Development Script"
            echo ""
            echo "Usage: ./scripts/dev.sh [command]"
            echo ""
            echo "Commands:"
            echo "  (none)    Full setup and start (default)"
            echo "  setup     Setup only (no API start)"
            echo "  start     Start API server only"
            echo "  stop      Stop all Docker services"
            echo "  reset     Reset database (destructive!)"
            echo "  logs      Show Docker logs"
            echo "  test      Run tests (pass pytest args)"
            echo "  help      Show this help message"
            ;;
        *)
            # Default: full setup and start
            check_prerequisites
            setup_env
            install_deps
            start_services
            wait_for_db
            run_migrations
            start_api
            ;;
    esac
}

main "$@"
