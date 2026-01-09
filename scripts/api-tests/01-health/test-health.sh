#!/usr/bin/env bash
# test-health.sh - Test the health check endpoint
#
# Tests the API health endpoint which returns status of the API
# and its dependencies (database, etc.)
#
# Usage: ./test-health.sh

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Health Check Test"

print_step "Testing: GET /v1/health"
print_info "URL: ${API_URL}/health"
echo ""

# Make the request
api_request_no_auth GET "/health"

# Display results
if is_success; then
    print_success "Health check passed (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Parse and display key info
    echo ""
    print_subheader "Details"
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    VERSION=$(echo "$RESPONSE" | jq -r '.version')
    ENVIRONMENT=$(echo "$RESPONSE" | jq -r '.environment')
    DB_STATUS=$(echo "$RESPONSE" | jq -r '.checks.database // "unknown"')

    print_info "Status: $STATUS"
    print_info "Version: $VERSION"
    print_info "Environment: $ENVIRONMENT"
    print_info "Database: $DB_STATUS"
else
    print_error "Health check failed (HTTP $HTTP_STATUS)"
    echo ""
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Health check test completed successfully"
