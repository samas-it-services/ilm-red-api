#!/usr/bin/env bash
# test-delete-key.sh - Test API key deletion
#
# Deletes an API key by ID.
#
# Usage: ./test-delete-key.sh [key_id]
#
# If no key_id provided, uses the last created key.

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Delete API Key Test"

# Check authentication
require_auth

# Get key ID
if [[ $# -ge 1 ]]; then
    KEY_ID="$1"
elif [[ -f "$TEST_DATA_DIR/api-key.json" ]]; then
    KEY_ID=$(jq -r '.id' "$TEST_DATA_DIR/api-key.json")
    print_info "Using saved key ID: $KEY_ID"
else
    print_error "No key ID provided and no saved key found."
    print_info "Usage: ./test-delete-key.sh [key_id]"
    print_info "Run test-list-keys.sh to see available keys."
    exit 1
fi

print_step "Testing: DELETE /v1/auth/api-keys/$KEY_ID"
print_info "URL: ${API_URL}/auth/api-keys/$KEY_ID"
echo ""

# Make the request
api_request DELETE "/auth/api-keys/$KEY_ID"

# Display results
if [[ "$HTTP_STATUS" == "204" ]]; then
    print_success "API key deleted successfully (HTTP $HTTP_STATUS)"

    # Remove saved key info
    rm -f "$TEST_DATA_DIR/api-key.json"
elif is_success; then
    print_success "API key deleted (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    rm -f "$TEST_DATA_DIR/api-key.json"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "API key not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to delete API key (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Delete API key test completed"
