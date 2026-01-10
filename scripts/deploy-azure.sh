#!/usr/bin/env bash
# scripts/deploy-azure.sh - Deploy ILM Red API to Azure
#
# This script deploys all Azure infrastructure and the API container.
#
# Usage:
#   ./scripts/deploy-azure.sh [environment] [options]
#
# Environments:
#   dev     Development environment
#   staging Staging environment
#   prod    Production environment (default)
#
# Options:
#   --infra-only    Deploy only infrastructure (no container)
#   --app-only      Deploy only application (assumes infra exists)
#   --skip-build    Skip Docker image build
#   --help          Show this help message
#
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$PROJECT_ROOT/infra"

# Default configuration
ENVIRONMENT="${1:-prod}"
LOCATION="westus2"  # Changed from eastus due to PostgreSQL quota restrictions
RESOURCE_GROUP="ilmred-${ENVIRONMENT}-rg"
DEPLOYMENT_NAME="ilmred-${ENVIRONMENT}-$(date +%Y%m%d%H%M%S)"

# Flags
INFRA_ONLY=false
APP_ONLY=false
SKIP_BUILD=false

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
    echo -e "${CYAN}[i]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[→]${NC} $1"
}

# Show usage
show_help() {
    echo "Usage: $0 [environment] [options]"
    echo ""
    echo "Environments:"
    echo "  dev       Development environment"
    echo "  staging   Staging environment"
    echo "  prod      Production environment (default)"
    echo ""
    echo "Options:"
    echo "  --infra-only    Deploy only infrastructure (no container)"
    echo "  --app-only      Deploy only application (assumes infra exists)"
    echo "  --skip-build    Skip Docker image build"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 prod                  # Full deployment to production"
    echo "  $0 dev --infra-only      # Deploy dev infrastructure only"
    echo "  $0 prod --app-only       # Update prod container only"
    exit 0
}

# Parse arguments
parse_args() {
    for arg in "$@"; do
        case "$arg" in
            dev|staging|prod)
                ENVIRONMENT="$arg"
                RESOURCE_GROUP="ilmred-${ENVIRONMENT}-rg"
                ;;
            --infra-only)
                INFRA_ONLY=true
                ;;
            --app-only)
                APP_ONLY=true
                ;;
            --skip-build)
                SKIP_BUILD=true
                ;;
            --help|-h)
                show_help
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing=0

    # Azure CLI
    if command -v az &> /dev/null; then
        print_status "Azure CLI: $(az version --query '"azure-cli"' -o tsv 2>/dev/null)"
    else
        print_error "Azure CLI not found. Run ./scripts/setup-azure.sh first"
        missing=1
    fi

    # Docker
    if command -v docker &> /dev/null; then
        print_status "Docker: $(docker --version | head -1)"
    else
        print_error "Docker not found"
        missing=1
    fi

    # Check Azure login
    if az account show &> /dev/null; then
        print_status "Azure login: $(az account show --query user.name -o tsv)"
    else
        print_error "Not logged in to Azure. Run: az login"
        missing=1
    fi

    # Check parameters file
    if [ -f "$INFRA_DIR/parameters.json" ]; then
        print_status "Parameters file: infra/parameters.json"
    else
        print_warning "Parameters file not found"
        print_info "Creating from example..."
        if [ -f "$INFRA_DIR/parameters.example.json" ]; then
            cp "$INFRA_DIR/parameters.example.json" "$INFRA_DIR/parameters.json"
            print_warning "Please edit infra/parameters.json with your API keys"
            print_info "At minimum, set jwtSecret (use: openssl rand -base64 32)"
            missing=1
        else
            print_error "No parameters.example.json found"
            missing=1
        fi
    fi

    # Check Bicep files
    if [ -f "$INFRA_DIR/main.bicep" ]; then
        print_status "Bicep templates: infra/main.bicep"
    else
        print_error "Bicep template not found: infra/main.bicep"
        missing=1
    fi

    if [ $missing -eq 1 ]; then
        echo ""
        print_error "Prerequisites not met. Please fix the issues above."
        exit 1
    fi

    print_status "All prerequisites satisfied"
}

# Create resource group
create_resource_group() {
    print_header "Creating Resource Group"

    if az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        print_status "Resource group already exists: $RESOURCE_GROUP"
    else
        print_step "Creating resource group: $RESOURCE_GROUP in $LOCATION"
        az group create \
            --name "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --tags "environment=$ENVIRONMENT" "project=ilm-red-api"
        print_status "Resource group created"
    fi
}

# Deploy infrastructure with Bicep
deploy_infrastructure() {
    print_header "Deploying Infrastructure"

    print_info "This may take 10-15 minutes..."
    print_info "Deploying: Container Registry, PostgreSQL, Redis, Storage, Key Vault, Container Apps"
    echo ""

    # Load parameters and add environment
    local params_file="$INFRA_DIR/parameters.json"

    print_step "Starting Bicep deployment: $DEPLOYMENT_NAME"

    az deployment group create \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$INFRA_DIR/main.bicep" \
        --parameters "@$params_file" \
        --parameters environment="$ENVIRONMENT" location="$LOCATION" \
        --verbose

    print_status "Infrastructure deployment complete"

    # Get outputs
    print_step "Retrieving deployment outputs..."

    ACR_LOGIN_SERVER=$(az deployment group show \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.outputs.acrLoginServer.value" -o tsv)

    API_URL=$(az deployment group show \
        --name "$DEPLOYMENT_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.outputs.apiUrl.value" -o tsv 2>/dev/null || echo "pending")

    print_status "ACR Login Server: $ACR_LOGIN_SERVER"
    print_status "API URL: $API_URL"
}

# Build and push Docker image
build_and_push_image() {
    print_header "Building and Pushing Docker Image"

    # Get ACR name from resource group
    local acr_name=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" -o tsv)

    if [ -z "$acr_name" ]; then
        print_error "Container Registry not found in $RESOURCE_GROUP"
        exit 1
    fi

    local acr_login_server=$(az acr show --name "$acr_name" --query "loginServer" -o tsv)
    local image_tag="$acr_login_server/ilm-red-api:latest"
    local image_tag_version="$acr_login_server/ilm-red-api:$(date +%Y%m%d%H%M%S)"

    # Login to ACR
    print_step "Logging in to Container Registry..."
    az acr login --name "$acr_name"

    if [ "$SKIP_BUILD" = false ]; then
        # Build image
        # IMPORTANT: Always use --platform linux/amd64 for Azure deployment
        # Mac ARM64 builds will fail with "exec format error" on Azure AMD64
        print_step "Building Docker image (linux/amd64 for Azure)..."
        docker build \
            --platform linux/amd64 \
            -f "$PROJECT_ROOT/docker/Dockerfile" \
            -t "$image_tag" \
            -t "$image_tag_version" \
            "$PROJECT_ROOT"

        print_status "Image built: $image_tag"
    fi

    # Push image
    print_step "Pushing image to Azure Container Registry..."
    docker push "$image_tag"
    docker push "$image_tag_version"

    print_status "Image pushed: $image_tag"

    # Store for later use
    ACR_LOGIN_SERVER="$acr_login_server"
    IMAGE_TAG="$image_tag"
}

# Update Container App with new image
update_container_app() {
    print_header "Updating Container App"

    local app_name="ilmred-${ENVIRONMENT}-api"

    # Check if container app exists
    if az containerapp show --name "$app_name" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        print_step "Updating container app: $app_name"

        az containerapp update \
            --name "$app_name" \
            --resource-group "$RESOURCE_GROUP" \
            --image "$IMAGE_TAG"

        print_status "Container app updated"
    else
        print_warning "Container app not found. It will be created during infrastructure deployment."
    fi
}

# Verify app health after deployment
# Note: Migrations run automatically on container startup via entrypoint.sh
verify_app_health() {
    print_header "Verifying Application Health"

    local app_name="ilmred-${ENVIRONMENT}-api"

    print_info "Migrations run automatically on container startup (via entrypoint.sh)"
    print_step "Waiting for app to be ready..."

    local app_url=$(az containerapp show \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")

    if [ -n "$app_url" ]; then
        print_info "Container App URL: https://$app_url"
        sleep 30

        # Health check
        local health_status=$(curl -s -o /dev/null -w "%{http_code}" "https://$app_url/v1/health" 2>/dev/null || echo "000")

        if [ "$health_status" = "200" ]; then
            print_status "App is healthy!"
        else
            print_warning "App returned status: $health_status"
            print_info "Check logs: az containerapp logs show --name $app_name --resource-group $RESOURCE_GROUP"
            print_info "If you see database errors, verify migrations ran:"
            print_info "  az containerapp exec --name $app_name --resource-group $RESOURCE_GROUP --command 'alembic current'"
        fi
    fi
}

# Print deployment summary
print_summary() {
    print_header "Deployment Complete!"

    local app_name="ilmred-${ENVIRONMENT}-api"
    local app_url=$(az containerapp show \
        --name "$app_name" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "pending")

    echo ""
    echo -e "${GREEN}ILM Red API deployed successfully!${NC}"
    echo ""
    echo "Resources created in: $RESOURCE_GROUP"
    echo ""
    echo "Endpoints:"
    echo -e "  ${CYAN}API URL:${NC}     https://$app_url"
    echo -e "  ${CYAN}Health:${NC}      https://$app_url/health"
    echo -e "  ${CYAN}Swagger:${NC}     https://$app_url/docs"
    echo -e "  ${CYAN}ReDoc:${NC}       https://$app_url/redoc"
    echo ""
    echo "Useful commands:"
    echo "  # View logs"
    echo "  az containerapp logs show --name $app_name --resource-group $RESOURCE_GROUP --follow"
    echo ""
    echo "  # Scale replicas"
    echo "  az containerapp update --name $app_name --resource-group $RESOURCE_GROUP --min-replicas 1"
    echo ""
    echo "  # Restart app"
    echo "  az containerapp revision restart --name $app_name --resource-group $RESOURCE_GROUP"
    echo ""
    echo -e "${YELLOW}Estimated monthly cost: ~\$35 (idle) to ~\$67 (1K users)${NC}"
    echo ""
}

# Cleanup on error
cleanup_on_error() {
    print_error "Deployment failed!"
    print_info "To clean up resources, run:"
    print_info "  az group delete --name $RESOURCE_GROUP --yes"
}

trap cleanup_on_error ERR

# Main function
main() {
    parse_args "$@"

    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         ILM Red API - Azure Deployment                    ║${NC}"
    echo -e "${BLUE}║         Environment: ${ENVIRONMENT}                                   ║${NC}"
    echo -e "${BLUE}║         Region: ${LOCATION}                                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    check_prerequisites
    create_resource_group

    if [ "$APP_ONLY" = false ]; then
        deploy_infrastructure
    fi

    if [ "$INFRA_ONLY" = false ]; then
        build_and_push_image
        update_container_app
        verify_app_health
    fi

    print_summary
}

main "$@"
