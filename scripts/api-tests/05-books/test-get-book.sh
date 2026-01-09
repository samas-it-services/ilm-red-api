#!/usr/bin/env bash
# test-get-book.sh - Test getting book details
#
# Retrieves detailed information about a specific book.
#
# Usage: ./test-get-book.sh [book_id]
#
# If no book_id provided, uses the last uploaded book.

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Get Book Details Test"

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-get-book.sh [book_id]"
        print_info "Run test-upload-book.sh first to upload a test book."
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
fi

print_step "Testing: GET /v1/books/$BOOK_ID"
print_info "URL: ${API_URL}/books/$BOOK_ID"
echo ""

# Make the request (optional auth)
api_request GET "/books/$BOOK_ID"

# Display results
if is_success; then
    print_success "Book details retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Show key details
    echo ""
    print_subheader "Book Details"
    print_info "ID: $(echo "$RESPONSE" | jq -r '.id')"
    print_info "Title: $(echo "$RESPONSE" | jq -r '.title')"
    print_info "Author: $(echo "$RESPONSE" | jq -r '.author // "Not specified"')"
    print_info "Category: $(echo "$RESPONSE" | jq -r '.category')"
    print_info "Visibility: $(echo "$RESPONSE" | jq -r '.visibility')"
    print_info "Status: $(echo "$RESPONSE" | jq -r '.status')"
    print_info "File Type: $(echo "$RESPONSE" | jq -r '.file_type')"

    FILE_SIZE=$(echo "$RESPONSE" | jq -r '.file_size')
    print_info "File Size: $(format_size $FILE_SIZE)"
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "Book not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "403" ]]; then
    print_error "Access denied - book is private (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to get book (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Get book details test completed"
