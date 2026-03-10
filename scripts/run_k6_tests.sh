#!/bin/bash
# ==============================================================================
# k6 Performance Test Runner
# ==============================================================================
#
# Hybrid RAG Knowledge Platform - k6 부하 테스트 실행 스크립트
#
# Usage:
#   ./scripts/run_k6_tests.sh [scenario] [test]
#
# Arguments:
#   scenario: smoke | load | stress (default: smoke)
#   test:     search | chat | auth | all (default: all)
#
# Examples:
#   ./scripts/run_k6_tests.sh                   # smoke test, all APIs
#   ./scripts/run_k6_tests.sh load search       # load test, search API only
#   ./scripts/run_k6_tests.sh stress all         # stress test, all APIs
#
# Docker mode:
#   ./scripts/run_k6_tests.sh --docker smoke all  # Run k6 via Docker
#
# Environment Variables:
#   BASE_URL:      API base URL (default: http://localhost:8080)
#   AUTH_EMAIL:    Login email (default: admin@example.com)
#   AUTH_PASSWORD: Login password (default: admin123!)
#   K6_OUT:        Output format (default: json)
#
# STORY-129: k6 성능 회귀 테스트 스크립트
# ==============================================================================

set -euo pipefail

# --- Configuration ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PERF_TEST_DIR="${PROJECT_ROOT}/knowledge_service/src/tests/performance"
RESULTS_DIR="${PROJECT_ROOT}/knowledge_service/docs/results/k6"

BASE_URL="${BASE_URL:-http://localhost:8080}"
AUTH_EMAIL="${AUTH_EMAIL:-admin@example.com}"
AUTH_PASSWORD="${AUTH_PASSWORD:-admin123!}"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Functions ---
log_info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $*"; }

usage() {
    echo "Usage: $0 [--docker] [scenario] [test]"
    echo ""
    echo "  scenario: smoke | load | stress  (default: smoke)"
    echo "  test:     search | chat | auth | all  (default: all)"
    echo ""
    echo "  --docker: Run k6 via Docker container"
    echo ""
    echo "Examples:"
    echo "  $0                        # smoke test, all APIs"
    echo "  $0 load search            # load test, search API only"
    echo "  $0 --docker stress all    # stress test via Docker"
    exit 0
}

# --- Parse Arguments ---
USE_DOCKER=false
SCENARIO="smoke"
TEST_TARGET="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --docker)
            USE_DOCKER=true
            shift
            ;;
        --help|-h)
            usage
            ;;
        smoke|load|stress)
            SCENARIO="$1"
            shift
            ;;
        search|chat|auth|all)
            TEST_TARGET="$1"
            shift
            ;;
        *)
            log_error "Unknown argument: $1"
            usage
            ;;
    esac
done

# --- Pre-flight Checks ---
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=============================================="
log_info "k6 Performance Test Runner"
echo "=============================================="
echo "  Scenario:   ${SCENARIO}"
echo "  Target:     ${TEST_TARGET}"
echo "  Base URL:   ${BASE_URL}"
echo "  Docker:     ${USE_DOCKER}"
echo "  Timestamp:  ${TIMESTAMP}"
echo "=============================================="
echo ""

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Check k6 availability
if [ "$USE_DOCKER" = false ]; then
    if ! command -v k6 &>/dev/null; then
        log_warn "k6 not found locally. Trying Docker mode..."
        USE_DOCKER=true
    fi
fi

if [ "$USE_DOCKER" = true ]; then
    if ! command -v docker &>/dev/null; then
        log_error "Docker not found. Install k6 or Docker."
        log_info "Install k6: https://k6.io/docs/get-started/installation/"
        exit 1
    fi
    log_info "Using Docker to run k6"
fi

# --- Run k6 Test ---
run_k6_test() {
    local test_name="$1"
    local test_file="$2"
    local result_file="${RESULTS_DIR}/k6_${test_name}_${SCENARIO}_${TIMESTAMP}.json"

    log_step "Running ${test_name} test (${SCENARIO})..."

    local k6_env_args=(
        "--env" "SCENARIO=${SCENARIO}"
        "--env" "BASE_URL=${BASE_URL}"
        "--env" "AUTH_EMAIL=${AUTH_EMAIL}"
        "--env" "AUTH_PASSWORD=${AUTH_PASSWORD}"
    )

    local exit_code=0

    if [ "$USE_DOCKER" = true ]; then
        # For Docker, we need to handle network access
        # When running against localhost, use host.docker.internal (macOS/Windows)
        # or --network=host (Linux)
        local docker_base_url="${BASE_URL}"
        if [[ "$BASE_URL" == *"localhost"* ]]; then
            docker_base_url="${BASE_URL//localhost/host.docker.internal}"
        fi

        docker run --rm \
            -v "${PERF_TEST_DIR}:/scripts:ro" \
            --add-host=host.docker.internal:host-gateway \
            grafana/k6:latest run \
            "${k6_env_args[@]}" \
            --env "BASE_URL=${docker_base_url}" \
            --summary-export="/dev/stderr" \
            "/scripts/$(basename "${test_file}")" \
            2>"${result_file}" || exit_code=$?
    else
        k6 run \
            "${k6_env_args[@]}" \
            --summary-export="${result_file}" \
            "${test_file}" || exit_code=$?
    fi

    if [ $exit_code -eq 0 ]; then
        log_info "${test_name} test PASSED"
    elif [ $exit_code -eq 99 ]; then
        log_warn "${test_name} test FAILED (thresholds breached)"
    else
        log_error "${test_name} test ERROR (exit code: ${exit_code})"
    fi

    if [ -f "${result_file}" ]; then
        log_info "Results saved: ${result_file}"
    fi

    echo ""
    return $exit_code
}

# --- Execute Tests ---
OVERALL_EXIT=0

if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "auth" ]; then
    run_k6_test "auth" "${PERF_TEST_DIR}/k6_auth_test.js" || OVERALL_EXIT=1
fi

if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "search" ]; then
    run_k6_test "search" "${PERF_TEST_DIR}/k6_search_test.js" || OVERALL_EXIT=1
fi

if [ "$TEST_TARGET" = "all" ] || [ "$TEST_TARGET" = "chat" ]; then
    run_k6_test "chat" "${PERF_TEST_DIR}/k6_chat_test.js" || OVERALL_EXIT=1
fi

# --- Summary ---
echo "=============================================="
if [ $OVERALL_EXIT -eq 0 ]; then
    log_info "All k6 tests PASSED"
else
    log_warn "Some k6 tests FAILED or had threshold breaches"
fi
echo "=============================================="
log_info "Results directory: ${RESULTS_DIR}"
echo ""

exit $OVERALL_EXIT
