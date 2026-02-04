#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Main Deployment Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Description: Automated deployment script with health checks and rollback
# Usage: ./deploy.sh [staging|production] [--dry-run] [--skip-backup]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"

# Default values
ENVIRONMENT="${1:-staging}"
DRY_RUN=false
SKIP_BACKUP=false
SKIP_TESTS=false
FORCE_DEPLOY=false

# Timestamp for logging
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${PROJECT_ROOT}/logs/deployments"
LOG_FILE="${LOG_DIR}/deploy_${ENVIRONMENT}_${TIMESTAMP}.log"

# Slack notification script
SLACK_SCRIPT="${PROJECT_ROOT}/scripts/send_slack.sh"

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

show_usage() {
    cat << EOF
Hybrid RAG Knowledge Platform - Deployment Script

Usage: $(basename "$0") [ENVIRONMENT] [OPTIONS]

ENVIRONMENT:
    staging         Deploy to staging environment (default)
    production      Deploy to production environment

OPTIONS:
    --dry-run       Show what would be done without executing
    --skip-backup   Skip pre-deployment backup
    --skip-tests    Skip post-deployment verification tests
    --force         Force deployment even if pre-checks fail
    -h, --help      Show this help message

EXAMPLES:
    $(basename "$0") staging
    $(basename "$0") production --skip-backup
    $(basename "$0") staging --dry-run

ENVIRONMENT VARIABLES:
    VERSION         Docker image version to deploy (default: latest)
    REGISTRY        Docker registry URL

EOF
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

validate_environment() {
    log INFO "Validating environment: $ENVIRONMENT"

    if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
        log ERROR "Invalid environment: $ENVIRONMENT. Use 'staging' or 'production'."
        exit 1
    fi

    # Check if docker-compose file exists
    local compose_file="${DOCKER_DIR}/docker-compose.yml"
    if [[ ! -f "$compose_file" ]]; then
        log ERROR "Docker compose file not found: $compose_file"
        exit 1
    fi

    # Check environment-specific config
    local env_file="${DOCKER_DIR}/.env.${ENVIRONMENT}"
    if [[ ! -f "$env_file" ]]; then
        log WARN "Environment file not found: $env_file"
        log INFO "Using default .env file"
        env_file="${DOCKER_DIR}/.env"
    fi

    if [[ ! -f "$env_file" && ! -f "${DOCKER_DIR}/.env" ]]; then
        log ERROR "No environment file found. Please create .env or .env.${ENVIRONMENT}"
        exit 1
    fi

    log SUCCESS "Environment validation passed"
}

# =============================================================================
# PRE-DEPLOYMENT CHECKS
# =============================================================================

run_pre_checks() {
    log STEP "[1/8] Running pre-deployment checks..."

    local pre_check_script="${SCRIPT_DIR}/pre-deploy-check.sh"

    if [[ -x "$pre_check_script" ]]; then
        if ! "$pre_check_script" "$ENVIRONMENT"; then
            if [[ "$FORCE_DEPLOY" == "true" ]]; then
                log WARN "Pre-deployment checks failed but --force flag is set. Continuing..."
            else
                log ERROR "Pre-deployment checks failed. Use --force to override."
                exit 1
            fi
        fi
    else
        log WARN "Pre-deployment check script not found. Skipping..."
    fi
}

# =============================================================================
# BACKUP
# =============================================================================

run_backup() {
    if [[ "$SKIP_BACKUP" == "true" ]]; then
        log INFO "Skipping backup (--skip-backup flag set)"
        return 0
    fi

    log STEP "[2/8] Creating pre-deployment backup..."

    local backup_script="${SCRIPT_DIR}/backup.sh"

    if [[ -x "$backup_script" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log INFO "[DRY-RUN] Would execute: $backup_script"
        else
            if "$backup_script" --dir "${PROJECT_ROOT}/backups/pre-deploy-${TIMESTAMP}"; then
                log SUCCESS "Backup completed successfully"
            else
                log ERROR "Backup failed"
                exit 1
            fi
        fi
    else
        log WARN "Backup script not found: $backup_script"
    fi
}

# =============================================================================
# GIT OPERATIONS
# =============================================================================

update_codebase() {
    log STEP "[3/8] Updating codebase..."

    local target_branch="develop"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        target_branch="main"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY-RUN] Would checkout and pull branch: $target_branch"
        return 0
    fi

    cd "$PROJECT_ROOT"

    # Stash any local changes
    if [[ -n "$(git status --porcelain)" ]]; then
        log INFO "Stashing local changes..."
        git stash push -m "Auto-stash before deployment ${TIMESTAMP}"
    fi

    # Fetch and checkout target branch
    log INFO "Fetching from origin..."
    git fetch origin

    log INFO "Checking out branch: $target_branch"
    git checkout "$target_branch"

    log INFO "Pulling latest changes..."
    git pull origin "$target_branch"

    log SUCCESS "Codebase updated to latest $target_branch"
}

# =============================================================================
# DOCKER OPERATIONS
# =============================================================================

pull_images() {
    log STEP "[4/8] Pulling Docker images..."

    cd "$DOCKER_DIR"

    # Determine compose files to use
    local compose_cmd="docker compose"
    local compose_files="-f docker-compose.yml"

    if [[ "$ENVIRONMENT" == "production" && -f "docker-compose.prod.yml" ]]; then
        compose_files="$compose_files -f docker-compose.prod.yml"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY-RUN] Would execute: $compose_cmd $compose_files pull"
        return 0
    fi

    log INFO "Pulling images..."
    if $compose_cmd $compose_files pull 2>>"$LOG_FILE"; then
        log SUCCESS "Images pulled successfully"
    else
        log ERROR "Failed to pull images"
        exit 1
    fi
}

deploy_containers() {
    log STEP "[5/8] Deploying containers..."

    cd "$DOCKER_DIR"

    # Set environment file
    local env_file=".env.${ENVIRONMENT}"
    if [[ ! -f "$env_file" ]]; then
        env_file=".env"
    fi

    # Copy environment file
    if [[ -f "$env_file" && "$env_file" != ".env" ]]; then
        cp "$env_file" .env
    fi

    # Determine compose files
    local compose_cmd="docker compose"
    local compose_files="-f docker-compose.yml"

    if [[ "$ENVIRONMENT" == "production" && -f "docker-compose.prod.yml" ]]; then
        compose_files="$compose_files -f docker-compose.prod.yml"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY-RUN] Would execute: $compose_cmd $compose_files up -d --remove-orphans"
        return 0
    fi

    log INFO "Starting containers with rolling update..."
    if $compose_cmd $compose_files up -d --remove-orphans 2>>"$LOG_FILE"; then
        log SUCCESS "Containers deployed successfully"
    else
        log ERROR "Failed to deploy containers"
        exit 1
    fi
}

# =============================================================================
# HEALTH CHECKS
# =============================================================================

wait_for_health() {
    log STEP "[6/8] Waiting for services to be healthy..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY-RUN] Would wait for health checks"
        return 0
    fi

    local max_wait=180  # 3 minutes
    local wait_interval=10
    local elapsed=0

    cd "$DOCKER_DIR"

    log INFO "Waiting up to ${max_wait}s for services to become healthy..."

    while [[ $elapsed -lt $max_wait ]]; do
        # Check if all services are healthy
        local unhealthy_count=$(docker compose ps --format json 2>/dev/null | jq -r 'select(.Health == "unhealthy" or .Health == "starting") | .Name' | wc -l)

        if [[ "$unhealthy_count" -eq 0 ]]; then
            log SUCCESS "All services are healthy"
            return 0
        fi

        log INFO "Waiting... ($elapsed/$max_wait seconds, $unhealthy_count services still starting)"
        sleep $wait_interval
        elapsed=$((elapsed + wait_interval))
    done

    log WARN "Some services may not be fully healthy after ${max_wait}s"
    docker compose ps
    return 0
}

run_health_checks() {
    log STEP "[7/8] Running health checks..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY-RUN] Would run health checks"
        return 0
    fi

    local failed_checks=0

    # Backend health check
    log INFO "Checking Backend service..."
    if curl -sf "http://localhost:8081/actuator/health" > /dev/null 2>&1; then
        log SUCCESS "Backend is healthy"
    else
        log WARN "Backend health check failed"
        ((failed_checks++))
    fi

    # AI Service health check
    log INFO "Checking AI Service..."
    if curl -sf "http://localhost:8000/api/v1/health" > /dev/null 2>&1; then
        log SUCCESS "AI Service is healthy"
    else
        log WARN "AI Service health check failed"
        ((failed_checks++))
    fi

    # API Gateway health check
    log INFO "Checking API Gateway..."
    if curl -sf "http://localhost:8080/actuator/health" > /dev/null 2>&1; then
        log SUCCESS "API Gateway is healthy"
    else
        log WARN "API Gateway health check failed"
        ((failed_checks++))
    fi

    # PostgreSQL health check
    log INFO "Checking PostgreSQL..."
    if docker exec kp-postgresql pg_isready -U knowledge > /dev/null 2>&1; then
        log SUCCESS "PostgreSQL is healthy"
    else
        log WARN "PostgreSQL health check failed"
        ((failed_checks++))
    fi

    # Elasticsearch health check
    log INFO "Checking Elasticsearch..."
    if curl -sf "http://localhost:9200/_cluster/health" | grep -q '"status":"green"\|"status":"yellow"' 2>/dev/null; then
        log SUCCESS "Elasticsearch is healthy"
    else
        log WARN "Elasticsearch health check failed"
        ((failed_checks++))
    fi

    if [[ $failed_checks -gt 0 ]]; then
        log WARN "$failed_checks health check(s) failed"
        return 1
    fi

    log SUCCESS "All health checks passed"
    return 0
}

# =============================================================================
# POST-DEPLOYMENT VERIFICATION
# =============================================================================

run_post_verification() {
    if [[ "$SKIP_TESTS" == "true" ]]; then
        log INFO "Skipping post-deployment verification (--skip-tests flag set)"
        return 0
    fi

    log STEP "[8/8] Running post-deployment verification..."

    local verify_script="${SCRIPT_DIR}/post-deploy-verify.sh"

    if [[ -x "$verify_script" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log INFO "[DRY-RUN] Would execute: $verify_script $ENVIRONMENT"
            return 0
        fi

        if "$verify_script" "$ENVIRONMENT"; then
            log SUCCESS "Post-deployment verification passed"
        else
            log WARN "Post-deployment verification had warnings"
        fi
    else
        log WARN "Post-deployment verification script not found"
    fi
}

# =============================================================================
# CLEANUP
# =============================================================================

cleanup() {
    log INFO "Cleaning up..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY-RUN] Would clean up old images"
        return 0
    fi

    cd "$DOCKER_DIR"

    # Remove dangling images
    docker image prune -f >> "$LOG_FILE" 2>&1 || true

    log SUCCESS "Cleanup completed"
}

# =============================================================================
# ROLLBACK
# =============================================================================

trigger_rollback() {
    log ERROR "Deployment failed. Initiating rollback..."

    send_slack "alerts" "DEPLOY FAILED: ${ENVIRONMENT} - Initiating rollback"

    local rollback_script="${SCRIPT_DIR}/rollback.sh"

    if [[ -x "$rollback_script" ]]; then
        "$rollback_script" "$ENVIRONMENT" --auto
    else
        log ERROR "Rollback script not found. Manual intervention required."
        log INFO "To manually rollback, restore from backup in: ${PROJECT_ROOT}/backups/"
    fi

    exit 1
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    # Parse arguments
    shift || true  # Skip environment argument
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # Create log directory
    mkdir -p "$LOG_DIR"

    # Start deployment
    local start_time=$(date +%s)

    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - Deployment"
    echo "============================================================================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp:   $TIMESTAMP"
    echo "Dry Run:     $DRY_RUN"
    echo "Skip Backup: $SKIP_BACKUP"
    echo "Skip Tests:  $SKIP_TESTS"
    echo "Log File:    $LOG_FILE"
    echo "============================================================================="

    log INFO "Starting deployment to $ENVIRONMENT environment"

    # Send Slack notification
    if [[ "$DRY_RUN" != "true" ]]; then
        send_slack "dev" "DEPLOY START: ${ENVIRONMENT} environment deployment initiated"
    fi

    # Validate environment
    validate_environment

    # Run deployment steps
    run_pre_checks
    run_backup
    update_codebase
    pull_images
    deploy_containers
    wait_for_health

    # Health checks with rollback on failure
    if ! run_health_checks; then
        if [[ "$ENVIRONMENT" == "production" ]]; then
            trigger_rollback
        else
            log WARN "Health checks failed but continuing for staging environment"
        fi
    fi

    run_post_verification
    cleanup

    # Calculate duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Summary
    echo ""
    echo "============================================================================="
    echo "DEPLOYMENT SUMMARY"
    echo "============================================================================="
    echo "Environment: $ENVIRONMENT"
    echo "Duration:    ${duration} seconds"
    echo "Status:      SUCCESS"
    echo "Log File:    $LOG_FILE"
    echo "============================================================================="

    log SUCCESS "Deployment completed successfully in ${duration} seconds"

    # Send Slack notification
    if [[ "$DRY_RUN" != "true" ]]; then
        send_slack "dev" "DEPLOY COMPLETE: ${ENVIRONMENT} environment deployed successfully (${duration}s)"
    fi

    # Show container status
    echo ""
    echo "Container Status:"
    cd "$DOCKER_DIR"
    docker compose ps
}

# Trap errors
trap 'log ERROR "Deployment failed at line $LINENO"; trigger_rollback' ERR

# Run main
main "$@"
