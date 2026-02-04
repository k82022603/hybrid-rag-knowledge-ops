#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Pre-Deployment Check Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Description: Validates system requirements before deployment
# Usage: ./pre-deploy-check.sh [staging|production]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"

ENVIRONMENT="${1:-staging}"

# Minimum requirements
MIN_DISK_GB=20
MIN_MEMORY_GB=8
MIN_CPU_CORES=2

# Required ports
REQUIRED_PORTS=(80 443 8080 8081 8000 5432 9200 7474 7687 6379 9000 8180 9090 3001 3100 16686 5601)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Track failures
WARNINGS=0
ERRORS=0

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log_check() {
    local status="$1"
    local message="$2"
    local detail="${3:-}"

    case "$status" in
        PASS)  echo -e "${GREEN}[PASS]${NC} $message" ;;
        FAIL)  echo -e "${RED}[FAIL]${NC} $message"; [[ -n "$detail" ]] && echo "       $detail" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $message"; [[ -n "$detail" ]] && echo "       $detail" ;;
        INFO)  echo -e "${BLUE}[INFO]${NC} $message" ;;
    esac
}

# =============================================================================
# SYSTEM CHECKS
# =============================================================================

check_disk_space() {
    log_check INFO "Checking disk space..."

    local available_gb
    available_gb=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')

    if [[ $available_gb -lt $MIN_DISK_GB ]]; then
        log_check FAIL "Insufficient disk space: ${available_gb}GB available (minimum: ${MIN_DISK_GB}GB)"
        ((ERRORS++))
    else
        log_check PASS "Disk space: ${available_gb}GB available (minimum: ${MIN_DISK_GB}GB)"
    fi
}

check_memory() {
    log_check INFO "Checking memory..."

    local total_memory_gb
    total_memory_gb=$(free -g | awk '/^Mem:/ {print $2}')

    local available_memory_gb
    available_memory_gb=$(free -g | awk '/^Mem:/ {print $7}')

    if [[ $total_memory_gb -lt $MIN_MEMORY_GB ]]; then
        log_check FAIL "Insufficient memory: ${total_memory_gb}GB total (minimum: ${MIN_MEMORY_GB}GB)"
        ((ERRORS++))
    else
        log_check PASS "Memory: ${total_memory_gb}GB total, ${available_memory_gb}GB available"
    fi

    # Check if there's enough free memory
    if [[ $available_memory_gb -lt 4 ]]; then
        log_check WARN "Low available memory: ${available_memory_gb}GB free"
        ((WARNINGS++))
    fi
}

check_cpu() {
    log_check INFO "Checking CPU..."

    local cpu_cores
    cpu_cores=$(nproc)

    if [[ $cpu_cores -lt $MIN_CPU_CORES ]]; then
        log_check FAIL "Insufficient CPU cores: ${cpu_cores} (minimum: ${MIN_CPU_CORES})"
        ((ERRORS++))
    else
        log_check PASS "CPU cores: ${cpu_cores} (minimum: ${MIN_CPU_CORES})"
    fi

    # Check CPU load
    local load_avg
    load_avg=$(cat /proc/loadavg | awk '{print $1}')
    local load_threshold=$cpu_cores

    if (( $(echo "$load_avg > $load_threshold" | bc -l) )); then
        log_check WARN "High CPU load: ${load_avg} (threshold: ${load_threshold})"
        ((WARNINGS++))
    else
        log_check PASS "CPU load: ${load_avg}"
    fi
}

# =============================================================================
# DOCKER CHECKS
# =============================================================================

check_docker() {
    log_check INFO "Checking Docker..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_check FAIL "Docker is not installed"
        ((ERRORS++))
        return
    fi

    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        log_check FAIL "Docker daemon is not running"
        ((ERRORS++))
        return
    fi

    # Get Docker version
    local docker_version
    docker_version=$(docker version --format '{{.Server.Version}}' 2>/dev/null || echo "unknown")

    log_check PASS "Docker version: ${docker_version}"

    # Check Docker Compose
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        local compose_version
        compose_version=$(docker compose version --short 2>/dev/null || echo "unknown")
        log_check PASS "Docker Compose version: ${compose_version}"
    else
        log_check FAIL "Docker Compose is not available"
        ((ERRORS++))
    fi

    # Check Docker disk usage
    local docker_disk_usage
    docker_disk_usage=$(docker system df --format '{{.Size}}' | head -1)
    log_check INFO "Docker disk usage: ${docker_disk_usage}"
}

check_docker_volumes() {
    log_check INFO "Checking Docker volumes..."

    local required_volumes=(
        "kp-postgresql-data"
        "kp-elasticsearch-data"
        "kp-neo4j-data"
        "kp-redis-data"
        "kp-minio-data"
    )

    local missing_volumes=0

    for vol in "${required_volumes[@]}"; do
        if docker volume ls -q | grep -q "^${vol}$"; then
            log_check PASS "Volume exists: ${vol}"
        else
            log_check INFO "Volume will be created: ${vol}"
        fi
    done
}

# =============================================================================
# PORT CHECKS
# =============================================================================

check_ports() {
    log_check INFO "Checking required ports..."

    local ports_in_use=0

    for port in "${REQUIRED_PORTS[@]}"; do
        if ss -tuln | grep -q ":${port} "; then
            # Check if it's a Docker container using the port
            local container
            container=$(docker ps --format '{{.Names}}' --filter "publish=${port}" 2>/dev/null | head -1)

            if [[ -n "$container" ]]; then
                log_check INFO "Port ${port} in use by container: ${container}"
            else
                log_check WARN "Port ${port} is already in use (not by Docker)"
                ((WARNINGS++))
                ((ports_in_use++))
            fi
        fi
    done

    if [[ $ports_in_use -eq 0 ]]; then
        log_check PASS "All required ports are available"
    fi
}

# =============================================================================
# ENVIRONMENT CHECKS
# =============================================================================

check_environment_file() {
    log_check INFO "Checking environment configuration..."

    local env_file="${DOCKER_DIR}/.env.${ENVIRONMENT}"
    if [[ ! -f "$env_file" ]]; then
        env_file="${DOCKER_DIR}/.env"
    fi

    if [[ ! -f "$env_file" ]]; then
        log_check FAIL "Environment file not found: ${DOCKER_DIR}/.env or .env.${ENVIRONMENT}"
        ((ERRORS++))
        return
    fi

    log_check PASS "Environment file found: ${env_file}"

    # Check required variables
    local required_vars=(
        "DB_PASSWORD"
        "NEO4J_PASSWORD"
        "MINIO_ACCESS_KEY"
        "MINIO_SECRET_KEY"
        "KEYCLOAK_DB_PASSWORD"
        "KEYCLOAK_ADMIN_PASSWORD"
        "JWT_SECRET"
    )

    local missing_vars=0

    for var in "${required_vars[@]}"; do
        if grep -q "^${var}=" "$env_file" && ! grep -q "^${var}=$" "$env_file"; then
            log_check PASS "Variable set: ${var}"
        else
            log_check FAIL "Variable missing or empty: ${var}"
            ((missing_vars++))
            ((ERRORS++))
        fi
    done

    # Check optional but recommended variables
    local recommended_vars=(
        "DEEPSEEK_API_KEY"
        "GRAFANA_ADMIN_PASSWORD"
    )

    for var in "${recommended_vars[@]}"; do
        if grep -q "^${var}=" "$env_file" && ! grep -q "^${var}=$" "$env_file"; then
            log_check PASS "Variable set: ${var}"
        else
            log_check WARN "Recommended variable missing: ${var}"
            ((WARNINGS++))
        fi
    done

    # Check JWT_SECRET length
    local jwt_secret
    jwt_secret=$(grep "^JWT_SECRET=" "$env_file" | cut -d'=' -f2 | tr -d '"' | tr -d "'")
    if [[ ${#jwt_secret} -lt 32 ]]; then
        log_check WARN "JWT_SECRET should be at least 32 characters (current: ${#jwt_secret})"
        ((WARNINGS++))
    fi
}

check_compose_files() {
    log_check INFO "Checking Docker Compose files..."

    local compose_file="${DOCKER_DIR}/docker-compose.yml"

    if [[ ! -f "$compose_file" ]]; then
        log_check FAIL "Docker Compose file not found: ${compose_file}"
        ((ERRORS++))
        return
    fi

    log_check PASS "Docker Compose file exists"

    # Validate compose file syntax
    cd "$DOCKER_DIR"
    if docker compose config > /dev/null 2>&1; then
        log_check PASS "Docker Compose file syntax is valid"
    else
        log_check FAIL "Docker Compose file has syntax errors"
        ((ERRORS++))
    fi

    # Check for production override file
    if [[ "$ENVIRONMENT" == "production" ]]; then
        if [[ -f "${DOCKER_DIR}/docker-compose.prod.yml" ]]; then
            log_check PASS "Production override file exists"
        else
            log_check WARN "Production override file not found"
            ((WARNINGS++))
        fi
    fi
}

# =============================================================================
# NETWORK CHECKS
# =============================================================================

check_network() {
    log_check INFO "Checking network connectivity..."

    # Check DNS resolution
    if host google.com > /dev/null 2>&1; then
        log_check PASS "DNS resolution working"
    else
        log_check WARN "DNS resolution may have issues"
        ((WARNINGS++))
    fi

    # Check Docker Hub connectivity
    if curl -sf "https://registry.hub.docker.com/v2/" > /dev/null 2>&1; then
        log_check PASS "Docker Hub is reachable"
    else
        log_check WARN "Docker Hub may not be reachable"
        ((WARNINGS++))
    fi

    # Check GitHub connectivity (for pulling code)
    if curl -sf "https://github.com" > /dev/null 2>&1; then
        log_check PASS "GitHub is reachable"
    else
        log_check WARN "GitHub may not be reachable"
        ((WARNINGS++))
    fi
}

# =============================================================================
# GIT CHECKS
# =============================================================================

check_git() {
    log_check INFO "Checking Git status..."

    cd "$PROJECT_ROOT"

    # Check if it's a git repository
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        log_check FAIL "Not a Git repository"
        ((ERRORS++))
        return
    fi

    # Check for uncommitted changes
    if [[ -n "$(git status --porcelain)" ]]; then
        log_check WARN "Uncommitted changes detected"
        ((WARNINGS++))
    else
        log_check PASS "No uncommitted changes"
    fi

    # Check current branch
    local current_branch
    current_branch=$(git branch --show-current)
    local expected_branch="develop"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        expected_branch="main"
    fi

    if [[ "$current_branch" == "$expected_branch" ]]; then
        log_check PASS "On expected branch: ${current_branch}"
    else
        log_check WARN "Current branch (${current_branch}) differs from expected (${expected_branch})"
        ((WARNINGS++))
    fi

    # Check if branch is up to date with remote
    git fetch origin &> /dev/null
    local local_commit
    local_commit=$(git rev-parse HEAD)
    local remote_commit
    remote_commit=$(git rev-parse "origin/${current_branch}" 2>/dev/null || echo "unknown")

    if [[ "$local_commit" == "$remote_commit" ]]; then
        log_check PASS "Branch is up to date with origin"
    else
        log_check WARN "Branch is behind origin (local: ${local_commit:0:7}, remote: ${remote_commit:0:7})"
        ((WARNINGS++))
    fi
}

# =============================================================================
# EXISTING CONTAINERS CHECK
# =============================================================================

check_existing_containers() {
    log_check INFO "Checking existing containers..."

    cd "$DOCKER_DIR"

    local running_containers
    running_containers=$(docker compose ps -q 2>/dev/null | wc -l)

    if [[ $running_containers -gt 0 ]]; then
        log_check INFO "Found ${running_containers} running container(s)"

        # Show running containers
        echo ""
        docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        echo ""

        # Check for unhealthy containers
        local unhealthy
        unhealthy=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.Health == "unhealthy") | .Name' | wc -l)

        if [[ $unhealthy -gt 0 ]]; then
            log_check WARN "Found ${unhealthy} unhealthy container(s)"
            ((WARNINGS++))
        fi
    else
        log_check INFO "No running containers found (fresh deployment)"
    fi
}

# =============================================================================
# DATABASE CONNECTIVITY CHECK
# =============================================================================

check_database_connectivity() {
    log_check INFO "Checking database connectivity (if containers running)..."

    # PostgreSQL
    if docker ps --format '{{.Names}}' | grep -q "kp-postgresql"; then
        if docker exec kp-postgresql pg_isready -U knowledge > /dev/null 2>&1; then
            log_check PASS "PostgreSQL is ready"
        else
            log_check WARN "PostgreSQL container running but not ready"
            ((WARNINGS++))
        fi
    else
        log_check INFO "PostgreSQL container not running"
    fi

    # Elasticsearch
    if docker ps --format '{{.Names}}' | grep -q "kp-elasticsearch"; then
        if curl -sf "http://localhost:9200/_cluster/health" > /dev/null 2>&1; then
            log_check PASS "Elasticsearch is ready"
        else
            log_check WARN "Elasticsearch container running but not ready"
            ((WARNINGS++))
        fi
    else
        log_check INFO "Elasticsearch container not running"
    fi

    # Neo4j
    if docker ps --format '{{.Names}}' | grep -q "kp-neo4j"; then
        if curl -sf "http://localhost:7474" > /dev/null 2>&1; then
            log_check PASS "Neo4j is ready"
        else
            log_check WARN "Neo4j container running but not ready"
            ((WARNINGS++))
        fi
    else
        log_check INFO "Neo4j container not running"
    fi
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - Pre-Deployment Checks"
    echo "============================================================================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp:   $(date)"
    echo "============================================================================="
    echo ""

    # Run all checks
    echo "=== System Requirements ==="
    check_disk_space
    check_memory
    check_cpu
    echo ""

    echo "=== Docker Environment ==="
    check_docker
    check_docker_volumes
    echo ""

    echo "=== Network & Ports ==="
    check_ports
    check_network
    echo ""

    echo "=== Configuration ==="
    check_environment_file
    check_compose_files
    echo ""

    echo "=== Source Control ==="
    check_git
    echo ""

    echo "=== Existing State ==="
    check_existing_containers
    check_database_connectivity
    echo ""

    # Summary
    echo "============================================================================="
    echo "PRE-DEPLOYMENT CHECK SUMMARY"
    echo "============================================================================="
    echo "Errors:   $ERRORS"
    echo "Warnings: $WARNINGS"
    echo "============================================================================="

    if [[ $ERRORS -gt 0 ]]; then
        echo -e "${RED}Pre-deployment checks FAILED with $ERRORS error(s)${NC}"
        echo "Please fix the errors above before proceeding with deployment."
        exit 1
    elif [[ $WARNINGS -gt 0 ]]; then
        echo -e "${YELLOW}Pre-deployment checks PASSED with $WARNINGS warning(s)${NC}"
        echo "You may proceed with deployment, but consider addressing the warnings."
        exit 0
    else
        echo -e "${GREEN}Pre-deployment checks PASSED${NC}"
        echo "Ready for deployment."
        exit 0
    fi
}

# Show usage
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    cat << EOF
Hybrid RAG Knowledge Platform - Pre-Deployment Check Script

Usage: $(basename "$0") [ENVIRONMENT]

ENVIRONMENT:
    staging         Check for staging deployment (default)
    production      Check for production deployment

This script validates:
    - System resources (disk, memory, CPU)
    - Docker installation and daemon
    - Required ports availability
    - Environment configuration
    - Docker Compose file validity
    - Git repository status
    - Existing container state
    - Database connectivity (if running)

Exit codes:
    0   All checks passed (or passed with warnings)
    1   Critical errors found

EOF
    exit 0
fi

main
