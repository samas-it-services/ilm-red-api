#!/usr/bin/env bash
# test-list-ratings.sh - Test listing book ratings
#
# Lists all ratings for a book with pagination.
# Does not require authentication.
#
# Usage: ./test-list-ratings.sh [book_id]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "List Book Ratings Test"

# Get book ID
if [[ $# -ge 1 ]]; then
    BOOK_ID="$1"
else
    BOOK_ID=$(get_test_book_id)
    if [[ -z "$BOOK_ID" ]]; then
        print_error "No book ID provided and no saved book found."
        print_info "Usage: ./test-list-ratings.sh [book_id]"
        exit 1
    fi
    print_info "Using saved book ID: $BOOK_ID"
fi

print_step "Testing: GET /v1/books/$BOOK_ID/ratings"
print_info "URL: ${API_URL}/books/$BOOK_ID/ratings"
echo ""

# Make the request (no auth required)
api_request_no_auth GET "/books/$BOOK_ID/ratings"

# Display results
if is_success; then
    print_success "Ratings retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Show summary
    echo ""
    print_subheader "Summary"
    TOTAL=$(echo "$RESPONSE" | jq -r '.pagination.total // 0')
    RATING_COUNT=$(echo "$RESPONSE" | jq '.data | length')

    print_info "Total ratings: $TOTAL"
    print_info "Ratings on this page: $RATING_COUNT"

    # Calculate average if there are ratings
    if [[ "$RATING_COUNT" -gt 0 ]]; then
        AVG=$(echo "$RESPONSE" | jq '[.data[].rating] | add / length')
        echo ""
        print_subheader "Ratings"
        print_info "Average rating: $AVG stars"
        echo "$RESPONSE" | jq -r '.data[] | "  - \(.rating)★ by \(.user.display_name // .user.username)"'
    fi
elif [[ "$HTTP_STATUS" == "404" ]]; then
    print_error "Book not found (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to list ratings (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "List ratings test completed"
