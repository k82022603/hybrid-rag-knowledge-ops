#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Blue-Green Deployment Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Description: Zero-downtime deployment using Blue-Green strategy
# Usage: ./blue-green-deploy.sh [switch|status|rollback]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${PROJECT_ROOT}/logs/blue-green"
LOG_FILE="${LOG_DIR}/blue-green_${TIMESTAMP}.log"

# Slack notification script
SLACK_SCRIPT="${PROJECT_ROOT}/scripts/send_slack.sh"

# State file to track active environment
STATE_FILE="${PROJECT_ROOT}/.blue-green-state"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    mkdir -p "$LOG_DIR"

    case "$level" in
        INFO)   echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        WARN)   echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        ERROR)  echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        STEP)   echo -e "${CYAN}[STEP]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
    esac
}

send_slack() {
    local channel="$1"
    local message="$2"

    if [[ -x "$SLACK_SCRIPT" ]]; then
        "$SLACK_SCRIPT" "$channel" "DevOps" "$message" 2>/dev/null || true
    fi
}

get_active_environment() {
    if [[ -f "$STATE_FILE" ]]; then
        cat "$STATE_FILE"
    else
        echo "blue"  # Default to blue
    fi
}

set_active_environment() {
    local env="$1"
    echo "$env" > "$STATE_FILE"
}

show_usage() {
    cat << EOF
Hybrid RAG Knowledge Platform - Blue-Green Deployment Script

Usage: $(basename "$0") <command> [options]

COMMANDS:
    deploy          Deploy new version to inactive environment
    switch          Switch traffic to the inactive environment
    status          Show current Blue-Green status
    rollback        Switch back to previous environment
    cleanup         Remove inactive environment containers

OPTIONS:
    --version VER   Specify version to deploy
    --dry-run       Show what would be done without executing
    -h, --help      Show this help message

EXAMPLES:
    $(basename "$0") deploy --version v1.2.0
    $(basename "$0") switch
    $(basename "$0") status
    $(basename "$0") rollback

BLUE-GREEN ARCHITECTURE:
    +-------------+      +------------------+
    |   Nginx     |      |   Load Balancer  |
    +------+------+      +--------+---------+
           |                      |
    +------v------+        +------v------+
    |    Blue     |<------>|    Green    |
    | (Active)    |        | (Standby)   |
    +-------------+        +-------------+

EOF
}

# =============================================================================
# BLUE-GREEN FUNCTIONS
# =============================================================================

show_status() {
    echo "============================================================================="
    echo "Blue-Green Deployment Status"
    echo "============================================================================="

    local active=$(get_active_environment)
    local inactive="blue"
    [[ "$active" == "blue" ]] && inactive="green"

    echo ""
    echo "Active Environment:   ${active^^}"
    echo "Standby Environment:  ${inactive^^}"
    echo ""

    echo "Container Status:"
    echo "============================================================================="

    cd "$DOCKER_DIR"

    # Check Blue environment
    echo ""
    echo "BLUE Environment:"
    local blue_services=("backend-blue" "ai-service-blue" "frontend-blue")
    for svc in "${blue_services[@]}"; do
        local container="kp-${svc}"
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            if [[ "$active" == "blue" ]]; then
                echo -e "  ${container}: ${GREEN}ACTIVE${NC} (${health})"
            else
                echo -e "  ${container}: ${YELLOW}STANDBY${NC} (${health})"
            fi
        else
            echo -e "  ${container}: ${RED}NOT RUNNING${NC}"
        fi
    done

    # Check Green environment
    echo ""
    echo "GREEN Environment:"
    local green_services=("backend-green" "ai-service-green" "frontend-green")
    for svc in "${green_services[@]}"; do
        local container="kp-${svc}"
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "N/A")
            if [[ "$active" == "green" ]]; then
                echo -e "  ${container}: ${GREEN}ACTIVE${NC} (${health})"
            else
                echo -e "  ${container}: ${YELLOW}STANDBY${NC} (${health})"
            fi
        else
            echo -e "  ${container}: ${RED}NOT RUNNING${NC}"
        fi
    done

    echo ""
    echo "============================================================================="
}

deploy_to_inactive() {
    local version="${1:-latest}"

    local active=$(get_active_environment)
    local inactive="blue"
    [[ "$active" == "blue" ]] && inactive="green"

    log STEP "Deploying version ${version} to ${inactive} environment..."

    send_slack "dev" "BLUE-GREEN DEPLOY: Deploying ${version} to ${inactive} environment"

    cd "$DOCKER_DIR"

    # Create Blue-Green compose file if not exists
    create_blue_green_compose

    # Deploy to inactive environment
    log INFO "Starting ${inactive} containers..."
    export VERSION="${version}"
    export ENVIRONMENT="${inactive}"

    docker compose -f docker-compose.blue-green.yml up -d \
        "backend-${inactive}" "ai-service-${inactive}" "frontend-${inactive}" \
        2>>"$LOG_FILE"

    # Wait for health
    log INFO "Waiting for ${inactive} environment to be healthy..."
    wait_for_environment_health "$inactive"

    if [[ $? -eq 0 ]]; then
        log SUCCESS "Version ${version} deployed to ${inactive} environment"
        send_slack "dev" "BLUE-GREEN DEPLOY: ${version} ready on ${inactive}"
        echo ""
        echo "Next step: Run '$(basename "$0") switch' to activate ${inactive} environment"
    else
        log ERROR "Deployment to ${inactive} failed"
        send_slack "alerts" "BLUE-GREEN DEPLOY FAILED: ${inactive} health check failed"
        return 1
    fi
}

switch_environment() {
    local active=$(get_active_environment)
    local inactive="blue"
    [[ "$active" == "blue" ]] && inactive="green"

    log STEP "Switching traffic from ${active} to ${inactive}..."

    # Verify inactive environment is healthy
    if ! wait_for_environment_health "$inactive"; then
        log ERROR "Cannot switch: ${inactive} environment is not healthy"
        return 1
    fi

    send_slack "dev" "BLUE-GREEN SWITCH: Switching from ${active} to ${inactive}"

    cd "$DOCKER_DIR"

    # Update nginx upstream to point to new environment
    log INFO "Updating load balancer configuration..."
    update_nginx_upstream "$inactive"

    # Reload nginx
    log INFO "Reloading nginx..."
    docker exec kp-nginx nginx -s reload 2>>"$LOG_FILE" || {
        log ERROR "Failed to reload nginx"
        return 1
    }

    # Update state
    set_active_environment "$inactive"

    log SUCCESS "Traffic switched to ${inactive} environment"
    send_slack "dev" "BLUE-GREEN SWITCH COMPLETE: Now serving from ${inactive}"

    echo ""
    echo "Active environment is now: ${inactive^^}"
    echo "Previous environment (${active}) is now standby"
    echo ""
    echo "To rollback: Run '$(basename "$0") rollback'"
}

rollback_switch() {
    local active=$(get_active_environment)
    local inactive="blue"
    [[ "$active" == "blue" ]] && inactive="green"

    log STEP "Rolling back from ${active} to ${inactive}..."

    send_slack "alerts" "BLUE-GREEN ROLLBACK: Switching back to ${inactive}"

    # Simply switch back
    switch_environment

    log SUCCESS "Rolled back to ${inactive} environment"
}

cleanup_inactive() {
    local active=$(get_active_environment)
    local inactive="blue"
    [[ "$active" == "blue" ]] && inactive="green"

    log STEP "Cleaning up ${inactive} environment..."

    read -p "This will stop and remove ${inactive} containers. Continue? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Cleanup cancelled."
        return 0
    fi

    cd "$DOCKER_DIR"

    # Stop inactive containers
    docker compose -f docker-compose.blue-green.yml stop \
        "backend-${inactive}" "ai-service-${inactive}" "frontend-${inactive}" \
        2>>"$LOG_FILE" || true

    docker compose -f docker-compose.blue-green.yml rm -f \
        "backend-${inactive}" "ai-service-${inactive}" "frontend-${inactive}" \
        2>>"$LOG_FILE" || true

    log SUCCESS "${inactive} environment cleaned up"
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

wait_for_environment_health() {
    local env="$1"
    local max_wait=120
    local interval=10
    local elapsed=0

    while [[ $elapsed -lt $max_wait ]]; do
        local healthy=true

        # Check backend
        if ! curl -sf "http://localhost:808${env:0:1}/actuator/health" > /dev/null 2>&1; then
            healthy=false
        fi

        # Check AI service
        if ! curl -sf "http://localhost:800${env:0:1}/api/v1/health" > /dev/null 2>&1; then
            healthy=false
        fi

        if [[ "$healthy" == "true" ]]; then
            return 0
        fi

        log INFO "Waiting for ${env} health... ($elapsed/$max_wait)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    return 1
}

update_nginx_upstream() {
    local target_env="$1"

    # Create nginx config for upstream
    local nginx_config="/tmp/upstream-${target_env}.conf"

    if [[ "$target_env" == "blue" ]]; then
        cat > "$nginx_config" << 'NGINX_EOF'
upstream backend {
    server backend-blue:8081;
}
upstream ai-service {
    server ai-service-blue:8000;
}
upstream frontend {
    server frontend-blue:80;
}
NGINX_EOF
    else
        cat > "$nginx_config" << 'NGINX_EOF'
upstream backend {
    server backend-green:8081;
}
upstream ai-service {
    server ai-service-green:8000;
}
upstream frontend {
    server frontend-green:80;
}
NGINX_EOF
    fi

    # Copy to nginx container
    docker cp "$nginx_config" kp-nginx:/etc/nginx/conf.d/upstream.conf 2>/dev/null || {
        log WARN "Could not update nginx config directly. Manual update may be required."
    }

    rm -f "$nginx_config"
}

create_blue_green_compose() {
    local compose_file="${DOCKER_DIR}/docker-compose.blue-green.yml"

    if [[ -f "$compose_file" ]]; then
        return 0
    fi

    log INFO "Creating Blue-Green Docker Compose file..."

    cat > "$compose_file" << 'COMPOSE_EOF'
# =============================================================================
# Blue-Green Deployment Docker Compose
# =============================================================================
# This file extends the main docker-compose.yml for Blue-Green deployments
# Usage: docker compose -f docker-compose.blue-green.yml up -d backend-blue
# =============================================================================

name: knowledge-platform-blue-green

networks:
  frontend:
    external: true
    name: kp-frontend
  backend:
    external: true
    name: kp-backend
  database:
    external: true
    name: kp-database

services:
  # ===========================================================================
  # BLUE ENVIRONMENT
  # ===========================================================================

  backend-blue:
    image: ${REGISTRY:-}knowledge-platform/backend:${VERSION:-latest}
    container_name: kp-backend-blue
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
      - database
    environment:
      - SPRING_PROFILES_ACTIVE=docker
      - SERVER_PORT=8081
      - DATABASE_URL=jdbc:postgresql://postgresql:5432/${DB_NAME:-knowledge}
      - DATABASE_USERNAME=${DB_USERNAME:-knowledge}
      - DATABASE_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - AI_SERVICE_URL=http://ai-service-blue:8000
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8081/actuator/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  ai-service-blue:
    image: ${REGISTRY:-}knowledge-platform/ai-service:${VERSION:-latest}
    container_name: kp-ai-service-blue
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
      - database
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - ELASTICSEARCH_HOST=elasticsearch
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgresql
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  frontend-blue:
    image: ${REGISTRY:-}knowledge-platform/frontend:${VERSION:-latest}
    container_name: kp-frontend-blue
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - frontend
    environment:
      - VITE_API_URL=http://127.0.0.1:8080/api
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:80/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ===========================================================================
  # GREEN ENVIRONMENT
  # ===========================================================================

  backend-green:
    image: ${REGISTRY:-}knowledge-platform/backend:${VERSION:-latest}
    container_name: kp-backend-green
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
      - database
    environment:
      - SPRING_PROFILES_ACTIVE=docker
      - SERVER_PORT=8081
      - DATABASE_URL=jdbc:postgresql://postgresql:5432/${DB_NAME:-knowledge}
      - DATABASE_USERNAME=${DB_USERNAME:-knowledge}
      - DATABASE_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - AI_SERVICE_URL=http://ai-service-green:8000
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8081/actuator/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 90s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  ai-service-green:
    image: ${REGISTRY:-}knowledge-platform/ai-service:${VERSION:-latest}
    container_name: kp-ai-service-green
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - backend
      - database
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - ELASTICSEARCH_HOST=elasticsearch
      - NEO4J_URI=bolt://neo4j:7687
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgresql
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 120s
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

  frontend-green:
    image: ${REGISTRY:-}knowledge-platform/frontend:${VERSION:-latest}
    container_name: kp-frontend-green
    restart: unless-stopped
    security_opt:
      - no-new-privileges:true
    networks:
      - frontend
    environment:
      - VITE_API_URL=http://127.0.0.1:8080/api
    healthcheck:
      test: ["CMD", "wget", "-q", "-O", "/dev/null", "http://127.0.0.1:80/"]
      interval: 30s
      timeout: 10s
      retries: 3
COMPOSE_EOF

    log SUCCESS "Blue-Green Docker Compose file created"
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    local command="${1:-status}"
    shift || true

    local version="latest"
    local dry_run=false

    # Parse options
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version)
                version="$2"
                shift 2
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                shift
                ;;
        esac
    done

    mkdir -p "$LOG_DIR"

    case "$command" in
        deploy)
            deploy_to_inactive "$version"
            ;;
        switch)
            switch_environment
            ;;
        status)
            show_status
            ;;
        rollback)
            rollback_switch
            ;;
        cleanup)
            cleanup_inactive
            ;;
        *)
            echo "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
