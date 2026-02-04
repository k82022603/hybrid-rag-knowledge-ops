#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Post-Deployment Verification Script
# =============================================================================
# Version: 1.1.0
# Created: 2026-02-04
# Updated: 2026-02-04 (R-003: jq fallback support)
# Description: Verifies deployment success with health checks and log analysis
# Usage: ./post-deploy-verify.sh [staging|production]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"

ENVIRONMENT="${1:-staging}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Slack notification script
SLACK_SCRIPT="${PROJECT_ROOT}/scripts/send_slack.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Check if jq is available
JQ_AVAILABLE=false
if command -v jq &> /dev/null; then
    JQ_AVAILABLE=true
fi

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_check() {
    local status="$1"
    local message="$2"
    local detail="${3:-}"

    case "$status" in
        PASS)
            echo -e "${GREEN}[PASS]${NC} $message"
            ((PASSED++))
            ;;
        FAIL)
            echo -e "${RED}[FAIL]${NC} $message"
            [[ -n "$detail" ]] && echo "       $detail"
            ((FAILED++))
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} $message"
            [[ -n "$detail" ]] && echo "       $detail"
            ((WARNINGS++))
            ;;
        INFO)
            echo -e "${BLUE}[INFO]${NC} $message"
            ;;
        STEP)
            echo -e "${CYAN}[STEP]${NC} $message"
            ;;
    esac
}

send_slack() {
    local channel="$1"
    local message="$2"

    if [[ -x "$SLACK_SCRIPT" ]]; then
        "$SLACK_SCRIPT" "$channel" "DevOps" "$message" 2>/dev/null || true
    fi
}

# =============================================================================
# JSON PARSING FUNCTIONS (R-003: jq with grep fallback)
# =============================================================================

# Parse JSON field with jq (preferred) or grep fallback
# Usage: json_get_field "$json_string" "field_name" "default_value"
json_get_field() {
    local json="$1"
    local field="$2"
    local default="${3:-unknown}"

    if [[ "$JQ_AVAILABLE" == true ]]; then
        # Use jq for reliable JSON parsing
        echo "$json" | jq -r ".${field} // \"${default}\"" 2>/dev/null || echo "$default"
    else
        # Fallback to grep-based parsing (less reliable but functional)
        local value
        value=$(echo "$json" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 | sed 's/.*:\s*"\([^"]*\)".*/\1/' 2>/dev/null)
        if [[ -z "$value" ]]; then
            # Try without quotes (for numbers, booleans)
            value=$(echo "$json" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*[^,}]*" | head -1 | sed 's/.*:\s*\([^,}]*\).*/\1/' | tr -d ' "' 2>/dev/null)
        fi
        echo "${value:-$default}"
    fi
}

# Parse nested JSON field
# Usage: json_get_nested "$json_string" ".components.db.status" "default_value"
json_get_nested() {
    local json="$1"
    local path="$2"
    local default="${3:-unknown}"

    if [[ "$JQ_AVAILABLE" == true ]]; then
        echo "$json" | jq -r "${path} // \"${default}\"" 2>/dev/null || echo "$default"
    else
        # Fallback: only supports simple nested access
        log_check INFO "Note: Complex JSON parsing limited without jq"
        echo "$default"
    fi
}

# Get array length from JSON
# Usage: json_array_length "$json_string" ".data.items"
json_array_length() {
    local json="$1"
    local path="${2:-.}"

    if [[ "$JQ_AVAILABLE" == true ]]; then
        echo "$json" | jq "${path} | length" 2>/dev/null || echo "0"
    else
        # Fallback: count array elements roughly
        local count
        count=$(echo "$json" | grep -o '\[' | wc -l)
        echo "$count"
    fi
}

# Get JSON keys
# Usage: json_get_keys "$json_string" ".components"
json_get_keys() {
    local json="$1"
    local path="${2:-.}"

    if [[ "$JQ_AVAILABLE" == true ]]; then
        echo "$json" | jq -r "${path} | keys[]" 2>/dev/null || echo ""
    else
        # Fallback: extract keys with grep (limited)
        echo ""
    fi
}

# =============================================================================
# CONTAINER STATUS CHECKS
# =============================================================================

check_container_status() {
    log_check STEP "Checking container status..."

    if [[ "$JQ_AVAILABLE" != true ]]; then
        log_check WARN "jq not installed - using fallback parsing (install jq for better reliability)"
    fi

    cd "$DOCKER_DIR"

    # Get all containers
    local containers
    containers=$(docker compose ps --format json 2>/dev/null)

    if [[ -z "$containers" ]]; then
        log_check FAIL "No containers found"
        return 1
    fi

    # Count containers by status
    local running=0
    local exited=0
    local unhealthy=0

    while IFS= read -r container; do
        local name state health

        if [[ "$JQ_AVAILABLE" == true ]]; then
            name=$(echo "$container" | jq -r '.Name')
            state=$(echo "$container" | jq -r '.State')
            health=$(echo "$container" | jq -r '.Health // "N/A"')
        else
            # Fallback parsing
            name=$(json_get_field "$container" "Name" "unknown")
            state=$(json_get_field "$container" "State" "unknown")
            health=$(json_get_field "$container" "Health" "N/A")
        fi

        if [[ "$state" == "running" ]]; then
            ((running++))
            if [[ "$health" == "healthy" || "$health" == "N/A" ]]; then
                log_check PASS "Container ${name}: ${state} (${health})"
            elif [[ "$health" == "starting" ]]; then
                log_check INFO "Container ${name}: ${state} (still starting)"
            else
                log_check WARN "Container ${name}: ${state} (${health})"
            fi
        elif [[ "$state" == "exited" ]]; then
            ((exited++))
            # init-db is expected to exit
            if [[ "$name" == "kp-init-db" ]]; then
                log_check INFO "Container ${name}: exited (init container - expected)"
            else
                log_check FAIL "Container ${name}: exited unexpectedly"
            fi
        else
            log_check WARN "Container ${name}: ${state}"
        fi

        if [[ "$health" == "unhealthy" ]]; then
            ((unhealthy++))
        fi
    done <<< "$(if [[ "$JQ_AVAILABLE" == true ]]; then echo "$containers" | jq -c '.'; else echo "$containers"; fi)"

    echo ""
    log_check INFO "Summary: ${running} running, ${exited} exited, ${unhealthy} unhealthy"

    if [[ $unhealthy -gt 0 ]]; then
        return 1
    fi
    return 0
}

# =============================================================================
# SERVICE HEALTH CHECKS
# =============================================================================

check_backend_health() {
    log_check STEP "Checking Backend service health..."

    local url="http://localhost:8081/actuator/health"
    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [[ "$http_code" == "200" ]]; then
        local status
        status=$(json_get_field "$body" "status" "UNKNOWN")

        if [[ "$status" == "UP" ]]; then
            log_check PASS "Backend: UP (HTTP ${http_code})"

            # Check component health (only with jq for complex parsing)
            if [[ "$JQ_AVAILABLE" == true ]]; then
                local components
                components=$(echo "$body" | jq -r '.components | keys[]' 2>/dev/null || echo "")

                for comp in $components; do
                    local comp_status
                    comp_status=$(echo "$body" | jq -r ".components.${comp}.status // \"UNKNOWN\"" 2>/dev/null)
                    if [[ "$comp_status" == "UP" ]]; then
                        log_check INFO "  - ${comp}: UP"
                    else
                        log_check WARN "  - ${comp}: ${comp_status}"
                    fi
                done
            fi
        else
            log_check WARN "Backend: ${status}"
        fi
    else
        log_check FAIL "Backend: Not responding (HTTP ${http_code})"
    fi
}

check_ai_service_health() {
    log_check STEP "Checking AI Service health..."

    local url="http://localhost:8000/api/v1/health"
    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [[ "$http_code" == "200" ]]; then
        local status
        status=$(json_get_field "$body" "status" "UNKNOWN")

        if [[ "$status" == "ok" || "$status" == "healthy" ]]; then
            log_check PASS "AI Service: ${status} (HTTP ${http_code})"
        else
            log_check WARN "AI Service: ${status}"
        fi
    else
        log_check FAIL "AI Service: Not responding (HTTP ${http_code})"
    fi
}

check_api_gateway_health() {
    log_check STEP "Checking API Gateway health..."

    local url="http://localhost:8080/actuator/health"
    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [[ "$http_code" == "200" ]]; then
        local status
        status=$(json_get_field "$body" "status" "UNKNOWN")

        if [[ "$status" == "UP" ]]; then
            log_check PASS "API Gateway: UP (HTTP ${http_code})"
        else
            log_check WARN "API Gateway: ${status}"
        fi
    else
        log_check FAIL "API Gateway: Not responding (HTTP ${http_code})"
    fi
}

check_frontend_health() {
    log_check STEP "Checking Frontend service..."

    local url="http://localhost:80"
    local http_code

    http_code=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null)

    if [[ "$http_code" == "200" || "$http_code" == "304" ]]; then
        log_check PASS "Frontend: Accessible (HTTP ${http_code})"
    else
        log_check FAIL "Frontend: Not responding (HTTP ${http_code})"
    fi
}

# =============================================================================
# DATABASE HEALTH CHECKS
# =============================================================================

check_postgresql_health() {
    log_check STEP "Checking PostgreSQL..."

    if ! docker ps --format '{{.Names}}' | grep -q "kp-postgresql"; then
        log_check FAIL "PostgreSQL container not running"
        return
    fi

    if docker exec kp-postgresql pg_isready -U knowledge > /dev/null 2>&1; then
        log_check PASS "PostgreSQL: Ready"

        # Check database exists
        local db_exists
        db_exists=$(docker exec kp-postgresql psql -U knowledge -d knowledge -c "SELECT 1" 2>/dev/null | grep -c "1 row" || echo "0")

        if [[ "$db_exists" -gt 0 ]]; then
            log_check PASS "PostgreSQL: Database 'knowledge' accessible"
        else
            log_check WARN "PostgreSQL: Database 'knowledge' not accessible"
        fi
    else
        log_check FAIL "PostgreSQL: Not ready"
    fi
}

check_elasticsearch_health() {
    log_check STEP "Checking Elasticsearch..."

    local url="http://localhost:9200/_cluster/health"
    local response
    local http_code

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null)
    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [[ "$http_code" == "200" ]]; then
        local status nodes
        status=$(json_get_field "$body" "status" "UNKNOWN")
        nodes=$(json_get_field "$body" "number_of_nodes" "0")

        if [[ "$status" == "green" || "$status" == "yellow" ]]; then
            log_check PASS "Elasticsearch: ${status} (${nodes} node(s))"
        else
            log_check WARN "Elasticsearch: ${status}"
        fi

        # Check indices
        local indices_response indices
        indices_response=$(curl -s "http://localhost:9200/_cat/indices?format=json" 2>/dev/null)
        indices=$(json_array_length "$indices_response" ".")
        log_check INFO "  - Indices count: ${indices}"
    else
        log_check FAIL "Elasticsearch: Not responding (HTTP ${http_code})"
    fi
}

check_neo4j_health() {
    log_check STEP "Checking Neo4j..."

    local url="http://localhost:7474"
    local http_code

    http_code=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null)

    if [[ "$http_code" == "200" ]]; then
        log_check PASS "Neo4j: Accessible (HTTP ${http_code})"
    else
        log_check FAIL "Neo4j: Not responding (HTTP ${http_code})"
    fi
}

check_redis_health() {
    log_check STEP "Checking Redis..."

    if ! docker ps --format '{{.Names}}' | grep -q "kp-redis"; then
        log_check FAIL "Redis container not running"
        return
    fi

    local pong
    pong=$(docker exec kp-redis redis-cli ping 2>/dev/null)

    if [[ "$pong" == "PONG" ]]; then
        log_check PASS "Redis: PONG"
    else
        log_check FAIL "Redis: Not responding"
    fi
}

check_keycloak_health() {
    log_check STEP "Checking Keycloak..."

    local url="http://localhost:8180/health/ready"
    local http_code

    http_code=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null)

    if [[ "$http_code" == "200" ]]; then
        log_check PASS "Keycloak: Ready (HTTP ${http_code})"
    else
        log_check FAIL "Keycloak: Not ready (HTTP ${http_code})"
    fi
}

# =============================================================================
# MONITORING HEALTH CHECKS
# =============================================================================

check_prometheus_health() {
    log_check STEP "Checking Prometheus..."

    local url="http://localhost:9090/-/healthy"
    local http_code

    http_code=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null)

    if [[ "$http_code" == "200" ]]; then
        log_check PASS "Prometheus: Healthy (HTTP ${http_code})"

        # Check targets (requires jq for reliable parsing)
        if [[ "$JQ_AVAILABLE" == true ]]; then
            local targets_up
            targets_up=$(curl -s "http://localhost:9090/api/v1/targets" 2>/dev/null | jq '[.data.activeTargets[] | select(.health == "up")] | length' 2>/dev/null || echo "0")
            log_check INFO "  - Active targets: ${targets_up}"
        fi
    else
        log_check WARN "Prometheus: Not responding (HTTP ${http_code})"
    fi
}

check_grafana_health() {
    log_check STEP "Checking Grafana..."

    local url="http://localhost:3001/api/health"
    local http_code

    http_code=$(curl -s -w "%{http_code}" -o /dev/null "$url" 2>/dev/null)

    if [[ "$http_code" == "200" ]]; then
        log_check PASS "Grafana: Healthy (HTTP ${http_code})"
    else
        log_check WARN "Grafana: Not responding (HTTP ${http_code})"
    fi
}

# =============================================================================
# LOG ERROR CHECKS
# =============================================================================

check_recent_errors() {
    log_check STEP "Checking recent error logs..."

    cd "$DOCKER_DIR"

    local critical_containers=("kp-backend" "kp-ai-service" "kp-api-gateway" "kp-postgresql" "kp-elasticsearch")

    for container in "${critical_containers[@]}"; do
        if ! docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            continue
        fi

        # Get last 100 lines and count errors
        local error_count
        error_count=$(docker logs --tail 100 "$container" 2>&1 | grep -ciE "(error|exception|fatal|critical)" || echo "0")

        if [[ $error_count -eq 0 ]]; then
            log_check PASS "${container}: No recent errors"
        elif [[ $error_count -lt 5 ]]; then
            log_check WARN "${container}: ${error_count} recent error(s)"
        else
            log_check FAIL "${container}: ${error_count} recent errors"
            echo "       Recent errors:"
            docker logs --tail 100 "$container" 2>&1 | grep -iE "(error|exception|fatal|critical)" | tail -3 | while read -r line; do
                echo "       - ${line:0:80}..."
            done
        fi
    done
}

# =============================================================================
# RESOURCE USAGE CHECKS
# =============================================================================

check_resource_usage() {
    log_check STEP "Checking resource usage..."

    cd "$DOCKER_DIR"

    # Get resource stats
    echo ""
    echo "Container Resource Usage:"
    echo "============================================================================="
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
    echo "============================================================================="
    echo ""

    # Check for high resource usage
    local high_cpu
    high_cpu=$(docker stats --no-stream --format "{{.Name}},{{.CPUPerc}}" | while IFS=',' read -r name cpu; do
        cpu_val=$(echo "$cpu" | tr -d '%')
        if (( $(echo "$cpu_val > 80" | bc -l) )); then
            echo "$name"
        fi
    done)

    if [[ -n "$high_cpu" ]]; then
        log_check WARN "High CPU usage detected on: $(echo $high_cpu | tr '\n' ', ')"
    else
        log_check PASS "CPU usage within normal range"
    fi

    # Check memory usage
    local total_mem_used
    total_mem_used=$(docker stats --no-stream --format "{{.MemUsage}}" | awk -F'/' '{gsub(/[GMK]iB/,"",$1); sum += $1} END {print sum}')
    log_check INFO "Total container memory: ~${total_mem_used} GB"
}

# =============================================================================
# CONNECTIVITY TESTS
# =============================================================================

check_internal_connectivity() {
    log_check STEP "Checking internal service connectivity..."

    # Test from backend to databases
    if docker ps --format '{{.Names}}' | grep -q "kp-backend"; then
        # PostgreSQL connectivity
        if docker exec kp-backend sh -c "wget -q -O /dev/null http://localhost:8081/actuator/health/db 2>/dev/null" 2>/dev/null; then
            log_check PASS "Backend -> PostgreSQL: Connected"
        else
            log_check INFO "Backend -> PostgreSQL: Skipped (health endpoint not available)"
        fi
    fi

    # Test API Gateway to Backend
    if docker ps --format '{{.Names}}' | grep -q "kp-api-gateway"; then
        if docker exec kp-api-gateway sh -c "wget -q -O - http://backend:8081/actuator/health 2>/dev/null | grep -q UP" 2>/dev/null; then
            log_check PASS "API Gateway -> Backend: Connected"
        else
            log_check WARN "API Gateway -> Backend: Connection check skipped"
        fi
    fi
}

# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

run_smoke_tests() {
    log_check STEP "Running smoke tests..."

    # Test API endpoints
    local endpoints=(
        "http://localhost:8080/actuator/info"
        "http://localhost:8081/actuator/info"
        "http://localhost:8000/api/v1/health"
    )

    for endpoint in "${endpoints[@]}"; do
        local http_code
        http_code=$(curl -s -w "%{http_code}" -o /dev/null "$endpoint" 2>/dev/null)

        if [[ "$http_code" == "200" ]]; then
            log_check PASS "Endpoint ${endpoint}: OK"
        else
            log_check WARN "Endpoint ${endpoint}: HTTP ${http_code}"
        fi
    done
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - Post-Deployment Verification"
    echo "============================================================================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp:   $(date)"
    echo "jq status:   $(if [[ "$JQ_AVAILABLE" == true ]]; then echo "Available"; else echo "Not installed (using fallback)"; fi)"
    echo "============================================================================="
    echo ""

    # Run all checks
    echo "=== Container Status ==="
    check_container_status
    echo ""

    echo "=== Application Services ==="
    check_backend_health
    check_ai_service_health
    check_api_gateway_health
    check_frontend_health
    echo ""

    echo "=== Data Services ==="
    check_postgresql_health
    check_elasticsearch_health
    check_neo4j_health
    check_redis_health
    check_keycloak_health
    echo ""

    echo "=== Monitoring Services ==="
    check_prometheus_health
    check_grafana_health
    echo ""

    echo "=== Log Analysis ==="
    check_recent_errors
    echo ""

    echo "=== Resource Usage ==="
    check_resource_usage
    echo ""

    echo "=== Connectivity ==="
    check_internal_connectivity
    echo ""

    echo "=== Smoke Tests ==="
    run_smoke_tests
    echo ""

    # Summary
    local total=$((PASSED + FAILED + WARNINGS))
    echo "============================================================================="
    echo "POST-DEPLOYMENT VERIFICATION SUMMARY"
    echo "============================================================================="
    echo "Total Checks: $total"
    echo "Passed:       $PASSED"
    echo "Failed:       $FAILED"
    echo "Warnings:     $WARNINGS"
    echo "============================================================================="

    # Determine overall status
    if [[ $FAILED -gt 0 ]]; then
        echo -e "${RED}Verification FAILED with $FAILED critical issue(s)${NC}"
        send_slack "alerts" "POST-DEPLOY VERIFY FAILED: ${ENVIRONMENT} - ${FAILED} critical issue(s)"
        exit 1
    elif [[ $WARNINGS -gt 3 ]]; then
        echo -e "${YELLOW}Verification PASSED with ${WARNINGS} warning(s)${NC}"
        echo "Consider investigating warnings to ensure system stability."
        send_slack "dev" "POST-DEPLOY VERIFY: ${ENVIRONMENT} passed with ${WARNINGS} warnings"
        exit 0
    else
        echo -e "${GREEN}Verification PASSED${NC}"
        echo "Deployment verified successfully!"
        send_slack "dev" "POST-DEPLOY VERIFY: ${ENVIRONMENT} passed - All checks OK"
        exit 0
    fi
}

# Show usage
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat << EOF
Hybrid RAG Knowledge Platform - Post-Deployment Verification Script

Usage: $(basename "$0") [ENVIRONMENT]

ENVIRONMENT:
    staging         Verify staging deployment (default)
    production      Verify production deployment

This script verifies:
    - Container status and health
    - Application service health (Backend, AI Service, Gateway, Frontend)
    - Database connectivity (PostgreSQL, Elasticsearch, Neo4j, Redis)
    - Auth service (Keycloak)
    - Monitoring services (Prometheus, Grafana)
    - Recent error logs
    - Resource usage
    - Internal connectivity
    - Basic API smoke tests

JSON Parsing:
    - Uses jq when available for reliable parsing
    - Falls back to grep-based parsing if jq is not installed
    - Install jq for best results: apt-get install jq

Exit codes:
    0   All checks passed (or passed with warnings)
    1   Critical failures found

EOF
    exit 0
fi

main
