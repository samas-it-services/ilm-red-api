#!/usr/bin/env bash
# test-download-book.sh - Test getting book download URL
#
# Retrieves a signed download URL for the book file.
# URL is valid for 1 hour.
#
# Usage: ./test-download-book.sh [book_id]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Get Book Download URL Test"

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-download-book.sh [book_id]"
        print_info "Run test-upload-book.sh first to upload a test book."
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
fi

print_step "Testing: GET /v1/books/$BOOK_ID/download"
print_info "URL: ${API_URL}/books/$BOOK_ID/download"
echo ""

# Make the request (optional auth)
api_request GET "/books/$BOOK_ID/download"

# Display results
if is_success; then
    print_success "Download URL retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Extract URL
    DOWNLOAD_URL=$(echo "$RESPONSE" | jq -r '.url')
    EXPIRES_IN=$(echo "$RESPONSE" | jq -r '.expires_in')

    echo ""
    print_info "Expires in: $EXPIRES_IN seconds"
    print_info "Download URL:"
    echo "$DOWNLOAD_URL"
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "Book not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "403" ]]; then
    print_error "Access denied (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "400" ]]; then
    print_warning "Book not ready for download (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Book may still be processing"
    exit 1
else
    print_error "Failed to get download URL (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Get download URL test completed"
