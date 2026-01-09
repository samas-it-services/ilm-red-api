#!/usr/bin/env bash
# test-logout.sh - Test user logout
#
# Logs out by revoking the refresh token.
# After logout, the refresh token can no longer be used.
#
# Usage: ./test-logout.sh [refresh_token]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "User Logout Test"

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

print_step "Testing: POST /v1/auth/logout"
print_info "URL: ${API_URL}/auth/logout"
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
api_request_no_auth POST "/auth/logout" "$REQUEST_BODY"

# Display results
if [[ "$HTTP_STATUS" == "204" ]]; then
    print_success "Logout successful (HTTP $HTTP_STATUS)"

    # Clear saved tokens
    clear_tokens
    print_info "Local tokens cleared"
elif is_success; then
    print_success "Logout successful (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"

    # Clear saved tokens
    clear_tokens
    print_info "Local tokens cleared"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_warning "Logout - token already invalid (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"

    # Clear saved tokens anyway
    clear_tokens
else
    print_error "Logout failed (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Logout test completed"
print_info "Run test-login.sh to login again"
