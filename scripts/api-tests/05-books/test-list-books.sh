#!/usr/bin/env bash
# test-list-books.sh - Test listing books
#
# Lists books with optional filtering and pagination.
#
# Usage: ./test-list-books.sh [options]
# Options:
#   -q QUERY        Search query
#   -c CATEGORY     Filter by category
#   -v VISIBILITY   Filter by visibility (public, private, friends)
#   -p PAGE         Page number
#   -s PAGE_SIZE    Items per page

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "List Books Test"

# Parse options
QUERY=""
CATEGORY=""
VISIBILITY=""
PAGE="1"
PAGE_SIZE="10"

while getopts "q:c:v:p:s:" opt; do
    case $opt in
        q) QUERY="$OPTARG" ;;
        c) CATEGORY="$OPTARG" ;;
        v) VISIBILITY="$OPTARG" ;;
        p) PAGE="$OPTARG" ;;
        s) PAGE_SIZE="$OPTARG" ;;
    esac
done

# Build query string
QUERY_PARAMS="page=$PAGE&page_size=$PAGE_SIZE"
[[ -n "$QUERY" ]] && QUERY_PARAMS="$QUERY_PARAMS&q=$QUERY"
[[ -n "$CATEGORY" ]] && QUERY_PARAMS="$QUERY_PARAMS&category=$CATEGORY"
[[ -n "$VISIBILITY" ]] && QUERY_PARAMS="$QUERY_PARAMS&visibility=$VISIBILITY"

print_step "Testing: GET /v1/books?$QUERY_PARAMS"
print_info "URL: ${API_URL}/books?$QUERY_PARAMS"
echo ""

# Make the request (optional auth - shows more books if authenticated)
api_request GET "/books?$QUERY_PARAMS"

# Display results
if is_success; then
    print_success "Books retrieved (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Show summary
    echo ""
    print_subheader "Summary"
    TOTAL=$(echo "$RESPONSE" | jq -r '.pagination.total // 0')
    TOTAL_PAGES=$(echo "$RESPONSE" | jq -r '.pagination.total_pages // 0')
    CURRENT_PAGE=$(echo "$RESPONSE" | jq -r '.pagination.page // 1')
    BOOK_COUNT=$(echo "$RESPONSE" | jq '.data | length')

    print_info "Total books: $TOTAL"
    print_info "Page $CURRENT_PAGE of $TOTAL_PAGES"
    print_info "Books on this page: $BOOK_COUNT"

    # List book titles
    if [[ "$BOOK_COUNT" -gt 0 ]]; then
        echo ""
        print_subheader "Books"
        echo "$RESPONSE" | jq -r '.data[] | "  - \(.title) [\(.status)] by \(.author // "Unknown")"'
    fi
else
    print_error "Failed to list books (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "List books test completed"
