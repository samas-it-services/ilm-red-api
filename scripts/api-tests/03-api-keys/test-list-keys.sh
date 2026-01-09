#!/usr/bin/env bash
# test-list-keys.sh - Test listing API keys
#
# Lists all API keys for the authenticated user.
# Only shows key prefixes, not full keys.
#
# Usage: ./test-list-keys.sh

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "List API Keys Test"

# Check authentication
require_auth

print_step "Testing: GET /v1/auth/api-keys"
print_info "URL: ${API_URL}/auth/api-keys"
echo ""

# Make the request
api_request GET "/auth/api-keys"

# Display results
if is_success; then
    print_success "API keys retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Count keys
    KEY_COUNT=$(echo "$RESPONSE" | jq 'length')
    echo ""
    print_info "Total API keys: $KEY_COUNT"

    # List key names
    if [[ "$KEY_COUNT" -gt 0 ]]; then
        echo ""
        print_subheader "Keys Summary"
        echo "$RESPONSE" | jq -r '.[] | "  - \(.name) (\(.key_prefix))"'
    fi
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
else
    print_error "Failed to list API keys (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "List API keys test completed"
