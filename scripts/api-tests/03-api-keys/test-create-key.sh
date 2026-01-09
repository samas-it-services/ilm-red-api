#!/usr/bin/env bash
# test-create-key.sh - Test API key creation
#
# Creates a new API key for the authenticated user.
# The full API key is only shown once during creation.
#
# Usage: ./test-create-key.sh [name] [permissions] [expires_in_days]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Create API Key Test"

# Check authentication
require_auth

# Set defaults
KEY_NAME="${1:-My Test API Key}"
PERMISSIONS="${2:-[\"read\", \"write\"]}"
EXPIRES_IN_DAYS="${3:-90}"

print_step "Testing: POST /v1/auth/api-keys"
print_info "URL: ${API_URL}/auth/api-keys"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "name": "$KEY_NAME",
    "permissions": $PERMISSIONS,
    "expires_in_days": $EXPIRES_IN_DAYS
}
EOF
)
print_json "$REQUEST_BODY"
echo ""

# Make the request
api_request POST "/auth/api-keys" "$REQUEST_BODY"

# Display results
if [[ "$HTTP_STATUS" == "201" ]]; then
    print_success "API key created successfully (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Extract and display the key
    API_KEY=$(echo "$RESPONSE" | jq -r '.api_key // empty')
    KEY_ID=$(echo "$RESPONSE" | jq -r '.key_info.id // empty')
    KEY_PREFIX=$(echo "$RESPONSE" | jq -r '.key_info.key_prefix // empty')

    echo ""
    print_warning "IMPORTANT: Save this API key now - it won't be shown again!"
    echo -e "${BOLD}API Key:${NC} $API_KEY"
    echo ""
    print_info "Key ID: $KEY_ID"
    print_info "Key Prefix: $KEY_PREFIX"

    # Save key info for other tests
    echo "{\"id\": \"$KEY_ID\", \"api_key\": \"$API_KEY\"}" > "$TEST_DATA_DIR/api-key.json"
    print_info "Key info saved to: $TEST_DATA_DIR/api-key.json"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
else
    print_error "Failed to create API key (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "API key creation test completed"
