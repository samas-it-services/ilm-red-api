#!/usr/bin/env bash
# test-login.sh - Test user login
#
# Logs in with test user credentials and saves tokens for subsequent tests.
#
# Usage: ./test-login.sh [email] [password]
#
# If no arguments provided, uses credentials from previous registration.

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "User Login Test"

# Get credentials
if [[ $# -ge 2 ]]; then
    EMAIL="$1"
    PASSWORD="$2"
elif [[ -f "$TEST_USER_FILE" ]]; then
    EMAIL=$(jq -r '.email' "$TEST_USER_FILE")
    PASSWORD=$(jq -r '.password' "$TEST_USER_FILE")
    print_info "Using saved test user: $EMAIL"
else
    print_error "No credentials provided and no saved test user found."
    print_info "Usage: ./test-login.sh [email] [password]"
    print_info "Or run test-register.sh first to create a test user."
    exit 1
fi

print_step "Testing: POST /v1/auth/login"
print_info "URL: ${API_URL}/auth/login"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "email": "$EMAIL",
    "password": "$PASSWORD"
}
EOF
)
# Don't print password in output
echo '{"email": "'$EMAIL'", "password": "***"}'
echo ""

# Make the request
api_request_no_auth POST "/auth/login" "$REQUEST_BODY"

# Display results
if is_success; then
    print_success "Login successful (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"

    # Hide the actual tokens in output, show structure
    echo "$RESPONSE" | jq '{
        access_token: (.access_token | .[0:20] + "..."),
        refresh_token: (.refresh_token | .[0:20] + "..."),
        token_type: .token_type,
        expires_in: .expires_in
    }'

    # Save tokens
    ACCESS_TOKEN=$(echo "$RESPONSE" | jq -r '.access_token')
    REFRESH_TOKEN=$(echo "$RESPONSE" | jq -r '.refresh_token')
    EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')

    save_tokens "$ACCESS_TOKEN" "$REFRESH_TOKEN" "$EXPIRES_IN"

    echo ""
    print_success "Tokens saved to: $TOKEN_FILE"
    print_info "Access token expires in: $EXPIRES_IN seconds"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Login failed - invalid credentials (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Login failed (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Login test completed"
