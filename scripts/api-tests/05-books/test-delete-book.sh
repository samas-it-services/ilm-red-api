#!/usr/bin/env bash
# test-delete-book.sh - Test book deletion
#
# Soft deletes a book. Only the book owner can delete.
#
# Usage: ./test-delete-book.sh [book_id]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Delete Book Test"

# Check authentication
require_auth

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-delete-book.sh [book_id]"
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
fi

print_step "Testing: DELETE /v1/books/$BOOK_ID"
print_info "URL: ${API_URL}/books/$BOOK_ID"
print_warning "This will soft delete the book!"
echo ""

# Make the request
api_request DELETE "/books/$BOOK_ID"

# Display results
if [[ "$HTTP_STATUS" == "204" ]]; then
    print_success "Book deleted successfully (HTTP $HTTP_STATUS)"

    # Remove saved book info
    rm -f "$TEST_BOOK_FILE"
elif is_success; then
    print_success "Book deleted (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    rm -f "$TEST_BOOK_FILE"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "403" ]]; then
    print_error "Permission denied - not the book owner (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "Book not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to delete book (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Delete book test completed"
