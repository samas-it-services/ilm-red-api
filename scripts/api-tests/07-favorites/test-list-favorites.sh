#!/usr/bin/env bash
# test-list-favorites.sh - Test listing favorite books
#
# Lists the authenticated user's favorite books.
#
# Usage: ./test-list-favorites.sh

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "List Favorite Books Test"

# Check authentication
require_auth

print_step "Testing: GET /v1/books/me/favorites"
print_info "URL: ${API_URL}/books/me/favorites"
echo ""

# Make the request
api_request GET "/books/me/favorites"

# Display results
if is_success; then
    print_success "Favorites retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Show summary
    echo ""
    print_subheader "Summary"
    TOTAL=$(echo "$RESPONSE" | jq -r '.pagination.total // 0')
    BOOK_COUNT=$(echo "$RESPONSE" | jq '.data | length')

    print_info "Total favorites: $TOTAL"
    print_info "Books on this page: $BOOK_COUNT"

    # List favorite books
    if [[ "$BOOK_COUNT" -gt 0 ]]; then
        echo ""
        print_subheader "Favorite Books"
        echo "$RESPONSE" | jq -r '.data[] | "  - \(.title) by \(.author // "Unknown")"'
    fi
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
else
    print_error "Failed to list favorites (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "List favorites test completed"
