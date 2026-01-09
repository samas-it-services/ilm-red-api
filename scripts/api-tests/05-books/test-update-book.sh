#!/usr/bin/env bash
# test-update-book.sh - Test updating book metadata
#
# Updates book metadata. Only the book owner can update.
#
# Usage: ./test-update-book.sh [book_id] [title]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Update Book Test"

# Check authentication
require_auth

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
    NEW_TITLE="${2:-Updated Title $(date +%s)}"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-update-book.sh [book_id] [title]"
        print_info "Run test-upload-book.sh first to upload a test book."
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
    NEW_TITLE="Updated Title $(date +%s)"
fi

print_step "Testing: PATCH /v1/books/$BOOK_ID"
print_info "URL: ${API_URL}/books/$BOOK_ID"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "title": "$NEW_TITLE",
    "description": "Updated description from API test at $(date)",
    "category": "education"
}
EOF
)
print_json "$REQUEST_BODY"
echo ""

# Make the request
api_request PATCH "/books/$BOOK_ID" "$REQUEST_BODY"

# Display results
if is_success; then
    print_success "Book updated (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Update saved book info
    save_test_book "$RESPONSE"

    echo ""
    print_info "New Title: $(echo "$RESPONSE" | jq -r '.title')"
    print_info "New Category: $(echo "$RESPONSE" | jq -r '.category')"
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
    print_error "Failed to update book (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Update book test completed"
