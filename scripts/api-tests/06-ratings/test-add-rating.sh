#!/usr/bin/env bash
# test-add-rating.sh - Test adding a book rating
#
# Adds or updates a rating for a book.
# Cannot rate your own books.
#
# Usage: ./test-add-rating.sh [book_id] [rating] [review]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Add Book Rating Test"

# Check authentication
require_auth

# Get parameters
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
    RATING="${2:-5}"
    REVIEW="${3:-Great book! Highly recommended.}"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-add-rating.sh [book_id] [rating] [review]"
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
    RATING="5"
    REVIEW="Great book! Reviewed via API test at $(date)."
fi

print_step "Testing: POST /v1/books/$BOOK_ID/ratings"
print_info "URL: ${API_URL}/books/$BOOK_ID/ratings"
echo ""

print_subheader "Request Body"
REQUEST_BODY=$(cat <<EOF
{
    "rating": $RATING,
    "review": "$REVIEW"
}
EOF
)
print_json "$REQUEST_BODY"
echo ""

# Make the request
api_request POST "/books/$BOOK_ID/ratings" "$REQUEST_BODY"

# Display results
if [[ "$HTTP_STATUS" == "201" ]]; then
    print_success "Rating added successfully (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    echo ""
    print_info "Rating: $(echo "$RESPONSE" | jq -r '.rating') stars"
elif is_success; then
    print_success "Rating updated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "400" ]]; then
    print_warning "Cannot rate - you may own this book (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "You cannot rate your own books"
    exit 1
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "Book not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to add rating (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Add rating test completed"
