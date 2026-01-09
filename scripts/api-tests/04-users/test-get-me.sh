#!/usr/bin/env bash
# test-get-me.sh - Test getting current user profile
#
# Retrieves the authenticated user's full profile.
#
# Usage: ./test-get-me.sh

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Get Current User Profile Test"

# Check authentication
require_auth

print_step "Testing: GET /v1/users/me"
print_info "URL: ${API_URL}/users/me"
echo ""

# Make the request
api_request GET "/users/me"

# Display results
if is_success; then
    print_success "Profile retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Display key info
    echo ""
    print_subheader "User Info"
    USER_ID=$(echo "$RESPONSE" | jq -r '.id')
    USERNAME=$(echo "$RESPONSE" | jq -r '.username')
    EMAIL=$(echo "$RESPONSE" | jq -r '.email')
    DISPLAY_NAME=$(echo "$RESPONSE" | jq -r '.display_name')
    ROLES=$(echo "$RESPONSE" | jq -r '.roles | join(", ")')

    print_info "ID: $USER_ID"
    print_info "Username: $USERNAME"
    print_info "Email: $EMAIL"
    print_info "Display Name: $DISPLAY_NAME"
    print_info "Roles: $ROLES"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
else
    print_error "Failed to get profile (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Get current user test completed"
