#!/usr/bin/env bash
# test-refresh.sh - Test token refresh
#
# Refreshes the access token using the saved refresh token.
# Implements token rotation - old refresh token is invalidated.
#
# Usage: ./test-refresh.sh [refresh_token]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Token Refresh Test"

# Get refresh token
if [[ $# -ge 1 ]]; then
    REFRESH_TOKEN="$1"
else
    REFRESH_TOKEN=$(get_refresh_token)
    if [[ -z "$REFRESH_TOKEN" ]]; then
        print_error "No refresh token available."
        print_info "Run test-login.sh first to get tokens."
        exit 1
    fi
    print_info "Using saved refresh token"
fi

print_step "Testing: POST /v1/auth/refresh"
print_info "URL: ${API_URL}/auth/refresh"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "refresh_token": "$REFRESH_TOKEN"
}
EOF
)
# Show truncated token
echo '{"refresh_token": "'${REFRESH_TOKEN:0:20}'..."}'
echo ""

# Make the request
api_request_no_auth POST "/auth/refresh" "$REQUEST_BODY"

# Display results
if is_success; then
    print_success "Token refresh successful (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"

    # Hide the actual tokens in output
    echo "$RESPONSE" | jq '{
        access_token: (.access_token | .[0:20] + "..."),
        refresh_token: (.refresh_token | .[0:20] + "..."),
        token_type: .token_type,
        expires_in: .expires_in
    }'

    # Save new tokens
    NEW_ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
    NEW_REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token')
    EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')

    save_tokens "$NEW_ACCESS_TOKEN" "$NEW_REFRESH_TOKEN" "$EXPIRES_IN"

    echo ""
    print_success "New tokens saved"
    print_info "Access token expires in: $EXPIRES_IN seconds"
    print_warning "Old refresh token is now invalidated (token rotation)"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Token refresh failed - invalid/expired token (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "You may need to login again: ./test-login.sh"
    exit 1
else
    print_error "Token refresh failed (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Token refresh test completed"
