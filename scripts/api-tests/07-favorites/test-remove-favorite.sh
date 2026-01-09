#!/usr/bin/env bash
# test-remove-favorite.sh - Test removing a book from favorites
#
# Removes a book from the user's favorites list.
#
# Usage: ./test-remove-favorite.sh [book_id]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Remove Book from Favorites Test"

# Check authentication
require_auth

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-remove-favorite.sh [book_id]"
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
fi

print_step "Testing: DELETE /v1/books/$BOOK_ID/favorite"
print_info "URL: ${API_URL}/books/$BOOK_ID/favorite"
echo ""

# Make the request
api_request DELETE "/books/$BOOK_ID/favorite"

# Display results
if [[ "$HTTP_STATUS" == "204" ]]; then
    print_success "Book removed from favorites (HTTP $HTTP_STATUS)"
elif is_success; then
    print_success "Book removed from favorites (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_warning "Book not in favorites (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
else
    print_error "Failed to remove favorite (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Remove favorite test completed"
