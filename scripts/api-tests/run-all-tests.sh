#!/usr/bin/env bash
# run-all-tests.sh - Master test runner for ILM Red API
#
# Runs all API tests in logical sequence, creating necessary
# test data along the way.
#
# Usage: ./run-all-tests.sh [options]
# Options:
#   --skip-cleanup    Don't delete test data at the end
#   --quick           Only run essential tests
#   --help            Show this help

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Options
SKIP_CLEANUP=false
QUICK_MODE=false

# Parse options
for arg in "$@"; do
    case "$arg" in
        --skip-cleanup) SKIP_CLEANUP=true ;;
        --quick) QUICK_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --skip-cleanup    Don't delete test data at the end"
            echo "  --quick           Only run essential tests"
            echo "  --help            Show this help"
            exit 0
            ;;
    esac
done

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Run a test script
run_test() {
    local test_name="$1"
    local test_script="$2"
    shift 2
    local args=("$@")

    TESTS_RUN=$((TESTS_RUN + 1))

    echo ""
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  TEST $TESTS_RUN: $test_name${NC}"
    echo -e "${MAGENTA}════════════════════════════════════════════════════════════${NC}"

    if [[ -x "$SCRIPT_DIR/$test_script" ]]; then
        if "$SCRIPT_DIR/$test_script" "${args[@]}"; then
            TESTS_PASSED=$((TESTS_PASSED + 1))
            echo -e "${GREEN}  ✓ PASSED${NC}"
        else
            TESTS_FAILED=$((TESTS_FAILED + 1))
            FAILED_TESTS+=("$test_name")
            echo -e "${RED}  ✗ FAILED${NC}"
        fi
    else
        print_error "Script not found or not executable: $test_script"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name (missing)")
    fi
}

# Print final summary
print_summary() {
    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}                     TEST SUMMARY                           ${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  Total Tests:  ${BOLD}$TESTS_RUN${NC}"
    echo -e "  Passed:       ${GREEN}$TESTS_PASSED${NC}"
    echo -e "  Failed:       ${RED}$TESTS_FAILED${NC}"
    echo ""

    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}Failed Tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test"
        done
        echo ""
    fi

    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All tests passed!${NC}"
    else
        echo -e "${RED}Some tests failed. Review the output above for details.${NC}"
    fi
}

# Cleanup function
cleanup() {
    if [[ "$SKIP_CLEANUP" == "true" ]]; then
        print_info "Skipping cleanup (--skip-cleanup flag)"
        return
    fi

    print_header "Cleanup"

    # Delete test book if exists
    BOOK_ID=$(get_test_book_id 2>/dev/null || true)
    if [[ -n "$BOOK_ID" ]]; then
        print_step "Deleting test book..."
        api_request DELETE "/books/$BOOK_ID" 2>/dev/null || true
    fi

    # Delete API key if exists
    if [[ -f "$TEST_DATA_DIR/api-key.json" ]]; then
        KEY_ID=$(jq -r '.id' "$TEST_DATA_DIR/api-key.json" 2>/dev/null || true)
        if [[ -n "$KEY_ID" ]]; then
            print_step "Deleting test API key..."
            api_request DELETE "/auth/api-keys/$KEY_ID" 2>/dev/null || true
        fi
    fi

    # Note: We don't delete the test user as it may be useful for future tests

    print_success "Cleanup completed"
}

# Main execution
main() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║            ILM Red API - Full Test Suite                  ║${NC}"
    echo -e "${BLUE}║                                                           ║${NC}"
    echo -e "${BLUE}║  API: ${API_BASE_URL}${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Clear any existing tokens to start fresh
    clear_tokens

    # ========================================
    # PHASE 1: Health Check (No Auth)
    # ========================================
    run_test "Health Check" "01-health/test-health.sh"

    # ========================================
    # PHASE 2: Authentication
    # ========================================
    run_test "User Registration" "02-auth/test-register.sh"
    run_test "User Login" "02-auth/test-login.sh"

    if [[ "$QUICK_MODE" == "false" ]]; then
        run_test "Token Refresh" "02-auth/test-refresh.sh"
    fi

    # ========================================
    # PHASE 3: User Profile
    # ========================================
    run_test "Get Current User" "04-users/test-get-me.sh"

    if [[ "$QUICK_MODE" == "false" ]]; then
        run_test "Update User Profile" "04-users/test-update-me.sh"
    fi

    # ========================================
    # PHASE 4: API Keys
    # ========================================
    if [[ "$QUICK_MODE" == "false" ]]; then
        run_test "Create API Key" "03-api-keys/test-create-key.sh"
        run_test "List API Keys" "03-api-keys/test-list-keys.sh"
    fi

    # ========================================
    # PHASE 5: Books
    # ========================================
    run_test "Upload Book" "05-books/test-upload-book.sh"
    run_test "List Books" "05-books/test-list-books.sh"
    run_test "Get Book Details" "05-books/test-get-book.sh"

    if [[ "$QUICK_MODE" == "false" ]]; then
        run_test "Update Book" "05-books/test-update-book.sh"
        run_test "Get Download URL" "05-books/test-download-book.sh"
    fi

    # ========================================
    # PHASE 6: Favorites
    # ========================================
    if [[ "$QUICK_MODE" == "false" ]]; then
        run_test "Add to Favorites" "07-favorites/test-add-favorite.sh"
        run_test "List Favorites" "07-favorites/test-list-favorites.sh"
        run_test "Remove from Favorites" "07-favorites/test-remove-favorite.sh"
    fi

    # ========================================
    # PHASE 7: Cleanup & Logout
    # ========================================
    cleanup

    if [[ "$QUICK_MODE" == "false" ]]; then
        # Delete API key we created
        if [[ -f "$TEST_DATA_DIR/api-key.json" ]]; then
            run_test "Delete API Key" "03-api-keys/test-delete-key.sh"
        fi
    fi

    # Note: We skip the ratings tests by default because you can't rate your own book
    # To test ratings, you'd need to:
    # 1. Create a second user
    # 2. Have that user rate the first user's book

    # Final logout
    run_test "Logout" "02-auth/test-logout.sh"

    # ========================================
    # Summary
    # ========================================
    print_summary

    # Exit with appropriate code
    if [[ $TESTS_FAILED -gt 0 ]]; then
        exit 1
    fi
}

# Trap to ensure cleanup on exit
trap 'print_summary' EXIT

# Run main
main
