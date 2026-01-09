#!/usr/bin/env bash
# test-upload-book.sh - Test book upload
#
# Uploads a book file to the API.
# Creates a sample PDF if no file is provided.
#
# Usage: ./test-upload-book.sh [file_path] [title]

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../config.sh"

print_header "Book Upload Test"

# Check authentication
require_auth

# Get file and title
FILE_PATH="${1:-}"
TITLE="${2:-Test Book $(date +%s)}"

# Create a sample text file if no file provided
if [[ -z "$FILE_PATH" ]]; then
    print_info "No file provided, creating sample text file..."
    FILE_PATH="$TEST_DATA_DIR/sample-book.txt"
    cat > "$FILE_PATH" << 'EOF'
Sample Book Content

Chapter 1: Introduction
This is a sample book created for testing the ILM Red API.
It demonstrates the book upload functionality.

Chapter 2: Content
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

Chapter 3: Conclusion
Thank you for testing the ILM Red API!
EOF
    print_info "Sample file created: $FILE_PATH"
fi

# Verify file exists
if [[ ! -f "$FILE_PATH" ]]; then
    print_error "File not found: $FILE_PATH"
    exit 1
fi

FILE_SIZE=$(wc -c < "$FILE_PATH" | tr -d ' ')
FILE_NAME=$(basename "$FILE_PATH")

print_step "Testing: POST /v1/books"
print_info "URL: ${API_URL}/books"
echo ""

print_subheader "Upload Details"
print_info "File: $FILE_PATH"
print_info "Size: $(format_size $FILE_SIZE)"
print_info "Title: $TITLE"
echo ""

# Get token
TOKEN=$(get_access_token)

# Make the multipart form request
print_step "Uploading..."
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "${API_URL}/books" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@$FILE_PATH" \
    -F "title=$TITLE" \
    -F "author=Test Author" \
    -F "description=A test book uploaded via API test script" \
    -F "category=other" \
    -F "visibility=private" \
    -F "language=en")

HTTP_STATUS=$(echo "$RESPONSE" | tail -n1)
RESPONSE=$(echo "$RESPONSE" | sed '$d')

# Display results
if [[ "$HTTP_STATUS" == "201" ]]; then
    print_success "Book uploaded successfully (HTTP $HTTP_STATUS)"
    echo ""
    print_subheader "Response"
    print_json "$RESPONSE"

    # Extract book info
    BOOK_ID=$(echo "$RESPONSE" | jq -r '.id')
    BOOK_STATUS=$(echo "$RESPONSE" | jq -r '.status')

    # Save for other tests
    save_test_book "$RESPONSE"

    echo ""
    print_info "Book ID: $BOOK_ID"
    print_info "Status: $BOOK_STATUS"
    print_info "Book info saved for subsequent tests"
elif [[ "$HTTP_STATUS" == "401" ]]; then
    print_error "Not authenticated (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    print_info "Run test-login.sh first"
    exit 1
elif [[ "$HTTP_STATUS" == "400" ]]; then
    print_error "Validation error (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
elif [[ "$HTTP_STATUS" == "413" ]]; then
    print_error "File too large (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
else
    print_error "Failed to upload book (HTTP $HTTP_STATUS)"
    print_json "$RESPONSE"
    exit 1
fi

echo ""
print_success "Book upload test completed"
