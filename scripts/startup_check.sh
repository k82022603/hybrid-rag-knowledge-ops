#!/bin/bash
# ============================================================================
# Hybrid RAG Knowledge Platform - Startup & Health Check
# ============================================================================
#
# Usage: bash scripts/startup_check.sh [--skip-compose] [--verbose]
#
# --skip-compose : docker-compose up 건너뛰기 (이미 기동된 상태에서 점검만)
# --verbose      : 상세 로그 출력
#
# Phases:
#   1. 인프라 기동 + Health Check (DB 3종 + Redis)
#   2. 애플리케이션 서비스 기동 확인 (ai-service)
#   3. 검색 API 자동 테스트 (Keyword / Hybrid / Semantic)
#   4. Nori Analyzer 검증 (_analyze API)
#   5. 결과 리포트
#
# Created: 2026-02-18
# Author: Infra Agent
# ============================================================================

set -euo pipefail

# ============================================================================
# Constants & Colors
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_DIR="$PROJECT_ROOT/infrastructure/docker"

# Timeouts (seconds)
HEALTH_CHECK_TIMEOUT=120
API_TEST_TIMEOUT=30

# Counters
PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Options
SKIP_COMPOSE=false
VERBOSE=false

# ============================================================================
# Argument Parsing
# ============================================================================

for arg in "$@"; do
    case "$arg" in
        --skip-compose) SKIP_COMPOSE=true ;;
        --verbose)      VERBOSE=true ;;
        --help|-h)
            echo "Usage: $0 [--skip-compose] [--verbose]"
            echo ""
            echo "  --skip-compose  Skip docker-compose up (check only)"
            echo "  --verbose       Show detailed output"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--skip-compose] [--verbose]"
            exit 1
            ;;
    esac
done

# ============================================================================
# Utility Functions
# ============================================================================

log_info()    { echo -e "${BLUE}[INFO]${NC}    $1"; }
log_pass()    { echo -e "${GREEN}[PASS]${NC}    $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
log_fail()    { echo -e "${RED}[FAIL]${NC}    $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}    $1"; WARN_COUNT=$((WARN_COUNT + 1)); }
log_verbose() { if $VERBOSE; then echo -e "${CYAN}[DEBUG]${NC}   $1"; fi; }
log_header()  { echo ""; echo -e "${BOLD}$1${NC}"; echo "------------------------------------------------------------"; }

# Detect WSL2 environment
detect_wsl2() {
    grep -qEi "(Microsoft|WSL)" /proc/version 2>/dev/null
}

# Get docker compose command (with WSL2 override if applicable)
get_compose_cmd() {
    local cmd="docker compose -f docker-compose.yml"
    if detect_wsl2 && [[ -f "$COMPOSE_DIR/docker-compose.wsl2.yml" ]]; then
        cmd="$cmd -f docker-compose.wsl2.yml"
        log_verbose "WSL2 environment detected - applying WSL2 override"
    fi
    echo "$cmd"
}

# Wait for container health with timeout
# Usage: wait_for_health <container_name> <timeout_seconds>
wait_for_health() {
    local container="$1"
    local timeout="$2"
    local elapsed=0

    while [ $elapsed -lt "$timeout" ]; do
        local status
        status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "not_found")

        if [[ "$status" == "healthy" ]]; then
            return 0
        elif [[ "$status" == "not_found" ]]; then
            return 1
        fi

        log_verbose "$container: $status (${elapsed}s / ${timeout}s)"
        sleep 2
        elapsed=$((elapsed + 2))
    done

    return 1
}

# Curl with timeout, returns HTTP body (silent)
api_call() {
    local method="$1"
    local url="$2"
    local data="${3:-}"
    local token="${4:-}"
    local timeout="${5:-$API_TEST_TIMEOUT}"

    local -a curl_args=(-s --max-time "$timeout" -X "$method" "$url")
    curl_args+=(-H "Content-Type: application/json")

    if [[ -n "$token" ]]; then
        curl_args+=(-H "Authorization: Bearer $token")
    fi

    if [[ -n "$data" ]]; then
        curl_args+=(-d "$data")
    fi

    curl "${curl_args[@]}" 2>/dev/null || echo ""
}

# Get container health status (handles containers without healthcheck)
get_container_health() {
    local container="$1"
    local raw
    raw=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$container" 2>/dev/null || echo "n/a")
    # Strip whitespace/newlines
    echo "$raw" | tr -d '[:space:]'
}

# ============================================================================
# Phase 1: Infrastructure Startup + Health Check
# ============================================================================

phase1_infra() {
    log_header "Phase 1: Infrastructure Startup + Health Check"

    # --- Docker daemon check ---
    if ! docker info > /dev/null 2>&1; then
        log_fail "Docker daemon is not running"
        echo "       Start Docker Desktop and try again."
        exit 1
    fi
    log_pass "Docker daemon is running"

    # --- docker-compose.yml check ---
    if [[ ! -f "$COMPOSE_DIR/docker-compose.yml" ]]; then
        log_fail "docker-compose.yml not found at $COMPOSE_DIR"
        exit 1
    fi
    log_pass "docker-compose.yml found"

    # --- .env check ---
    if [[ ! -f "$COMPOSE_DIR/.env" ]]; then
        log_fail ".env file not found at $COMPOSE_DIR"
        exit 1
    fi
    log_pass ".env file found"

    # --- Start containers ---
    if ! $SKIP_COMPOSE; then
        log_info "Starting containers with docker-compose up -d ..."
        cd "$COMPOSE_DIR"
        local compose_cmd
        compose_cmd=$(get_compose_cmd)
        if $compose_cmd up -d 2>&1; then
            log_pass "docker-compose up -d completed"
        else
            log_fail "docker-compose up -d failed"
            exit 1
        fi
    else
        log_info "Skipping docker-compose up (--skip-compose)"
    fi

    # --- Health check: DB 3종 + Redis ---
    log_info "Waiting for infrastructure services (timeout: ${HEALTH_CHECK_TIMEOUT}s) ..."

    local infra_services=("kp-elasticsearch" "kp-postgresql" "kp-neo4j" "kp-redis")
    local all_healthy=true

    for container in "${infra_services[@]}"; do
        local running
        running=$(docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null || echo "false")

        if [[ "$running" != "true" ]]; then
            log_fail "$container is not running"
            all_healthy=false
            continue
        fi

        if wait_for_health "$container" "$HEALTH_CHECK_TIMEOUT"; then
            log_pass "$container is healthy"
        else
            local final_status
            final_status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")
            log_fail "$container health check timed out (status: $final_status)"
            all_healthy=false
        fi
    done

    # --- Redis PING ---
    local redis_pong
    redis_pong=$(docker exec kp-redis redis-cli ping 2>/dev/null || echo "")
    if [[ "$redis_pong" == "PONG" ]]; then
        log_pass "Redis PING -> PONG"
    else
        log_fail "Redis PING failed (got: $redis_pong)"
    fi

    if ! $all_healthy; then
        log_warn "Some infrastructure services are not healthy. Continuing with checks..."
    fi
}

# ============================================================================
# Phase 2: Application Service Startup
# ============================================================================

phase2_app() {
    log_header "Phase 2: Application Service Startup"

    # --- ai-service container status ---
    local ai_running
    ai_running=$(docker inspect --format='{{.State.Running}}' kp-ai-service 2>/dev/null || echo "false")
    if [[ "$ai_running" != "true" ]]; then
        log_fail "kp-ai-service is not running"
        return
    fi

    # --- Wait for ai-service health ---
    log_info "Waiting for ai-service health (timeout: ${HEALTH_CHECK_TIMEOUT}s) ..."
    if wait_for_health "kp-ai-service" "$HEALTH_CHECK_TIMEOUT"; then
        log_pass "kp-ai-service is healthy"
    else
        local ai_status
        ai_status=$(docker inspect --format='{{.State.Health.Status}}' kp-ai-service 2>/dev/null || echo "unknown")
        log_warn "kp-ai-service health check timed out (status: $ai_status)"
    fi

    # --- Health API check ---
    local health_resp
    health_resp=$(api_call GET "http://localhost:8000/api/v1/health" "" "" 15)

    if [[ -z "$health_resp" ]]; then
        log_fail "ai-service /api/v1/health returned empty response"
        return
    fi

    log_verbose "Health response: $health_resp"

    # --- Parse dependency statuses ---
    local deps_ok=true

    # Check ES connection
    local es_status
    es_status=$(echo "$health_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    deps = d.get('dependencies', d.get('services', {}))
    es = deps.get('elasticsearch', deps.get('es', {}))
    if isinstance(es, dict):
        print(es.get('status', es.get('connected', 'unknown')))
    else:
        print(es)
except: print('parse_error')
" 2>/dev/null || echo "parse_error")

    if [[ "$es_status" == "connected" || "$es_status" == "healthy" || "$es_status" == "True" || "$es_status" == "true" ]]; then
        log_pass "ai-service -> Elasticsearch: connected"
    else
        log_fail "ai-service -> Elasticsearch: $es_status"
        deps_ok=false
    fi

    # Check Neo4j connection
    local neo4j_status
    neo4j_status=$(echo "$health_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    deps = d.get('dependencies', d.get('services', {}))
    n = deps.get('neo4j', {})
    if isinstance(n, dict):
        print(n.get('status', n.get('connected', 'unknown')))
    else:
        print(n)
except: print('parse_error')
" 2>/dev/null || echo "parse_error")

    if [[ "$neo4j_status" == "connected" || "$neo4j_status" == "healthy" || "$neo4j_status" == "True" || "$neo4j_status" == "true" ]]; then
        log_pass "ai-service -> Neo4j: connected"
    else
        log_fail "ai-service -> Neo4j: $neo4j_status"
        deps_ok=false
    fi

    # Check PostgreSQL connection
    local pg_status
    pg_status=$(echo "$health_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    deps = d.get('dependencies', d.get('services', {}))
    p = deps.get('postgresql', deps.get('postgres', deps.get('pg', {})))
    if isinstance(p, dict):
        print(p.get('status', p.get('connected', 'unknown')))
    else:
        print(p)
except: print('parse_error')
" 2>/dev/null || echo "parse_error")

    if [[ "$pg_status" == "connected" || "$pg_status" == "healthy" || "$pg_status" == "True" || "$pg_status" == "true" ]]; then
        log_pass "ai-service -> PostgreSQL: connected"
    else
        log_fail "ai-service -> PostgreSQL: $pg_status"
        deps_ok=false
    fi

    # --- If dependencies failed, restart ai-service once ---
    if ! $deps_ok; then
        log_warn "Dependency connections failed. Restarting kp-ai-service (1 attempt)..."
        docker restart kp-ai-service >/dev/null 2>&1
        log_info "Waiting for ai-service restart (90s) ..."
        sleep 30

        if wait_for_health "kp-ai-service" 90; then
            log_pass "kp-ai-service restarted and healthy"
        else
            log_fail "kp-ai-service restart did not resolve health issues"
        fi
    fi
}

# ============================================================================
# Phase 3: Search API Tests
# ============================================================================

phase3_search() {
    log_header "Phase 3: Search API Tests"

    # --- JWT Login ---
    log_info "Authenticating (JWT login) ..."

    # IMPORTANT: Use temp file to avoid bash ! history expansion issues
    cat > /tmp/startup_check_login.json << 'ENDJSON'
{"email":"admin@example.com","password":"admin123!"}
ENDJSON

    local login_resp
    login_resp=$(curl -s --max-time "$API_TEST_TIMEOUT" \
        -X POST "http://localhost:8000/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d @/tmp/startup_check_login.json 2>/dev/null || echo "")
    rm -f /tmp/startup_check_login.json

    if [[ -z "$login_resp" ]]; then
        log_fail "Login API returned empty response"
        log_info "Skipping search tests (no auth token)"
        return
    fi

    log_verbose "Login response: ${login_resp:0:200}..."

    # Extract accessToken (camelCase)
    local token
    token=$(echo "$login_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('accessToken', d.get('access_token', '')))
except: print('')
" 2>/dev/null || echo "")

    if [[ -z "$token" ]]; then
        log_fail "Failed to extract accessToken from login response"
        log_verbose "Response was: $login_resp"
        log_info "Skipping search tests (no auth token)"
        return
    fi

    log_pass "JWT login successful (token acquired)"

    # --- Run search tests ---
    local search_failed=false

    run_search_test() {
        local search_type="$1"
        local endpoint="$2"
        local payload="$3"
        local auth_token="$4"

        local resp
        resp=$(api_call POST "$endpoint" "$payload" "$auth_token")

        if [[ -z "$resp" ]]; then
            log_fail "$search_type: empty response"
            return 1
        fi

        log_verbose "$search_type response: ${resp:0:300}..."

        local total
        total=$(echo "$resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('total', 0))
except: print(-1)
" 2>/dev/null || echo "-1")

        if [[ "$total" == "-1" ]]; then
            # Might be an error response
            local detail
            detail=$(echo "$resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('detail', d.get('message', 'unknown error')))
except: print('parse error')
" 2>/dev/null || echo "parse error")
            log_fail "$search_type: API error - $detail"
            return 1
        elif [[ "$total" -gt 0 ]]; then
            log_pass "$search_type: $total results found"
            return 0
        else
            log_fail "$search_type: 0 results (expected > 0)"
            return 1
        fi
    }

    # Keyword Search
    run_search_test "Keyword Search" \
        "http://localhost:8000/api/v1/search/keyword" \
        '{"query":"프로젝트 관리","top_k":5}' \
        "$token" || search_failed=true

    # Hybrid Search
    run_search_test "Hybrid Search" \
        "http://localhost:8000/api/v1/search/hybrid" \
        '{"query":"프로젝트 관리","top_k":5,"useGraph":true,"useVector":true}' \
        "$token" || search_failed=true

    # Semantic Search
    run_search_test "Semantic Search" \
        "http://localhost:8000/api/v1/search/semantic" \
        '{"query":"프로젝트 관리","top_k":5}' \
        "$token" || search_failed=true

    # --- If any search returned 0 results, flush Redis + restart ai-service ---
    if $search_failed; then
        log_warn "Search tests failed. Attempting recovery: Redis FLUSHALL + ai-service restart ..."

        # Redis FLUSHALL
        local flush_result
        flush_result=$(docker exec kp-redis redis-cli FLUSHALL 2>/dev/null || echo "FAILED")
        if [[ "$flush_result" == "OK" ]]; then
            log_info "Redis FLUSHALL: OK (stale cache cleared)"
        else
            log_warn "Redis FLUSHALL: $flush_result"
        fi

        # Restart ai-service
        docker restart kp-ai-service >/dev/null 2>&1
        log_info "Waiting for ai-service restart (60s) ..."
        sleep 30

        if wait_for_health "kp-ai-service" 60; then
            log_info "ai-service restarted. Re-running search tests ..."

            # Re-login after restart
            cat > /tmp/startup_check_login.json << 'ENDJSON'
{"email":"admin@example.com","password":"admin123!"}
ENDJSON
            login_resp=$(curl -s --max-time "$API_TEST_TIMEOUT" \
                -X POST "http://localhost:8000/api/v1/auth/login" \
                -H "Content-Type: application/json" \
                -d @/tmp/startup_check_login.json 2>/dev/null || echo "")
            rm -f /tmp/startup_check_login.json

            token=$(echo "$login_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('accessToken', d.get('access_token', '')))
except: print('')
" 2>/dev/null || echo "")

            if [[ -n "$token" ]]; then
                # Re-test (results logged but no second recovery attempt)
                run_search_test "Keyword Search (retry)" \
                    "http://localhost:8000/api/v1/search/keyword" \
                    '{"query":"프로젝트 관리","top_k":5}' \
                    "$token" || true

                run_search_test "Hybrid Search (retry)" \
                    "http://localhost:8000/api/v1/search/hybrid" \
                    '{"query":"프로젝트 관리","top_k":5,"useGraph":true,"useVector":true}' \
                    "$token" || true

                run_search_test "Semantic Search (retry)" \
                    "http://localhost:8000/api/v1/search/semantic" \
                    '{"query":"프로젝트 관리","top_k":5}' \
                    "$token" || true
            else
                log_fail "Re-login failed after restart"
            fi
        else
            log_fail "ai-service did not become healthy after restart"
        fi
    fi
}

# ============================================================================
# Phase 4: Nori Analyzer Verification
# ============================================================================

phase4_nori() {
    log_header "Phase 4: Nori Analyzer Verification"

    local test_text="프로젝트관리시스템구축"
    local analyze_resp

    # Call ES _analyze API with the text field analyzer
    analyze_resp=$(curl -s --max-time "$API_TEST_TIMEOUT" \
        -X POST "http://localhost:9200/knowledge_chunks/_analyze" \
        -H "Content-Type: application/json" \
        -d "{\"field\":\"text\",\"text\":\"$test_text\"}" 2>/dev/null || echo "")

    if [[ -z "$analyze_resp" ]]; then
        log_fail "Nori: ES _analyze API returned empty response"
        return
    fi

    log_verbose "Analyze response: ${analyze_resp:0:500}"

    # Count tokens
    local token_count
    token_count=$(echo "$analyze_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tokens = d.get('tokens', [])
    print(len(tokens))
except: print(-1)
" 2>/dev/null || echo "-1")

    # Extract token list for display
    local token_list
    token_list=$(echo "$analyze_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    tokens = [t['token'] for t in d.get('tokens', [])]
    print(' / '.join(tokens))
except: print('parse error')
" 2>/dev/null || echo "parse error")

    if [[ "$token_count" == "-1" ]]; then
        # Maybe index doesn't exist
        local error_type
        error_type=$(echo "$analyze_resp" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('error', {}).get('type', 'unknown'))
except: print('unknown')
" 2>/dev/null || echo "unknown")
        log_fail "Nori: _analyze failed (error: $error_type)"
        log_verbose "Full response: $analyze_resp"
    elif [[ "$token_count" -le 1 ]]; then
        log_warn "Nori: $token_count token(s) for '$test_text' -> standard analyzer (Nori NOT active)"
        log_info "       Tokens: $token_list"
        log_info "       Expected 4+ tokens: 프로젝트 / 관리 / 시스템 / 구축"
    elif [[ "$token_count" -ge 3 ]]; then
        log_pass "Nori: $token_count tokens for '$test_text' -> Nori analyzer active"
        log_info "       Tokens: $token_list"
    else
        log_warn "Nori: $token_count tokens for '$test_text' (ambiguous, check manually)"
        log_info "       Tokens: $token_list"
    fi
}

# ============================================================================
# Phase 5: Result Report
# ============================================================================

phase5_report() {
    log_header "Phase 5: Final Report"

    local total=$((PASS_COUNT + FAIL_COUNT + WARN_COUNT))

    echo ""
    echo -e "  ${GREEN}PASS${NC}: $PASS_COUNT"
    echo -e "  ${RED}FAIL${NC}: $FAIL_COUNT"
    echo -e "  ${YELLOW}WARN${NC}: $WARN_COUNT"
    echo -e "  --------"
    echo -e "  TOTAL: $total checks"
    echo ""

    # Container status summary
    echo -e "${BOLD}Container Status:${NC}"
    echo "------------------------------------------------------------"
    printf "  %-25s %-15s %s\n" "CONTAINER" "STATUS" "HEALTH"
    echo "  -------------------------------------------------------"

    local containers=("kp-elasticsearch" "kp-postgresql" "kp-neo4j" "kp-redis" "kp-ai-service" "kp-backend" "kp-api-gateway" "kp-frontend" "kp-nginx" "kp-keycloak" "kp-minio" "kp-kibana" "kp-prometheus" "kp-grafana" "kp-loki" "kp-promtail" "kp-jaeger" "kp-keycloak-db")

    for c in "${containers[@]}"; do
        local running
        running=$(docker inspect --format='{{.State.Running}}' "$c" 2>/dev/null || echo "not_found")
        running=$(echo "$running" | tr -d '[:space:]')

        local health
        health=$(get_container_health "$c")

        local status_color="$RED"
        local health_color="$RED"
        local status_text="stopped"

        if [[ "$running" == "true" ]]; then
            status_color="$GREEN"
            status_text="running"
        elif [[ "$running" == "not_found" ]]; then
            status_text="not found"
        fi

        if [[ "$health" == "healthy" ]]; then
            health_color="$GREEN"
        elif [[ "$health" == "starting" ]]; then
            health_color="$YELLOW"
        elif [[ "$health" == "n/a" || "$health" == "no_healthcheck" ]]; then
            health_color="$CYAN"
            health="no check"
        fi

        printf "  %-25s ${status_color}%-15s${NC} ${health_color}%s${NC}\n" "$c" "$status_text" "$health"
    done

    echo ""
    echo "------------------------------------------------------------"

    if [[ $FAIL_COUNT -eq 0 ]]; then
        echo -e "${GREEN}${BOLD}ALL CHECKS PASSED${NC} - Platform is ready!"
    elif [[ $FAIL_COUNT -le 2 ]]; then
        echo -e "${YELLOW}${BOLD}PARTIAL ISSUES DETECTED${NC} - Review warnings above."
    else
        echo -e "${RED}${BOLD}CRITICAL FAILURES DETECTED${NC} - Platform needs attention."
    fi
    echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
    echo ""
    echo "============================================================"
    echo "  Hybrid RAG Knowledge Platform - Startup Check"
    echo "  $(date '+%Y-%m-%d %H:%M:%S')"
    echo "============================================================"

    if detect_wsl2; then
        log_info "Environment: WSL2"
    else
        log_info "Environment: Linux/Other"
    fi

    if $SKIP_COMPOSE; then
        log_info "Mode: Health check only (--skip-compose)"
    else
        log_info "Mode: Full startup + health check"
    fi

    phase1_infra
    phase2_app
    phase3_search
    phase4_nori
    phase5_report

    # Exit code
    if [[ $FAIL_COUNT -gt 0 ]]; then
        exit 1
    fi
    exit 0
}

main
