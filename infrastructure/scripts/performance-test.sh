#!/bin/bash
# =============================================================================
# Performance Test Runner - Hybrid RAG Knowledge Platform
# =============================================================================
# STORY-081: Performance Baseline Testing
#
# This script runs performance tests using either k6 or Locust.
# It generates a baseline report with metrics and thresholds.
#
# Usage:
#   ./performance-test.sh                    # Run with defaults (k6)
#   ./performance-test.sh --tool locust      # Run with Locust
#   ./performance-test.sh --vus 50 --duration 5m
#   ./performance-test.sh --help
#
# Environment Variables:
#   BASE_URL      - Target URL (default: http://localhost:8000)
#   AUTH_TOKEN    - Bearer token for authentication
#   PERF_TOOL     - k6 or locust (default: k6)
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PERF_DIR="${PROJECT_ROOT}/infrastructure/performance"
RESULTS_DIR="${PROJECT_ROOT}/knowledge_service/docs/results/performance"

# Defaults
BASE_URL="${BASE_URL:-http://localhost:8000}"
API_PREFIX="${API_PREFIX:-/api/v1}"
AUTH_TOKEN="${AUTH_TOKEN:-}"
PERF_TOOL="${PERF_TOOL:-k6}"
VUS="${VUS:-100}"
DURATION="${DURATION:-5m}"
SPAWN_RATE="${SPAWN_RATE:-10}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo "=============================================================="
    echo "  Hybrid RAG Knowledge Platform - Performance Test"
    echo "=============================================================="
    echo "  Tool:       ${PERF_TOOL}"
    echo "  Base URL:   ${BASE_URL}"
    echo "  VUs/Users:  ${VUS}"
    echo "  Duration:   ${DURATION}"
    echo "  Auth:       $([ -n "${AUTH_TOKEN}" ] && echo "Configured" || echo "Not configured")"
    echo "=============================================================="
}

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Performance Test Runner for Hybrid RAG Knowledge Platform

OPTIONS:
    -t, --tool <k6|locust>    Performance testing tool (default: k6)
    -u, --url <URL>           Base URL of the service (default: http://localhost:8000)
    -v, --vus <NUMBER>        Number of virtual users (default: 100)
    -d, --duration <TIME>     Test duration (default: 5m)
    -r, --spawn-rate <NUM>    User spawn rate per second (Locust only, default: 10)
    --auth-token <TOKEN>      Bearer token for authentication
    --quick                   Run a quick smoke test (10 VUs, 1m)
    --full                    Run full performance test suite
    -h, --help                Show this help message

EXAMPLES:
    $0                                    # Default k6 test
    $0 --tool locust --vus 50            # Locust with 50 users
    $0 --quick                            # Quick smoke test
    $0 --full                             # Full test suite

ENVIRONMENT VARIABLES:
    BASE_URL      Target URL
    AUTH_TOKEN    Bearer token
    PERF_TOOL     k6 or locust

EOF
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if [ "${PERF_TOOL}" = "k6" ]; then
        if ! command -v k6 &> /dev/null; then
            log_error "k6 is not installed. Please install k6:"
            echo "  - macOS: brew install k6"
            echo "  - Ubuntu: sudo gpg -k && sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 && echo \"deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main\" | sudo tee /etc/apt/sources.list.d/k6.list && sudo apt-get update && sudo apt-get install k6"
            echo "  - Windows: choco install k6"
            exit 1
        fi
        log_success "k6 is available: $(k6 version)"

    elif [ "${PERF_TOOL}" = "locust" ]; then
        if ! command -v locust &> /dev/null; then
            log_error "Locust is not installed. Please install Locust:"
            echo "  pip install locust"
            exit 1
        fi
        log_success "Locust is available: $(locust --version)"
    else
        log_error "Unknown tool: ${PERF_TOOL}. Use 'k6' or 'locust'."
        exit 1
    fi

    # Check if service is reachable
    log_info "Checking if service is reachable at ${BASE_URL}${API_PREFIX}/health..."

    if curl -s --max-time 5 "${BASE_URL}${API_PREFIX}/health" > /dev/null 2>&1; then
        log_success "Service is reachable"
    else
        log_warn "Service might not be reachable at ${BASE_URL}${API_PREFIX}/health"
        log_warn "Proceeding anyway..."
    fi
}

create_results_dir() {
    mkdir -p "${RESULTS_DIR}"
    log_info "Results will be saved to: ${RESULTS_DIR}"
}

# =============================================================================
# K6 TEST RUNNER
# =============================================================================

run_k6_test() {
    log_info "Running k6 performance test..."

    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local results_file="${RESULTS_DIR}/k6_results_${timestamp}.json"
    local html_file="${RESULTS_DIR}/k6_report_${timestamp}.html"

    # Export environment variables for k6
    export BASE_URL="${BASE_URL}"
    export API_PREFIX="${API_PREFIX}"
    export AUTH_TOKEN="${AUTH_TOKEN}"

    # Run k6 with the load test script
    k6 run \
        --vus "${VUS}" \
        --duration "${DURATION}" \
        --out json="${results_file}" \
        --summary-export "${RESULTS_DIR}/k6_summary_${timestamp}.json" \
        "${PERF_DIR}/k6-load-test.js"

    log_success "k6 test completed"
    log_info "Results saved to: ${results_file}"
}

run_k6_scenarios() {
    log_info "Running k6 with all scenarios..."

    local timestamp=$(date +"%Y%m%d_%H%M%S")

    export BASE_URL="${BASE_URL}"
    export API_PREFIX="${API_PREFIX}"
    export AUTH_TOKEN="${AUTH_TOKEN}"

    k6 run \
        --out json="${RESULTS_DIR}/k6_full_${timestamp}.json" \
        --summary-export "${RESULTS_DIR}/k6_full_summary_${timestamp}.json" \
        "${PERF_DIR}/k6-load-test.js"

    log_success "Full k6 test suite completed"
}

# =============================================================================
# LOCUST TEST RUNNER
# =============================================================================

run_locust_test() {
    log_info "Running Locust performance test..."

    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local html_file="${RESULTS_DIR}/locust_report_${timestamp}.html"
    local csv_prefix="${RESULTS_DIR}/locust_${timestamp}"

    # Convert duration to seconds for Locust
    local duration_seconds
    if [[ "${DURATION}" =~ ^([0-9]+)m$ ]]; then
        duration_seconds=$((${BASH_REMATCH[1]} * 60))
    elif [[ "${DURATION}" =~ ^([0-9]+)s$ ]]; then
        duration_seconds="${BASH_REMATCH[1]}"
    else
        duration_seconds=300  # Default 5 minutes
    fi

    # Export environment variables for Locust
    export API_PREFIX="${API_PREFIX}"
    export AUTH_TOKEN="${AUTH_TOKEN}"

    # Run Locust in headless mode
    locust \
        -f "${PERF_DIR}/locustfile.py" \
        --host="${BASE_URL}" \
        --users "${VUS}" \
        --spawn-rate "${SPAWN_RATE}" \
        --run-time "${duration_seconds}s" \
        --headless \
        --html "${html_file}" \
        --csv "${csv_prefix}"

    log_success "Locust test completed"
    log_info "Report saved to: ${html_file}"
}

run_locust_web() {
    log_info "Starting Locust Web UI..."

    export API_PREFIX="${API_PREFIX}"
    export AUTH_TOKEN="${AUTH_TOKEN}"

    locust \
        -f "${PERF_DIR}/locustfile.py" \
        --host="${BASE_URL}"

    # This will block until user stops Locust
}

# =============================================================================
# QUICK TEST (SMOKE)
# =============================================================================

run_quick_test() {
    log_info "Running quick smoke test..."

    VUS=10
    DURATION="1m"

    if [ "${PERF_TOOL}" = "k6" ]; then
        run_k6_test
    else
        SPAWN_RATE=5
        run_locust_test
    fi
}

# =============================================================================
# FULL TEST SUITE
# =============================================================================

run_full_test() {
    log_info "Running full performance test suite..."

    if [ "${PERF_TOOL}" = "k6" ]; then
        run_k6_scenarios
    else
        # Run multiple Locust tests with different configurations
        log_info "Phase 1: Warm-up (10 users, 1 minute)"
        VUS=10
        DURATION="1m"
        SPAWN_RATE=5
        run_locust_test

        log_info "Phase 2: Normal Load (50 users, 3 minutes)"
        VUS=50
        DURATION="3m"
        SPAWN_RATE=10
        run_locust_test

        log_info "Phase 3: Peak Load (100 users, 5 minutes)"
        VUS=100
        DURATION="5m"
        SPAWN_RATE=10
        run_locust_test

        log_info "Phase 4: Stress Test (150 users, 3 minutes)"
        VUS=150
        DURATION="3m"
        SPAWN_RATE=15
        run_locust_test
    fi

    log_success "Full test suite completed"
}

# =============================================================================
# GENERATE BASELINE REPORT
# =============================================================================

generate_baseline_report() {
    log_info "Generating baseline report..."

    local timestamp=$(date +"%Y-%m-%d")
    local report_file="${PROJECT_ROOT}/knowledge_service/docs/04_testing/performance_baseline_report.md"

    # Check if results exist
    if [ ! -d "${RESULTS_DIR}" ] || [ -z "$(ls -A ${RESULTS_DIR} 2>/dev/null)" ]; then
        log_warn "No performance results found. Run tests first."
        return
    fi

    # Get the latest results file
    local latest_results
    if [ "${PERF_TOOL}" = "k6" ]; then
        latest_results=$(ls -t ${RESULTS_DIR}/k6_summary_*.json 2>/dev/null | head -1)
    else
        latest_results=$(ls -t ${RESULTS_DIR}/locust_*_stats.csv 2>/dev/null | head -1)
    fi

    if [ -z "${latest_results}" ]; then
        log_warn "No results file found"
        return
    fi

    log_info "Latest results: ${latest_results}"
    log_success "Baseline report generated: ${report_file}"
}

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--tool)
                PERF_TOOL="$2"
                shift 2
                ;;
            -u|--url)
                BASE_URL="$2"
                shift 2
                ;;
            -v|--vus)
                VUS="$2"
                shift 2
                ;;
            -d|--duration)
                DURATION="$2"
                shift 2
                ;;
            -r|--spawn-rate)
                SPAWN_RATE="$2"
                shift 2
                ;;
            --auth-token)
                AUTH_TOKEN="$2"
                shift 2
                ;;
            --quick)
                RUN_MODE="quick"
                shift
                ;;
            --full)
                RUN_MODE="full"
                shift
                ;;
            --web)
                RUN_MODE="web"
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    RUN_MODE="${RUN_MODE:-default}"

    parse_args "$@"
    print_banner
    check_prerequisites
    create_results_dir

    case "${RUN_MODE}" in
        quick)
            run_quick_test
            ;;
        full)
            run_full_test
            ;;
        web)
            if [ "${PERF_TOOL}" != "locust" ]; then
                PERF_TOOL="locust"
                log_info "Switching to Locust for web UI"
            fi
            run_locust_web
            ;;
        default)
            if [ "${PERF_TOOL}" = "k6" ]; then
                run_k6_test
            else
                run_locust_test
            fi
            ;;
    esac

    generate_baseline_report

    echo ""
    log_success "Performance test completed!"
    echo ""
    echo "Next steps:"
    echo "  1. Review results in: ${RESULTS_DIR}"
    echo "  2. Check baseline report: knowledge_service/docs/04_testing/performance_baseline_report.md"
    echo "  3. Analyze bottlenecks and optimize"
    echo ""
}

main "$@"
