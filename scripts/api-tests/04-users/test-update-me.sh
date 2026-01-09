#!/usr/bin/env bash
# test-update-me.sh - Test updating current user profile
#
# Updates the authenticated user's profile.
#
# Usage: ./test-update-me.sh [display_name] [bio]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Update Current User Profile Test"

# Check authentication
require_auth

# Set values
DISPLAY_NAME="${1:-Updated Display Name}"
BIO="${2:-This is my updated bio from API test.}"

print_step "Testing: PATCH /v1/users/me"
print_info "URL: ${API_URL}/users/me"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "display_name": "$DISPLAY_NAME",
    "bio": "$BIO"
}
EOF
)
print_json "$REQUEST_BODY"
echo ""

# Make the request
api_request PATCH "/users/me" "$REQUEST_BODY"

# Display results
if is_success; then
    print_success "Profile updated (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Show updated fields
    echo ""
    print_subheader "Updated Fields"
    print_info "Display Name: $(echo "$RESPONSE" | jq -r '.display_name')"
    print_info "Bio: $(echo "$RESPONSE" | jq -r '.bio')"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "400" ]]; then
    print_error "Validation error (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to update profile (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Update current user test completed"
