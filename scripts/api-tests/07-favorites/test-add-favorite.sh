#!/usr/bin/env bash
# test-add-favorite.sh - Test adding a book to favorites
#
# Adds a book to the user's favorites list.
#
# Usage: ./test-add-favorite.sh [book_id]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Add Book to Favorites Test"

# Check authentication
require_auth

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-add-favorite.sh [book_id]"
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
fi

print_step "Testing: POST /v1/books/$BOOK_ID/favorite"
print_info "URL: ${API_URL}/books/$BOOK_ID/favorite"
echo ""

# Make the request
api_request POST "/books/$BOOK_ID/favorite"

# Display results
if [[ "$HTTP_STATUS" == "201" ]]; then
    print_success "Book added to favorites (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"
elif is_success; then
    print_success "Book added to favorites (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "Book not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "409" ]]; then
    print_warning "Book already in favorites (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
else
    print_error "Failed to add favorite (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Add favorite test completed"
