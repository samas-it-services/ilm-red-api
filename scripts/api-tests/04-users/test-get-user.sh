#!/usr/bin/env bash
# test-get-user.sh - Test getting a public user profile
#
# Retrieves a user's public profile by ID.
# Does not require authentication.
#
# Usage: ./test-get-user.sh [user_id]
#
# If no user_id provided, gets the current user's public profile.

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Get Public User Profile Test"

# Get user ID
if [[ $# -ge 1 ]]; then
    USER_ID="$1"
else
    # Try to get current user's ID first
    TOKEN=$(get_access_token)
    if [[ -n "$TOKEN" ]]; then
        api_request GET "/users/me"
        if is_success; then
            USER_ID=$(echo "$RESPONSE" | jq -r '.id')
            print_info "Using current user ID: $USER_ID"
        fi
    fi

    if [[ -z "$USER_ID" ]]; then
        print_error "No user ID provided."
        print_info "Usage: ./test-get-user.sh [user_id]"
        exit 1
    fi
fi

print_step "Testing: GET /v1/users/$USER_ID"
print_info "URL: ${API_URL}/users/$USER_ID"
echo ""

# Make the request (no auth required for public profile)
api_request_no_auth GET "/users/$USER_ID"

# Display results
if is_success; then
    print_success "Public profile retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Display public info
    echo ""
    print_subheader "Public Info"
    print_info "Username: $(echo "$RESPONSE" | jq -r '.username')"
    print_info "Display Name: $(echo "$RESPONSE" | jq -r '.display_name')"
    print_info "Bio: $(echo "$RESPONSE" | jq -r '.bio // "Not set"')"
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "User not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to get user profile (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Get public user profile test completed"
