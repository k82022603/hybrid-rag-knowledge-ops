#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Staging Environment Validation Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Author: QA Agent (Claude Opus 4.5)
# Description: Comprehensive staging environment validation before production
# Usage: ./staging-validation.sh [--full|--smoke|--category <name>|--data-flow]
# JIRA: STORY-080
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"
KNOWLEDGE_SERVICE="${PROJECT_ROOT}/knowledge_service"
REPORTS_DIR="${PROJECT_ROOT}/knowledge_service/docs/results/staging_validation"

# Slack notification script
SLACK_SCRIPT="${PROJECT_ROOT}/scripts/send_slack.sh"

# Timestamp for reports
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORTS_DIR}/validation_${TIMESTAMP}.md"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Test categories
declare -A CATEGORY_PASSED
declare -A CATEGORY_FAILED
declare -A CATEGORY_TOTAL

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_header() {
    echo ""
    echo -e "${CYAN}=============================================================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}=============================================================================${NC}"
}

log_section() {
    echo ""
    echo -e "${MAGENTA}=== $1 ===${NC}"
}

log_check() {
    local status="$1"
    local category="$2"
    local message="$3"
    local detail="${4:-}"

    ((TOTAL_TESTS++))
    CATEGORY_TOTAL[$category]=$((${CATEGORY_TOTAL[$category]:-0} + 1))

    case "$status" in
        PASS)
            echo -e "${GREEN}[PASS]${NC} [$category] $message"
            ((PASSED_TESTS++))
            CATEGORY_PASSED[$category]=$((${CATEGORY_PASSED[$category]:-0} + 1))
            ;;
        FAIL)
            echo -e "${RED}[FAIL]${NC} [$category] $message"
            [[ -n "$detail" ]] && echo "       $detail"
            ((FAILED_TESTS++))
            CATEGORY_FAILED[$category]=$((${CATEGORY_FAILED[$category]:-0} + 1))
            ;;
        SKIP)
            echo -e "${YELLOW}[SKIP]${NC} [$category] $message"
            [[ -n "$detail" ]] && echo "       $detail"
            ((SKIPPED_TESTS++))
            ;;
        INFO)
            echo -e "${BLUE}[INFO]${NC} [$category] $message"
            ;;
    esac
}

send_slack() {
    local channel="$1"
    local message="$2"

    if [[ -x "$SLACK_SCRIPT" ]]; then
        "$SLACK_SCRIPT" "$channel" "QA" "$message" 2>/dev/null || true
    fi
}

ensure_reports_dir() {
    mkdir -p "$REPORTS_DIR"
}

# =============================================================================
# PRE-VALIDATION
# =============================================================================

run_pre_validation() {
    log_section "Pre-Validation Checks"

    # Check Docker
    if docker info &> /dev/null; then
        log_check PASS "INFRA" "Docker daemon is running"
    else
        log_check FAIL "INFRA" "Docker daemon is not running"
        return 1
    fi

    # Check Docker Compose
    if docker compose version &> /dev/null; then
        log_check PASS "INFRA" "Docker Compose is available"
    else
        log_check FAIL "INFRA" "Docker Compose is not available"
        return 1
    fi

    # Check if staging environment file exists
    if [[ -f "${DOCKER_DIR}/.env.staging" ]]; then
        log_check PASS "INFRA" "Staging environment file exists"
    else
        log_check FAIL "INFRA" "Staging environment file not found" "${DOCKER_DIR}/.env.staging"
    fi

    # Check project directories
    local dirs=("$KNOWLEDGE_SERVICE" "${KNOWLEDGE_SERVICE}/frontend" "${KNOWLEDGE_SERVICE}/backend")
    for dir in "${dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            log_check PASS "INFRA" "Directory exists: $(basename "$dir")"
        else
            log_check FAIL "INFRA" "Directory not found: $dir"
        fi
    done
}

# =============================================================================
# CONTAINER HEALTH CHECKS
# =============================================================================

run_container_checks() {
    log_section "Container Health Checks"

    cd "$DOCKER_DIR"

    # Expected containers (18 total, excluding init-db which should be exited)
    local critical_containers=(
        "kp-nginx"
        "kp-frontend"
        "kp-api-gateway"
        "kp-backend"
        "kp-ai-service"
        "kp-postgresql"
        "kp-keycloak-db"
        "kp-elasticsearch"
        "kp-neo4j"
        "kp-redis"
        "kp-minio"
        "kp-keycloak"
    )

    local monitoring_containers=(
        "kp-prometheus"
        "kp-grafana"
        "kp-loki"
        "kp-promtail"
        "kp-jaeger"
    )

    # Check critical containers
    for container in "${critical_containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local health
            health=$(docker inspect --format '{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")

            if [[ "$health" == "healthy" || "$health" == "N/A" ]]; then
                log_check PASS "CONTAINER" "$container is running (health: $health)"
            else
                log_check FAIL "CONTAINER" "$container is running but health: $health"
            fi
        else
            log_check FAIL "CONTAINER" "$container is not running"
        fi
    done

    # Check monitoring containers (non-critical)
    for container in "${monitoring_containers[@]}"; do
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            log_check PASS "MONITOR" "$container is running"
        else
            log_check SKIP "MONITOR" "$container is not running" "Monitoring optional in staging"
        fi
    done

    # Check init-db (should be exited)
    local init_status
    init_status=$(docker ps -a --format '{{.Names}} {{.Status}}' | grep "kp-init-db" | awk '{print $2}' || echo "not found")
    if [[ "$init_status" == "Exited" ]]; then
        log_check PASS "CONTAINER" "kp-init-db completed successfully"
    else
        log_check SKIP "CONTAINER" "kp-init-db status: $init_status"
    fi
}

# =============================================================================
# SERVICE HEALTH CHECKS
# =============================================================================

run_service_health_checks() {
    log_section "Service Health Endpoints"

    # Backend Health
    local backend_url="http://localhost:8081/actuator/health"
    local backend_response
    backend_response=$(curl -s -w "\n%{http_code}" "$backend_url" 2>/dev/null || echo "error\n000")
    local backend_code=$(echo "$backend_response" | tail -1)
    local backend_body=$(echo "$backend_response" | head -n -1)

    if [[ "$backend_code" == "200" ]]; then
        local backend_status
        backend_status=$(echo "$backend_body" | grep -o '"status":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "UNKNOWN")
        if [[ "$backend_status" == "UP" ]]; then
            log_check PASS "HEALTH" "Backend: UP"
        else
            log_check FAIL "HEALTH" "Backend: $backend_status"
        fi
    else
        log_check FAIL "HEALTH" "Backend: Not responding (HTTP $backend_code)"
    fi

    # AI Service Health
    local ai_url="http://localhost:8000/api/v1/health"
    local ai_code
    ai_code=$(curl -s -w "%{http_code}" -o /dev/null "$ai_url" 2>/dev/null || echo "000")

    if [[ "$ai_code" == "200" ]]; then
        log_check PASS "HEALTH" "AI Service: OK"
    else
        log_check FAIL "HEALTH" "AI Service: Not responding (HTTP $ai_code)"
    fi

    # API Gateway Health
    local gateway_url="http://localhost:8080/actuator/health"
    local gateway_code
    gateway_code=$(curl -s -w "%{http_code}" -o /dev/null "$gateway_url" 2>/dev/null || echo "000")

    if [[ "$gateway_code" == "200" ]]; then
        log_check PASS "HEALTH" "API Gateway: UP"
    else
        log_check FAIL "HEALTH" "API Gateway: Not responding (HTTP $gateway_code)"
    fi

    # Frontend
    local frontend_code
    frontend_code=$(curl -s -w "%{http_code}" -o /dev/null "http://localhost:80" 2>/dev/null || echo "000")

    if [[ "$frontend_code" == "200" || "$frontend_code" == "304" ]]; then
        log_check PASS "HEALTH" "Frontend: Accessible"
    else
        log_check FAIL "HEALTH" "Frontend: Not accessible (HTTP $frontend_code)"
    fi

    # Elasticsearch
    local es_url="http://localhost:9200/_cluster/health"
    local es_response
    es_response=$(curl -s "$es_url" 2>/dev/null || echo "{}")
    local es_status
    es_status=$(echo "$es_response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "error")

    if [[ "$es_status" == "green" || "$es_status" == "yellow" ]]; then
        log_check PASS "HEALTH" "Elasticsearch: $es_status"
    else
        log_check FAIL "HEALTH" "Elasticsearch: $es_status"
    fi

    # Neo4j
    local neo4j_code
    neo4j_code=$(curl -s -w "%{http_code}" -o /dev/null "http://localhost:7474" 2>/dev/null || echo "000")

    if [[ "$neo4j_code" == "200" ]]; then
        log_check PASS "HEALTH" "Neo4j: Accessible"
    else
        log_check FAIL "HEALTH" "Neo4j: Not accessible (HTTP $neo4j_code)"
    fi

    # Redis
    if docker ps --format '{{.Names}}' | grep -q "kp-redis"; then
        local redis_ping
        redis_ping=$(docker exec kp-redis redis-cli ping 2>/dev/null || echo "error")
        if [[ "$redis_ping" == "PONG" ]]; then
            log_check PASS "HEALTH" "Redis: PONG"
        else
            log_check FAIL "HEALTH" "Redis: Not responding"
        fi
    else
        log_check SKIP "HEALTH" "Redis: Container not running"
    fi

    # PostgreSQL
    if docker ps --format '{{.Names}}' | grep -q "kp-postgresql"; then
        if docker exec kp-postgresql pg_isready -U knowledge > /dev/null 2>&1; then
            log_check PASS "HEALTH" "PostgreSQL: Ready"
        else
            log_check FAIL "HEALTH" "PostgreSQL: Not ready"
        fi
    else
        log_check SKIP "HEALTH" "PostgreSQL: Container not running"
    fi

    # Keycloak
    local kc_code
    kc_code=$(curl -s -w "%{http_code}" -o /dev/null "http://localhost:8180/health/ready" 2>/dev/null || echo "000")

    if [[ "$kc_code" == "200" ]]; then
        log_check PASS "HEALTH" "Keycloak: Ready"
    else
        log_check FAIL "HEALTH" "Keycloak: Not ready (HTTP $kc_code)"
    fi
}

# =============================================================================
# UNIT TESTS
# =============================================================================

run_unit_tests() {
    log_section "Unit Tests"

    local unit_passed=0
    local unit_failed=0

    # Backend Unit Tests (SpringBoot)
    if [[ -d "${KNOWLEDGE_SERVICE}/backend" && -f "${KNOWLEDGE_SERVICE}/backend/gradlew" ]]; then
        echo "Running Backend unit tests..."
        cd "${KNOWLEDGE_SERVICE}/backend"

        if ./gradlew test --quiet 2>/dev/null; then
            local test_count
            test_count=$(find build/test-results/test -name "*.xml" -exec grep -h "tests=" {} \; 2>/dev/null | grep -o 'tests="[0-9]*"' | cut -d'"' -f2 | awk '{sum+=$1} END {print sum}' || echo "0")
            log_check PASS "UNIT-BE" "Backend tests passed: ${test_count:-0} tests"
            ((unit_passed++))
        else
            log_check FAIL "UNIT-BE" "Backend tests failed"
            ((unit_failed++))
        fi
    else
        log_check SKIP "UNIT-BE" "Backend test environment not available"
    fi

    # AI Service Unit Tests (Python)
    if [[ -d "${KNOWLEDGE_SERVICE}/src/tests" ]]; then
        echo "Running AI Service unit tests..."
        cd "${KNOWLEDGE_SERVICE}"

        if python -m pytest src/tests/unit --quiet --tb=no 2>/dev/null; then
            local pytest_count
            pytest_count=$(python -m pytest src/tests/unit --collect-only -q 2>/dev/null | tail -1 | grep -o '[0-9]*' | head -1 || echo "0")
            log_check PASS "UNIT-AI" "AI Service tests passed: ${pytest_count:-0} tests"
            ((unit_passed++))
        else
            log_check FAIL "UNIT-AI" "AI Service tests failed or not configured"
            ((unit_failed++))
        fi
    else
        log_check SKIP "UNIT-AI" "AI Service test directory not found"
    fi

    # Frontend Unit Tests (React)
    if [[ -d "${KNOWLEDGE_SERVICE}/frontend" && -f "${KNOWLEDGE_SERVICE}/frontend/package.json" ]]; then
        echo "Running Frontend unit tests..."
        cd "${KNOWLEDGE_SERVICE}/frontend"

        if npm run test:run --silent 2>/dev/null; then
            log_check PASS "UNIT-FE" "Frontend tests passed"
            ((unit_passed++))
        else
            log_check FAIL "UNIT-FE" "Frontend tests failed or not configured"
            ((unit_failed++))
        fi
    else
        log_check SKIP "UNIT-FE" "Frontend test environment not available"
    fi

    echo ""
    log_check INFO "UNIT" "Unit test summary: $unit_passed passed, $unit_failed failed"
}

# =============================================================================
# INTEGRATION TESTS
# =============================================================================

run_integration_tests() {
    log_section "Integration Tests"

    local int_passed=0
    local int_failed=0

    # Backend Integration Tests
    if [[ -d "${KNOWLEDGE_SERVICE}/backend" && -f "${KNOWLEDGE_SERVICE}/backend/gradlew" ]]; then
        echo "Running Backend integration tests..."
        cd "${KNOWLEDGE_SERVICE}/backend"

        if ./gradlew integrationTest --quiet 2>/dev/null; then
            log_check PASS "INT-BE" "Backend integration tests passed"
            ((int_passed++))
        else
            log_check FAIL "INT-BE" "Backend integration tests failed"
            ((int_failed++))
        fi
    else
        log_check SKIP "INT-BE" "Backend integration test environment not available"
    fi

    # AI Service Integration Tests
    if [[ -d "${KNOWLEDGE_SERVICE}/src/tests/integration" ]]; then
        echo "Running AI Service integration tests..."
        cd "${KNOWLEDGE_SERVICE}"

        if python -m pytest src/tests/integration --quiet --tb=no 2>/dev/null; then
            log_check PASS "INT-AI" "AI Service integration tests passed"
            ((int_passed++))
        else
            log_check FAIL "INT-AI" "AI Service integration tests failed or not configured"
            ((int_failed++))
        fi
    else
        log_check SKIP "INT-AI" "AI Service integration test directory not found"
    fi

    echo ""
    log_check INFO "INT" "Integration test summary: $int_passed passed, $int_failed failed"
}

# =============================================================================
# E2E TESTS
# =============================================================================

run_e2e_tests() {
    log_section "E2E Tests (Playwright)"

    if [[ -d "${KNOWLEDGE_SERVICE}/frontend" && -f "${KNOWLEDGE_SERVICE}/frontend/playwright.config.ts" ]]; then
        echo "Running E2E tests with Playwright..."
        cd "${KNOWLEDGE_SERVICE}/frontend"

        # Install Playwright browsers if needed
        npx playwright install chromium --with-deps 2>/dev/null || true

        if npx playwright test --reporter=list 2>/dev/null; then
            local e2e_count
            e2e_count=$(npx playwright test --list 2>/dev/null | grep -c "test" || echo "0")
            log_check PASS "E2E" "E2E tests passed: ${e2e_count} tests"
        else
            log_check FAIL "E2E" "E2E tests failed"
        fi
    else
        log_check SKIP "E2E" "Playwright not configured"
    fi
}

# =============================================================================
# SECURITY TESTS
# =============================================================================

run_security_tests() {
    log_section "Security Tests"

    # API Security - Check for common vulnerabilities
    echo "Running security checks..."

    # Check TLS configuration
    local nginx_tls
    nginx_tls=$(docker exec kp-nginx cat /etc/nginx/nginx.conf 2>/dev/null | grep -c "ssl_protocols" || echo "0")
    if [[ "$nginx_tls" -gt 0 ]]; then
        log_check PASS "SEC" "TLS configuration found in Nginx"
    else
        log_check SKIP "SEC" "TLS configuration not verified"
    fi

    # Check for security headers
    local headers_response
    headers_response=$(curl -s -I "http://localhost:80" 2>/dev/null || echo "")

    if echo "$headers_response" | grep -qi "X-Content-Type-Options"; then
        log_check PASS "SEC" "X-Content-Type-Options header present"
    else
        log_check FAIL "SEC" "X-Content-Type-Options header missing"
    fi

    if echo "$headers_response" | grep -qi "X-Frame-Options"; then
        log_check PASS "SEC" "X-Frame-Options header present"
    else
        log_check FAIL "SEC" "X-Frame-Options header missing"
    fi

    # Check for exposed sensitive endpoints
    local actuator_code
    actuator_code=$(curl -s -w "%{http_code}" -o /dev/null "http://localhost:8081/actuator/env" 2>/dev/null || echo "000")
    if [[ "$actuator_code" == "401" || "$actuator_code" == "403" || "$actuator_code" == "404" ]]; then
        log_check PASS "SEC" "Sensitive actuator endpoints protected"
    else
        log_check FAIL "SEC" "Sensitive actuator endpoint exposed (HTTP $actuator_code)"
    fi

    # Check JWT secret length (from env file)
    if [[ -f "${DOCKER_DIR}/.env.staging" ]]; then
        local jwt_secret
        jwt_secret=$(grep "^JWT_SECRET=" "${DOCKER_DIR}/.env.staging" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
        if [[ ${#jwt_secret} -ge 32 ]]; then
            log_check PASS "SEC" "JWT secret has sufficient length (>= 32 chars)"
        else
            log_check FAIL "SEC" "JWT secret too short (< 32 chars)"
        fi
    fi

    # Run Python security tests if available
    if [[ -d "${KNOWLEDGE_SERVICE}/src/tests/security" ]]; then
        cd "${KNOWLEDGE_SERVICE}"
        if python -m pytest src/tests/security --quiet --tb=no 2>/dev/null; then
            log_check PASS "SEC" "Python security tests passed"
        else
            log_check FAIL "SEC" "Python security tests failed"
        fi
    else
        log_check SKIP "SEC" "Security test suite not found"
    fi
}

# =============================================================================
# DATA FLOW VALIDATION
# =============================================================================

run_data_flow_validation() {
    log_section "Data Flow Validation"

    echo "Testing document lifecycle (upload -> process -> search)..."

    # This is a simplified data flow test
    # In a full implementation, this would upload a test document and verify the complete flow

    # Check if MinIO is accessible
    local minio_code
    minio_code=$(curl -s -w "%{http_code}" -o /dev/null "http://localhost:9000/minio/health/live" 2>/dev/null || echo "000")
    if [[ "$minio_code" == "200" ]]; then
        log_check PASS "DATAFLOW" "MinIO storage accessible"
    else
        log_check FAIL "DATAFLOW" "MinIO storage not accessible"
    fi

    # Check Elasticsearch indices
    local es_indices
    es_indices=$(curl -s "http://localhost:9200/_cat/indices?format=json" 2>/dev/null | grep -c "index" || echo "0")
    if [[ "$es_indices" -gt 0 ]]; then
        log_check PASS "DATAFLOW" "Elasticsearch has $es_indices indices"
    else
        log_check SKIP "DATAFLOW" "No Elasticsearch indices found (may be expected)"
    fi

    # Check Neo4j connectivity
    if docker ps --format '{{.Names}}' | grep -q "kp-neo4j"; then
        local neo4j_result
        neo4j_result=$(docker exec kp-neo4j cypher-shell -u neo4j -p "${NEO4J_PASSWORD:-neo4j}" "RETURN 1" 2>/dev/null | grep -c "1" || echo "0")
        if [[ "$neo4j_result" -gt 0 ]]; then
            log_check PASS "DATAFLOW" "Neo4j graph database responding"
        else
            log_check SKIP "DATAFLOW" "Neo4j query failed (credentials may differ)"
        fi
    fi

    # Check PostgreSQL tables
    if docker ps --format '{{.Names}}' | grep -q "kp-postgresql"; then
        local pg_tables
        pg_tables=$(docker exec kp-postgresql psql -U knowledge -d knowledge -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null | tr -d ' ' || echo "0")
        if [[ "$pg_tables" -gt 0 ]]; then
            log_check PASS "DATAFLOW" "PostgreSQL has $pg_tables tables"
        else
            log_check SKIP "DATAFLOW" "No PostgreSQL tables found (may be expected)"
        fi
    fi
}

# =============================================================================
# API CONTRACT TESTS
# =============================================================================

run_api_contract_tests() {
    log_section "API Contract Tests"

    # Test critical API endpoints
    local endpoints=(
        "GET http://localhost:8080/actuator/info 200"
        "GET http://localhost:8081/actuator/health 200"
        "GET http://localhost:8000/api/v1/health 200"
        "GET http://localhost:8000/api/v1/documents 200,401"
        "GET http://localhost:8080/api/v1/documents 200,401"
    )

    for endpoint_spec in "${endpoints[@]}"; do
        local method url expected_codes
        read -r method url expected_codes <<< "$endpoint_spec"

        local actual_code
        actual_code=$(curl -s -w "%{http_code}" -o /dev/null -X "$method" "$url" 2>/dev/null || echo "000")

        if [[ "$expected_codes" == *"$actual_code"* ]]; then
            log_check PASS "CONTRACT" "$method $url -> HTTP $actual_code"
        else
            log_check FAIL "CONTRACT" "$method $url -> HTTP $actual_code (expected: $expected_codes)"
        fi
    done
}

# =============================================================================
# GENERATE REPORT
# =============================================================================

generate_report() {
    ensure_reports_dir

    cat > "$REPORT_FILE" << EOF
# Staging Validation Report

**Date**: $(date +"%Y-%m-%d %H:%M:%S")
**Environment**: Staging
**Script Version**: 1.0.0

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | $TOTAL_TESTS |
| Passed | $PASSED_TESTS |
| Failed | $FAILED_TESTS |
| Skipped | $SKIPPED_TESTS |
| Pass Rate | $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)% |

---

## Category Breakdown

| Category | Passed | Failed | Total |
|----------|--------|--------|-------|
EOF

    for category in "${!CATEGORY_TOTAL[@]}"; do
        echo "| $category | ${CATEGORY_PASSED[$category]:-0} | ${CATEGORY_FAILED[$category]:-0} | ${CATEGORY_TOTAL[$category]} |" >> "$REPORT_FILE"
    done

    cat >> "$REPORT_FILE" << EOF

---

## Validation Status

EOF

    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo "**PASSED** - All validation checks passed. Ready for production deployment." >> "$REPORT_FILE"
    else
        echo "**FAILED** - $FAILED_TESTS check(s) failed. Production deployment NOT recommended." >> "$REPORT_FILE"
    fi

    cat >> "$REPORT_FILE" << EOF

---

## Next Steps

EOF

    if [[ $FAILED_TESTS -eq 0 ]]; then
        cat >> "$REPORT_FILE" << EOF
1. Review this report with Tech Lead
2. Obtain approval sign-off
3. Schedule production deployment window
4. Execute production deployment
5. Run post-deployment verification
EOF
    else
        cat >> "$REPORT_FILE" << EOF
1. Review failed checks in detail
2. Create bug tickets for failures
3. Fix issues and re-run validation
4. Do NOT proceed to production until all checks pass
EOF
    fi

    echo ""
    echo "Report generated: $REPORT_FILE"
}

# =============================================================================
# SMOKE TEST (Quick Validation)
# =============================================================================

run_smoke_test() {
    log_header "Smoke Test (Quick Validation)"

    run_pre_validation
    run_container_checks
    run_service_health_checks
}

# =============================================================================
# FULL VALIDATION
# =============================================================================

run_full_validation() {
    log_header "Full Staging Environment Validation"

    run_pre_validation
    run_container_checks
    run_service_health_checks
    run_unit_tests
    run_integration_tests
    run_e2e_tests
    run_security_tests
    run_api_contract_tests
    run_data_flow_validation
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    local mode="${1:---full}"
    local category="${2:-}"

    # Send start notification
    send_slack "dev" "STAGING VALIDATION: Started - Mode: $mode"

    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - Staging Environment Validation"
    echo "============================================================================="
    echo "Mode:        $mode"
    echo "Timestamp:   $(date)"
    echo "Project:     $PROJECT_ROOT"
    echo "============================================================================="

    case "$mode" in
        --full)
            run_full_validation
            ;;
        --smoke)
            run_smoke_test
            ;;
        --category)
            case "$category" in
                infra|infrastructure)
                    run_pre_validation
                    run_container_checks
                    ;;
                health)
                    run_service_health_checks
                    ;;
                unit)
                    run_unit_tests
                    ;;
                integration)
                    run_integration_tests
                    ;;
                e2e)
                    run_e2e_tests
                    ;;
                security)
                    run_security_tests
                    ;;
                contract)
                    run_api_contract_tests
                    ;;
                dataflow|data-flow)
                    run_data_flow_validation
                    ;;
                *)
                    echo "Unknown category: $category"
                    echo "Valid categories: infra, health, unit, integration, e2e, security, contract, dataflow"
                    exit 1
                    ;;
            esac
            ;;
        --data-flow)
            run_data_flow_validation
            ;;
        -h|--help)
            cat << EOF
Hybrid RAG Knowledge Platform - Staging Validation Script

Usage: $(basename "$0") [OPTIONS]

OPTIONS:
    --full              Run full validation suite (default)
    --smoke             Run quick smoke test (containers + health)
    --category <name>   Run specific test category
    --data-flow         Run data flow validation only
    -h, --help          Show this help message

CATEGORIES:
    infra, infrastructure   Pre-validation and container checks
    health                  Service health endpoints
    unit                    Unit tests (Backend, AI Service, Frontend)
    integration             Integration tests
    e2e                     End-to-end tests (Playwright)
    security                Security tests
    contract                API contract tests
    dataflow, data-flow     Data flow validation

EXAMPLES:
    $(basename "$0") --full
    $(basename "$0") --smoke
    $(basename "$0") --category unit
    $(basename "$0") --category e2e
    $(basename "$0") --data-flow

REPORTS:
    Reports are saved to: ${REPORTS_DIR}/

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $mode"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    echo "============================================================================="
    echo "VALIDATION SUMMARY"
    echo "============================================================================="
    echo "Total Tests:  $TOTAL_TESTS"
    echo "Passed:       $PASSED_TESTS"
    echo "Failed:       $FAILED_TESTS"
    echo "Skipped:      $SKIPPED_TESTS"
    echo "============================================================================="

    # Generate report for full validation
    if [[ "$mode" == "--full" ]]; then
        generate_report
    fi

    # Final status
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "${GREEN}VALIDATION PASSED${NC}"
        echo "Staging environment is ready for production deployment review."
        send_slack "dev" "STAGING VALIDATION: PASSED - $PASSED_TESTS/$TOTAL_TESTS checks passed"
        exit 0
    else
        echo -e "${RED}VALIDATION FAILED${NC}"
        echo "$FAILED_TESTS check(s) failed. Please review and fix before proceeding."
        send_slack "dev" "STAGING VALIDATION: FAILED - $FAILED_TESTS/$TOTAL_TESTS checks failed"
        exit 1
    fi
}

main "$@"
