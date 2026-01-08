#!/usr/bin/env bash
# scripts/setup-azure.sh - First-time Azure account and CLI setup
#
# This script helps you set up Azure CLI and prepare your account
# for deploying the ILM Red API.
#
# Usage: ./scripts/setup-azure.sh
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

# Check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*) echo "macos" ;;
        Linux*)  echo "linux" ;;
        MINGW*|MSYS*|CYGWIN*) echo "windows" ;;
        *) echo "unknown" ;;
    esac
}

# Install Azure CLI
install_azure_cli() {
    local os=$(detect_os)

    print_header "Installing Azure CLI"

    case "$os" in
        macos)
            if command_exists brew; then
                print_step "Installing via Homebrew..."
                brew update && brew install azure-cli
            else
                print_step "Installing via direct download..."
                curl -L https://aka.ms/InstallAzureCli | bash
            fi
            ;;
        linux)
            print_step "Installing via Microsoft repository..."
            curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
            ;;
        windows)
            print_error "On Windows, please install Azure CLI manually:"
            print_info "  https://aka.ms/installazurecliwindows"
            print_info "  Or run: winget install -e --id Microsoft.AzureCLI"
            exit 1
            ;;
        *)
            print_error "Unknown operating system. Please install Azure CLI manually:"
            print_info "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
            exit 1
            ;;
    esac

    print_status "Azure CLI installed successfully"
}

# Check Azure CLI installation
check_azure_cli() {
    print_header "Checking Azure CLI"

    if command_exists az; then
        local version=$(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "unknown")
        print_status "Azure CLI installed: v$version"
        return 0
    else
        print_warning "Azure CLI not found"

        read -p "Would you like to install Azure CLI? (y/N) " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_azure_cli
        else
            print_error "Azure CLI is required. Please install it manually:"
            print_info "  https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
            exit 1
        fi
    fi
}

# Check Docker installation
check_docker() {
    print_header "Checking Docker"

    if command_exists docker; then
        local version=$(docker --version 2>/dev/null | head -1)
        print_status "Docker installed: $version"

        if docker info &> /dev/null; then
            print_status "Docker daemon is running"
        else
            print_warning "Docker daemon is not running. Please start Docker Desktop."
        fi
    else
        print_warning "Docker not found. It's required for building container images."
        print_info "  Install from: https://www.docker.com/products/docker-desktop"
    fi
}

# Azure login
azure_login() {
    print_header "Azure Login"

    # Check if already logged in
    if az account show &> /dev/null; then
        local account=$(az account show --query "name" -o tsv)
        local user=$(az account show --query "user.name" -o tsv)
        print_status "Already logged in as: $user"
        print_info "Subscription: $account"

        read -p "Continue with this account? (Y/n) " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Nn]$ ]]; then
            print_step "Logging out..."
            az logout
            print_step "Please log in with your Azure account..."
            az login
        fi
    else
        print_step "Please log in with your Azure account..."
        print_info "A browser window will open for authentication."
        echo ""
        az login
    fi

    print_status "Azure login successful"
}

# Select subscription
select_subscription() {
    print_header "Select Azure Subscription"

    # List subscriptions
    local subs=$(az account list --query "[].{Name:name, ID:id, State:state}" -o table)

    if [ -z "$subs" ]; then
        print_error "No Azure subscriptions found!"
        print_info ""
        print_info "To create a free Azure account:"
        print_info "  1. Go to https://azure.microsoft.com/free/"
        print_info "  2. Click 'Start free'"
        print_info "  3. Sign in with your Microsoft account"
        print_info "  4. Complete the registration"
        print_info ""
        print_info "After creating an account, run this script again."
        exit 1
    fi

    echo ""
    echo "Available subscriptions:"
    echo "$subs"
    echo ""

    local current_sub=$(az account show --query "id" -o tsv 2>/dev/null)
    local current_name=$(az account show --query "name" -o tsv 2>/dev/null)

    print_info "Current subscription: $current_name"

    read -p "Use this subscription? (Y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        read -p "Enter subscription ID to use: " sub_id
        az account set --subscription "$sub_id"
        print_status "Switched to subscription: $(az account show --query name -o tsv)"
    fi
}

# Register required Azure providers
register_providers() {
    print_header "Registering Azure Resource Providers"

    local providers=(
        "Microsoft.App"                      # Container Apps
        "Microsoft.ContainerRegistry"        # Container Registry
        "Microsoft.DBforPostgreSQL"          # PostgreSQL Flexible Server
        "Microsoft.Cache"                    # Redis Cache
        "Microsoft.Storage"                  # Blob Storage
        "Microsoft.KeyVault"                 # Key Vault
        "Microsoft.OperationalInsights"      # Log Analytics (for Container Apps)
        "Microsoft.ManagedIdentity"          # Managed Identity
    )

    for provider in "${providers[@]}"; do
        local state=$(az provider show --namespace "$provider" --query "registrationState" -o tsv 2>/dev/null || echo "NotRegistered")

        if [ "$state" == "Registered" ]; then
            print_status "$provider - Already registered"
        else
            print_step "Registering $provider..."
            az provider register --namespace "$provider" --wait
            print_status "$provider - Registered"
        fi
    done

    print_status "All required providers registered"
}

# Create parameters file
setup_parameters() {
    print_header "Setting Up Parameters File"

    local params_example="$PROJECT_ROOT/infra/parameters.example.json"
    local params_file="$PROJECT_ROOT/infra/parameters.json"

    if [ -f "$params_file" ]; then
        print_status "Parameters file already exists: infra/parameters.json"
        print_info "Edit this file to configure your deployment."
    elif [ -f "$params_example" ]; then
        cp "$params_example" "$params_file"
        print_status "Created parameters file from example"
        print_warning "Please edit infra/parameters.json with your API keys"
    else
        print_warning "Parameters example file not found"
        print_info "Run deploy-azure.sh to generate it"
    fi
}

# Print summary and next steps
print_summary() {
    print_header "Setup Complete!"

    echo ""
    echo -e "${GREEN}Your Azure environment is ready for deployment!${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo -e "  ${CYAN}1.${NC} Edit infra/parameters.json with your settings:"
    echo "     - Generate JWT secret: openssl rand -base64 32"
    echo "     - Add your OpenAI API key (optional)"
    echo "     - Add your Qwen API key (optional)"
    echo ""
    echo -e "  ${CYAN}2.${NC} Deploy to Azure:"
    echo "     ./scripts/deploy-azure.sh prod"
    echo ""
    echo -e "  ${CYAN}3.${NC} After deployment, access your API at:"
    echo "     https://ilmred-prod-api.<region>.azurecontainerapps.io"
    echo ""
    echo -e "${YELLOW}Estimated monthly cost: ~\$35 (idle) to ~\$67 (1K users)${NC}"
    echo ""
}

# Main function
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         ILM Red API - Azure Setup Script                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    check_azure_cli
    check_docker
    azure_login
    select_subscription
    register_providers
    setup_parameters
    print_summary
}

main "$@"
