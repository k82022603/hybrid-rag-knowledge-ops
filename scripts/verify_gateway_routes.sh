#!/bin/bash
# =============================================================================
# verify_gateway_routes.sh - Gateway Route Verification Script
# =============================================================================
# Compares Spring Cloud Gateway routes (application.yml) against
# AI Service (FastAPI) actual endpoints to detect missing routes.
#
# Background: On 2026-02-07, /api/v1/graph/** route was missing from Gateway,
# causing 500 errors. This script prevents such regressions.
#
# Usage:
#   ./scripts/verify_gateway_routes.sh                  # Interactive mode
#   ./scripts/verify_gateway_routes.sh --ci             # CI mode (exit code)
#   ./scripts/verify_gateway_routes.sh --verbose        # Verbose output
#   ./scripts/verify_gateway_routes.sh --fix-hint       # Show fix suggestions
#
# Exit codes:
#   0 - All AI Service route groups have Gateway routes
#   1 - Missing Gateway routes detected
#   2 - Configuration error (files not found)
# =============================================================================

set -euo pipefail

# ---- Configuration ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GATEWAY_YML="$PROJECT_ROOT/knowledge_service/gateway/src/main/resources/application.yml"
ROUTES_DIR="$PROJECT_ROOT/knowledge_service/src/app/api/routes"
ROUTES_INIT="$ROUTES_DIR/__init__.py"

CI_MODE=false
VERBOSE=false
FIX_HINT=false

# Routes that are intentionally NOT exposed through Gateway to AI Service.
# - auth: Handled by Backend (Gateway routes /api/v1/auth/** to Backend)
# - health: Internal AI Service health checks (root /health is used instead)
# - cache: Internal cache management (admin-only, not exposed)
# - extract: Internal ETL pipeline endpoints (called via Docker network)
# - embed: Internal embedding endpoints (called via Docker network)
#
# Override via GATEWAY_EXCLUDE_ROUTES env var (comma-separated):
#   GATEWAY_EXCLUDE_ROUTES="auth,health,cache" ./scripts/verify_gateway_routes.sh
DEFAULT_EXCLUDE="auth,health,cache,extract,embed"
EXCLUDE_ROUTES="${GATEWAY_EXCLUDE_ROUTES:-$DEFAULT_EXCLUDE}"

# ---- Parse arguments ----
for arg in "$@"; do
    case $arg in
        --ci)        CI_MODE=true ;;
        --verbose)   VERBOSE=true ;;
        --fix-hint)  FIX_HINT=true ;;
        --strict)    EXCLUDE_ROUTES="" ;;
        --help|-h)
            echo "Usage: $0 [--ci] [--verbose] [--fix-hint] [--strict]"
            echo ""
            echo "Options:"
            echo "  --ci        CI mode: suppress colors, return exit code only"
            echo "  --verbose   Show detailed route matching info"
            echo "  --fix-hint  Show suggested Gateway route YAML for missing routes"
            echo "  --strict    Check ALL routes (ignore exclusion list)"
            echo "  --help      Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  GATEWAY_EXCLUDE_ROUTES  Comma-separated list of route prefixes to exclude"
            echo "                          Default: $DEFAULT_EXCLUDE"
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            exit 2
            ;;
    esac
done

# ---- Color helpers ----
if [ "$CI_MODE" = true ]; then
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    BOLD=""
    RESET=""
else
    RED="\033[0;31m"
    GREEN="\033[0;32m"
    YELLOW="\033[1;33m"
    BLUE="\033[0;34m"
    BOLD="\033[1m"
    RESET="\033[0m"
fi

info()  { echo -e "${BLUE}[INFO]${RESET} $1"; }
ok()    { echo -e "${GREEN}[OK]${RESET} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $1"; }
fail()  { echo -e "${RED}[FAIL]${RESET} $1"; }

# ---- File checks ----
if [ ! -f "$GATEWAY_YML" ]; then
    fail "Gateway application.yml not found: $GATEWAY_YML"
    exit 2
fi

if [ ! -f "$ROUTES_INIT" ]; then
    fail "AI Service routes __init__.py not found: $ROUTES_INIT"
    exit 2
fi

if [ ! -d "$ROUTES_DIR" ]; then
    fail "AI Service routes directory not found: $ROUTES_DIR"
    exit 2
fi

echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD} Gateway Route Verification${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo ""

# =============================================================================
# Step 1: Extract AI Service route prefixes from __init__.py
# =============================================================================
info "Extracting AI Service route groups from __init__.py..."

# Parse: router.include_router(..., prefix="/xxx", ...)
AI_ROUTE_PREFIXES=()
while IFS= read -r line; do
    prefix=$(echo "$line" | grep -oP 'prefix="/\K[^"]+')
    if [ -n "$prefix" ]; then
        AI_ROUTE_PREFIXES+=("$prefix")
    fi
done < <(grep 'include_router' "$ROUTES_INIT" | grep 'prefix=')

if [ ${#AI_ROUTE_PREFIXES[@]} -eq 0 ]; then
    fail "No route prefixes found in $ROUTES_INIT"
    exit 2
fi

if [ "$VERBOSE" = true ]; then
    echo "  AI Service route groups:"
    for prefix in "${AI_ROUTE_PREFIXES[@]}"; do
        echo "    - /api/v1/$prefix/**"
    done
    echo ""
fi

# =============================================================================
# Step 2: Extract Gateway routes targeting AI Service
# =============================================================================
info "Extracting Gateway routes from application.yml..."

# We look for routes whose URI targets ai-service (either http://ai-service:8000
# or ${AI_SERVICE_URL:...}) and extract their Path predicates.
# We focus on the default (local) profile section, not the docker profile.

# Extract Path predicates from the entire file (both profiles have same routes)
GATEWAY_PATHS=()
while IFS= read -r path; do
    # Clean up the path pattern
    path=$(echo "$path" | sed 's/[[:space:]]*//g' | sed 's/,$//')
    if [ -n "$path" ]; then
        GATEWAY_PATHS+=("$path")
    fi
done < <(grep -E '^\s*- Path=' "$GATEWAY_YML" | sed 's/.*Path=//' | sort -u)

if [ ${#GATEWAY_PATHS[@]} -eq 0 ]; then
    fail "No Gateway route paths found in $GATEWAY_YML"
    exit 2
fi

if [ "$VERBOSE" = true ]; then
    echo "  Gateway route paths (unique):"
    for gpath in "${GATEWAY_PATHS[@]}"; do
        echo "    - $gpath"
    done
    echo ""
fi

# =============================================================================
# Step 3: Identify which Gateway routes target AI Service
# =============================================================================
info "Identifying AI Service-targeted Gateway routes..."

# Parse route blocks to map route-id -> uri -> path
# We consider a route as AI-Service-targeted if its URI contains "ai-service" or "8000"
AI_SERVICE_GATEWAY_PATHS=()
BACKEND_GATEWAY_PATHS=()

current_uri=""
while IFS= read -r line; do
    # Detect uri lines
    if echo "$line" | grep -qE '^\s*uri:'; then
        current_uri=$(echo "$line" | sed 's/.*uri:\s*//' | sed 's/[[:space:]]*$//')
    fi
    # Detect Path predicate lines
    if echo "$line" | grep -qE '^\s*- Path='; then
        path=$(echo "$line" | sed 's/.*Path=//' | sed 's/[[:space:]]*$//')
        if echo "$current_uri" | grep -qE 'ai-service|8000'; then
            AI_SERVICE_GATEWAY_PATHS+=("$path")
        else
            BACKEND_GATEWAY_PATHS+=("$path")
        fi
    fi
done < <(sed -n '1,/^---$/p' "$GATEWAY_YML")
# Only parse the first YAML document (local profile) to avoid double-counting

if [ "$VERBOSE" = true ]; then
    echo "  AI Service Gateway paths:"
    for gpath in "${AI_SERVICE_GATEWAY_PATHS[@]}"; do
        echo "    - $gpath"
    done
    echo "  Backend Gateway paths:"
    for gpath in "${BACKEND_GATEWAY_PATHS[@]}"; do
        echo "    - $gpath"
    done
    echo ""
fi

# =============================================================================
# Step 4: Compare AI Service routes vs Gateway routes
# =============================================================================
info "Comparing AI Service routes against Gateway configuration..."

# Parse exclusion list
IFS=',' read -ra EXCLUDED_PREFIXES <<< "$EXCLUDE_ROUTES"

if [ ${#EXCLUDED_PREFIXES[@]} -gt 0 ] && [ -n "${EXCLUDED_PREFIXES[0]}" ]; then
    info "Excluded (internal/intentional): ${EXCLUDED_PREFIXES[*]}"
fi
echo ""

MISSING_ROUTES=()
COVERED_ROUTES=()
EXCLUDED_LIST=()

is_excluded() {
    local prefix="$1"
    for excluded in "${EXCLUDED_PREFIXES[@]}"; do
        if [ "$prefix" = "$excluded" ]; then
            return 0
        fi
    done
    return 1
}

for prefix in "${AI_ROUTE_PREFIXES[@]}"; do
    full_path="/api/v1/${prefix}/**"

    # Check exclusion list first
    if is_excluded "$prefix"; then
        EXCLUDED_LIST+=("$prefix")
        if [ "$VERBOSE" = true ]; then
            info "/api/v1/${prefix}/** -> Excluded (internal/intentional)"
        fi
        continue
    fi

    found=false

    # Check if there's a dedicated Gateway route for this prefix
    for gpath in "${AI_SERVICE_GATEWAY_PATHS[@]}"; do
        normalized_gpath=$(echo "$gpath" | sed 's/\/\*\*$//')
        normalized_prefix="/api/v1/${prefix}"

        if [ "$normalized_gpath" = "$normalized_prefix" ]; then
            found=true
            break
        fi
    done

    if [ "$found" = true ]; then
        COVERED_ROUTES+=("$prefix")
        ok "/api/v1/${prefix}/** -> Dedicated AI Service Gateway route exists"
    else
        # Check if caught by catch-all /api/v1/** (which goes to Backend, NOT AI Service)
        has_catchall=false
        for gpath in "${BACKEND_GATEWAY_PATHS[@]}"; do
            if [ "$gpath" = "/api/v1/**" ]; then
                has_catchall=true
                break
            fi
        done

        if [ "$has_catchall" = true ]; then
            MISSING_ROUTES+=("$prefix")
            fail "/api/v1/${prefix}/** -> NO dedicated route! Falls through to Backend catch-all /api/v1/**"
        else
            MISSING_ROUTES+=("$prefix")
            fail "/api/v1/${prefix}/** -> NO Gateway route at all!"
        fi
    fi
done

# =============================================================================
# Step 5: Detailed endpoint listing for missing routes
# =============================================================================
if [ ${#MISSING_ROUTES[@]} -gt 0 ] && [ "$VERBOSE" = true ]; then
    echo ""
    info "Detailed endpoints in missing route groups:"
    for prefix in "${MISSING_ROUTES[@]}"; do
        route_file="$ROUTES_DIR/${prefix}.py"
        if [ -f "$route_file" ]; then
            echo -e "  ${BOLD}/api/v1/${prefix}${RESET}:"
            # Extract endpoint paths from @router decorators
            grep -E '@router\.(get|post|put|delete|patch)\(' "$route_file" -A1 | \
                grep -oP '^\s+"\K[^"]*(?=",?)' | while read -r endpoint; do
                    if [ -z "$endpoint" ]; then
                        echo "    - /api/v1/${prefix}"
                    else
                        echo "    - /api/v1/${prefix}${endpoint}"
                    fi
                done
        fi
    done
fi

# =============================================================================
# Step 6: Fix hints
# =============================================================================
if [ ${#MISSING_ROUTES[@]} -gt 0 ] && [ "$FIX_HINT" = true ]; then
    echo ""
    info "Suggested Gateway route YAML for missing routes:"
    echo ""
    for prefix in "${MISSING_ROUTES[@]}"; do
        route_id="${prefix}-service"
        cat <<YAML
        # ${prefix^} Service Routes (/api/v1/${prefix}/**)
        - id: ${route_id}
          uri: \${AI_SERVICE_URL:http://localhost:8000}
          predicates:
            - Path=/api/v1/${prefix}/**
          filters:
            - TokenRelay=
            - name: CircuitBreaker
              args:
                name: ai-service-circuit-breaker
                fallbackUri: forward:/fallback/ai-service
            - name: Retry
              args:
                retries: 2
                statuses: BAD_GATEWAY,GATEWAY_TIMEOUT
                methods: GET,POST
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 30
                redis-rate-limiter.burstCapacity: 60
                redis-rate-limiter.requestedTokens: 1

YAML
    done
    warn "Add these routes BEFORE the catch-all /api/v1/** route in application.yml"
fi

# =============================================================================
# Step 7: Summary
# =============================================================================
echo ""
echo -e "${BOLD}========================================${RESET}"
echo -e "${BOLD} Summary${RESET}"
echo -e "${BOLD}========================================${RESET}"
echo ""
echo "  AI Service route groups:  ${#AI_ROUTE_PREFIXES[@]}"
echo "  Covered by Gateway:       ${#COVERED_ROUTES[@]}"
echo "  Excluded (internal):      ${#EXCLUDED_LIST[@]}"
echo "  Missing Gateway routes:   ${#MISSING_ROUTES[@]}"
echo ""

if [ ${#MISSING_ROUTES[@]} -gt 0 ]; then
    warn "Missing routes: ${MISSING_ROUTES[*]}"
    echo ""
    warn "These AI Service endpoints will be routed to the Backend (catch-all /api/v1/**),"
    warn "causing 404 or 500 errors for callers."
    echo ""
    if [ "$FIX_HINT" = false ]; then
        info "Run with --fix-hint to see suggested Gateway route YAML."
    fi

    if [ "$CI_MODE" = true ]; then
        echo "RESULT: FAIL"
    fi
    exit 1
else
    ok "All AI Service route groups have dedicated Gateway routes."
    echo ""
    if [ "$CI_MODE" = true ]; then
        echo "RESULT: PASS"
    fi
    exit 0
fi
