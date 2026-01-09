#!/usr/bin/env bash
# config.sh - Shared configuration for API test scripts
#
# This file contains common variables, functions, and helpers
# used by all API test scripts.
#
# Usage: source this file at the beginning of each test script
#   source "$(dirname "$0")/../config.sh"

set -e

# ============================================================================
# AZURE DEPLOYMENT CONFIGURATION
# ============================================================================

# API Base URL - Change this for different environments
export API_BASE_URL="${API_BASE_URL:-https://ilmred-prod-api.braverock-f357973c.westus2.azurecontainerapps.io}"
export API_VERSION="v1"

# Full API URL
export API_URL="${API_BASE_URL}/${API_VERSION}"

# Azure Resource Details (for reference)
export AZURE_REGION="westus2"
export AZURE_RESOURCE_GROUP="ilmred-prod-rg"
export AZURE_POSTGRES_HOST="ilmred-prod-postgres.postgres.database.azure.com"
export AZURE_REDIS_HOST="ilmred-prod-redis.redis.cache.windows.net"
export AZURE_ACR="ilmredprodacr.azurecr.io"
export AZURE_STORAGE="ilmredprodstorage"
export AZURE_KEYVAULT="ilmred-prod-kv-3gfbth"

# ============================================================================
# TOKEN STORAGE
# ============================================================================

# Directory for storing tokens and test data
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export TEST_DATA_DIR="${SCRIPT_DIR}/.test-data"
export TOKEN_FILE="${TEST_DATA_DIR}/tokens.json"
export TEST_USER_FILE="${TEST_DATA_DIR}/test-user.json"
export TEST_BOOK_FILE="${TEST_DATA_DIR}/test-book.json"

# Create test data directory if it doesn't exist
mkdir -p "$TEST_DATA_DIR"

# ============================================================================
# COLORS AND FORMATTING
# ============================================================================

export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export NC='\033[0m' # No Color
export BOLD='\033[1m'

# ============================================================================
# OUTPUT FUNCTIONS
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_subheader() {
    echo ""
    echo -e "${CYAN}── $1 ──${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

print_step() {
    echo -e "${BLUE}→${NC} $1"
}

print_json() {
    if command -v jq &> /dev/null; then
        echo "$1" | jq '.'
    else
        echo "$1"
    fi
}

# ============================================================================
# HTTP RESPONSE HANDLING
# ============================================================================

# Make an API request and capture both response and status code
# Usage: api_request METHOD ENDPOINT [DATA] [EXTRA_ARGS...]
# Returns: Sets $RESPONSE and $HTTP_STATUS
api_request() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="${API_URL}${endpoint}"
    local curl_args=(-s -w "___HTTP_STATUS___%{http_code}" -X "$method")

    # Add content type for POST/PUT/PATCH
    if [[ "$method" =~ ^(POST|PUT|PATCH)$ ]] && [[ -n "$data" ]]; then
        curl_args+=(-H "Content-Type: application/json" -d "$data")
    fi

    # Add authorization header if token exists
    local token
    token=$(get_access_token 2>/dev/null || true)
    if [[ -n "$token" ]]; then
        curl_args+=(-H "Authorization: Bearer $token")
    fi

    # Make the request
    local output
    output=$(curl "${curl_args[@]}" "$url")

    # Split response and status code using unique separator
    HTTP_STATUS="${output##*___HTTP_STATUS___}"
    RESPONSE="${output%___HTTP_STATUS___*}"

    export HTTP_STATUS RESPONSE
}

# Make an API request without authentication
api_request_no_auth() {
    local method="$1"
    local endpoint="$2"
    local data="${3:-}"

    local url="${API_URL}${endpoint}"
    local curl_args=(-s -w "___HTTP_STATUS___%{http_code}" -X "$method")

    # Add content type for POST/PUT/PATCH
    if [[ "$method" =~ ^(POST|PUT|PATCH)$ ]] && [[ -n "$data" ]]; then
        curl_args+=(-H "Content-Type: application/json" -d "$data")
    fi

    # Make the request
    local output
    output=$(curl "${curl_args[@]}" "$url")

    # Split response and status code using unique separator
    HTTP_STATUS="${output##*___HTTP_STATUS___}"
    RESPONSE="${output%___HTTP_STATUS___*}"

    export HTTP_STATUS RESPONSE
}

# Make an API request with API key authentication
api_request_with_key() {
    local api_key="$1"
    local method="$2"
    local endpoint="$3"
    local data="${4:-}"

    local url="${API_URL}${endpoint}"
    local curl_args=(-s -w "___HTTP_STATUS___%{http_code}" -X "$method" -H "X-API-Key: $api_key")

    # Add content type for POST/PUT/PATCH
    if [[ "$method" =~ ^(POST|PUT|PATCH)$ ]] && [[ -n "$data" ]]; then
        curl_args+=(-H "Content-Type: application/json" -d "$data")
    fi

    # Make the request
    local output
    output=$(curl "${curl_args[@]}" "$url")

    # Split response and status code using unique separator
    HTTP_STATUS="${output##*___HTTP_STATUS___}"
    RESPONSE="${output%___HTTP_STATUS___*}"

    export HTTP_STATUS RESPONSE
}

# Check if HTTP status indicates success
is_success() {
    [[ "$HTTP_STATUS" =~ ^2[0-9][0-9]$ ]]
}

# ============================================================================
# TOKEN MANAGEMENT
# ============================================================================

# Save tokens to file
save_tokens() {
    local access_token="$1"
    local refresh_token="$2"
    local expires_in="${3:-900}"

    cat > "$TOKEN_FILE" << EOF
{
    "access_token": "$access_token",
    "refresh_token": "$refresh_token",
    "expires_in": $expires_in,
    "saved_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
}

# Get access token from file
get_access_token() {
    if [[ -f "$TOKEN_FILE" ]]; then
        jq -r '.access_token // empty' "$TOKEN_FILE"
    fi
}

# Get refresh token from file
get_refresh_token() {
    if [[ -f "$TOKEN_FILE" ]]; then
        jq -r '.refresh_token // empty' "$TOKEN_FILE"
    fi
}

# Clear saved tokens
clear_tokens() {
    rm -f "$TOKEN_FILE"
}

# ============================================================================
# TEST USER MANAGEMENT
# ============================================================================

# Generate a unique test user
generate_test_user() {
    local timestamp=$(date +%s)
    local random=$(( RANDOM % 10000 ))

    cat << EOF
{
    "email": "test-${timestamp}-${random}@ilm-red-test.com",
    "password": "TestPassword123!",
    "username": "testuser_${timestamp}_${random}",
    "display_name": "Test User ${timestamp}"
}
EOF
}

# Save test user info
save_test_user() {
    local user_json="$1"
    echo "$user_json" > "$TEST_USER_FILE"
}

# Get test user info
get_test_user() {
    if [[ -f "$TEST_USER_FILE" ]]; then
        cat "$TEST_USER_FILE"
    fi
}

# ============================================================================
# TEST BOOK MANAGEMENT
# ============================================================================

# Save test book info
save_test_book() {
    local book_json="$1"
    echo "$book_json" > "$TEST_BOOK_FILE"
}

# Get test book info
get_test_book() {
    if [[ -f "$TEST_BOOK_FILE" ]]; then
        cat "$TEST_BOOK_FILE"
    fi
}

# Get test book ID
get_test_book_id() {
    if [[ -f "$TEST_BOOK_FILE" ]]; then
        jq -r '.id // empty' "$TEST_BOOK_FILE"
    fi
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

# Check if jq is installed
require_jq() {
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed."
        print_info "Install with: brew install jq (macOS) or apt install jq (Linux)"
        exit 1
    fi
}

# Check if curl is installed
require_curl() {
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed."
        exit 1
    fi
}

# Ensure user is logged in
require_auth() {
    local token
    token=$(get_access_token)
    if [[ -z "$token" ]]; then
        print_error "Not logged in. Run test-login.sh first."
        exit 1
    fi
}

# Format file size
format_size() {
    local size=$1
    if [[ $size -ge 1073741824 ]]; then
        echo "$(( size / 1073741824 )) GB"
    elif [[ $size -ge 1048576 ]]; then
        echo "$(( size / 1048576 )) MB"
    elif [[ $size -ge 1024 ]]; then
        echo "$(( size / 1024 )) KB"
    else
        echo "$size bytes"
    fi
}

# ============================================================================
# INITIALIZATION
# ============================================================================

# Verify dependencies
require_curl
require_jq

# Print configuration info (when sourced with DEBUG=1)
if [[ "${DEBUG:-0}" == "1" ]]; then
    print_info "API URL: $API_URL"
    print_info "Test Data Dir: $TEST_DATA_DIR"
fi
