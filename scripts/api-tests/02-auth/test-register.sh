#!/usr/bin/env bash
# test-register.sh - Test user registration
#
# Registers a new test user account. Generates a unique email
# and username to avoid conflicts.
#
# Usage: ./test-register.sh [email] [password] [username] [display_name]
#
# If no arguments provided, generates random test credentials.

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "User Registration Test"

# Generate or use provided credentials
if [[ $# -ge 4 ]]; then
    EMAIL="$1"
    PASSWORD="$2"
    USERNAME="$3"
    DISPLAY_NAME="$4"
else
    # Generate unique test user
    TIMESTAMP=$(date +%s)
    RANDOM_NUM=$(( RANDOM % 10000 ))
    EMAIL="test-${TIMESTAMP}-${RANDOM_NUM}@ilm-red-test.com"
    PASSWORD="TestPassword123!"
    USERNAME="testuser_${TIMESTAMP}_${RANDOM_NUM}"
    DISPLAY_NAME="Test User ${TIMESTAMP}"
fi

print_step "Testing: POST /v1/auth/register"
print_info "URL: ${API_URL}/auth/register"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "email": "$EMAIL",
    "password": "$PASSWORD",
    "username": "$USERNAME",
    "display_name": "$DISPLAY_NAME"
}
EOF
)
print_json "$REQUEST_BODY"
echo ""

# Make the request
api_request_no_auth POST "/auth/register" "$REQUEST_BODY"

# Display results
if [[ "$HTTP_STATUS" == "201" ]]; then
    print_success "Registration successful (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Save test user info for later use
    save_test_user "$(cat <<EOF
{
    "email": "$EMAIL",
    "password": "$PASSWORD",
    "username": "$USERNAME",
    "display_name": "$DISPLAY_NAME"
}
EOF
)"

    # Save tokens
    ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
    REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token')
    EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')

    if [[ -n "$ACCESS_TOKEN" && "$ACCESS_TOKEN" != "null" ]]; then
        save_tokens "$ACCESS_TOKEN" "$REFRESH_TOKEN" "$EXPIRES_IN"
        print_success "Tokens saved for subsequent tests"
    fi

    echo ""
    print_info "Test user credentials saved to: $TEST_USER_FILE"
    print_info "Email: $EMAIL"
    print_info "Password: $PASSWORD"
elif [[ "$HTTP_STATUS" == "400" ]]; then
    print_warning "Registration failed - validation error (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "409" ]]; then
    print_warning "Registration failed - user already exists (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Try running test-login.sh instead"
    exit 1
else
    print_error "Registration failed (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Registration test completed"
