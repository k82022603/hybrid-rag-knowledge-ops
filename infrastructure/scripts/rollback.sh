#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Rollback Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Description: Comprehensive rollback script for application and database
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load environment variables
if [[ -f "${SCRIPT_DIR}/../docker/.env" ]]; then
    source "${SCRIPT_DIR}/../docker/.env"
elif [[ -f "${PROJECT_ROOT}/infrastructure/docker/.env" ]]; then
    source "${PROJECT_ROOT}/infrastructure/docker/.env"
fi

# Rollback configuration
BACKUP_BASE_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/var/log/rollback_${TIMESTAMP}.log"
ROLLBACK_HISTORY_FILE="/var/log/rollback_history.log"

# Docker container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-kp-postgresql}"
ELASTICSEARCH_CONTAINER="${ELASTICSEARCH_CONTAINER:-kp-elasticsearch}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-kp-neo4j}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-kp-backend}"
AI_SERVICE_CONTAINER="${AI_SERVICE_CONTAINER:-kp-ai-service}"
GATEWAY_CONTAINER="${GATEWAY_CONTAINER:-kp-api-gateway}"
FRONTEND_CONTAINER="${FRONTEND_CONTAINER:-kp-frontend}"

# Docker Compose configuration
DOCKER_COMPOSE_DIR="${PROJECT_ROOT}/infrastructure/docker"
DOCKER_COMPOSE_FILE="${DOCKER_COMPOSE_DIR}/docker-compose.yml"
DOCKER_COMPOSE_PROD_FILE="${DOCKER_COMPOSE_DIR}/docker-compose.prod.yml"

# Health check configuration
HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-30}
HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-10}

# Auto-rollback thresholds
AUTO_ROLLBACK_ERROR_THRESHOLD=${AUTO_ROLLBACK_ERROR_THRESHOLD:-5}
AUTO_ROLLBACK_HEALTH_FAILURES=${AUTO_ROLLBACK_HEALTH_FAILURES:-3}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Create log directory if not exists
    mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

    case "$level" in
        INFO)  echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        CRITICAL) echo -e "${MAGENTA}[CRITICAL]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
    esac
}

check_container() {
    local container="$1"
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        return 0
    else
        return 1
    fi
}

get_container_image_version() {
    local container="$1"
    docker inspect --format='{{.Config.Image}}' "$container" 2>/dev/null | sed 's/.*://'
}

confirm() {
    local message="$1"
    echo -e "${YELLOW}WARNING: $message${NC}"
    read -p "Are you sure you want to continue? (yes/no): " response
    if [[ "$response" != "yes" ]]; then
        echo "Aborted."
        exit 1
    fi
}

record_rollback() {
    local version="$1"
    local reason="$2"
    local status="$3"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    mkdir -p "$(dirname "$ROLLBACK_HISTORY_FILE")" 2>/dev/null || true
    echo "${timestamp} | Version: ${version} | Reason: ${reason} | Status: ${status}" >> "$ROLLBACK_HISTORY_FILE"
}

send_notification() {
    local message="$1"
    local channel="${2:-alerts}"

    if [[ -f "${PROJECT_ROOT}/scripts/send_slack.sh" ]]; then
        "${PROJECT_ROOT}/scripts/send_slack.sh" "$channel" "DevOps" "$message" 2>/dev/null || true
    fi
}

# =============================================================================
# PRE-ROLLBACK FUNCTIONS
# =============================================================================

pre_rollback_backup() {
    log INFO "Creating pre-rollback backup..."

    local backup_dir="${BACKUP_BASE_DIR}/pre-rollback-${TIMESTAMP}"
    mkdir -p "$backup_dir"

    # Save current container images
    log INFO "Recording current container images..."
    docker compose -f "$DOCKER_COMPOSE_FILE" images > "${backup_dir}/current_images.txt" 2>/dev/null || true

    # Backup PostgreSQL if running
    if check_container "$POSTGRES_CONTAINER"; then
        log INFO "Backing up PostgreSQL..."
        if [[ -n "${DB_PASSWORD:-}" ]]; then
            docker exec -e PGPASSWORD="${DB_PASSWORD}" "$POSTGRES_CONTAINER" \
                pg_dump -U "${DB_USERNAME:-knowledge}" -d "${DB_NAME:-knowledge}" \
                > "${backup_dir}/postgresql_pre_rollback.sql" 2>/dev/null || {
                    log WARN "PostgreSQL backup failed, continuing..."
                }
        fi
    fi

    # Record current state
    docker compose -f "$DOCKER_COMPOSE_FILE" ps > "${backup_dir}/container_state.txt" 2>/dev/null || true

    log SUCCESS "Pre-rollback backup completed: $backup_dir"
    echo "$backup_dir"
}

validate_target_version() {
    local version="$1"
    local registry="${REGISTRY:-ghcr.io/knowledge-platform}"

    log INFO "Validating target version: $version"

    # Check if version tag exists for main services
    local services=("backend" "ai-service" "frontend" "api-gateway")
    local valid=true

    for service in "${services[@]}"; do
        local image="${registry}/${service}:${version}"
        log INFO "Checking image: $image"

        # Try to pull the image to validate
        if ! docker pull "$image" 2>/dev/null; then
            log WARN "Image not found or not accessible: $image"
            valid=false
        fi
    done

    if [[ "$valid" == "false" ]]; then
        log WARN "Some images not found. Rollback may use local images."
        return 1
    fi

    log SUCCESS "All target images validated"
    return 0
}

# =============================================================================
# ROLLBACK FUNCTIONS
# =============================================================================

rollback_application() {
    local version="$1"
    local reason="${2:-Manual rollback}"

    log INFO "=== Application Rollback Started ==="
    log INFO "Target Version: $version"
    log INFO "Reason: $reason"

    # Create pre-rollback backup
    local backup_dir=$(pre_rollback_backup)

    # Record rollback initiation
    record_rollback "$version" "$reason" "STARTED"
    send_notification "ROLLBACK INITIATED: Rolling back to version $version - Reason: $reason"

    cd "$DOCKER_COMPOSE_DIR"

    # Step 1: Stop application services gracefully
    log INFO "[1/5] Stopping application services gracefully..."
    docker compose -f docker-compose.yml stop \
        kp-backend kp-ai-service kp-api-gateway kp-frontend 2>/dev/null || true

    sleep 5  # Wait for graceful shutdown

    # Step 2: Set target version
    log INFO "[2/5] Setting target version: $version"
    export VERSION="$version"

    # Step 3: Pull target version images
    log INFO "[3/5] Pulling target version images..."
    docker compose -f docker-compose.yml pull backend ai-service api-gateway frontend 2>/dev/null || {
        log WARN "Some images could not be pulled, using local images..."
    }

    # Step 4: Start services with new version
    log INFO "[4/5] Starting services with rollback version..."
    docker compose -f docker-compose.yml up -d --remove-orphans

    # Step 5: Wait for health checks
    log INFO "[5/5] Waiting for services to be healthy..."
    wait_for_health

    local health_status=$?

    if [[ $health_status -eq 0 ]]; then
        log SUCCESS "=== Application Rollback Completed Successfully ==="
        record_rollback "$version" "$reason" "SUCCESS"
        send_notification "ROLLBACK COMPLETED: Successfully rolled back to version $version"
        return 0
    else
        log ERROR "=== Application Rollback Failed - Services Not Healthy ==="
        record_rollback "$version" "$reason" "FAILED"
        send_notification "ROLLBACK FAILED: Health checks failed after rollback to version $version"
        return 1
    fi
}

rollback_database() {
    local backup_date="$1"
    local target="${2:-all}"  # all, postgresql, elasticsearch, neo4j

    log INFO "=== Database Rollback Started ==="
    log INFO "Backup Date: $backup_date"
    log INFO "Target: $target"

    confirm "This will OVERWRITE current database data. This action cannot be undone!"

    # Verify backup exists
    local backup_path="${BACKUP_BASE_DIR}/${backup_date}"
    if [[ ! -d "$backup_path" ]]; then
        # Try alternate date format
        backup_path=$(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -name "*${backup_date}*" | head -1)
        if [[ -z "$backup_path" ]]; then
            log ERROR "Backup not found for date: $backup_date"
            log INFO "Available backups:"
            ls -la "$BACKUP_BASE_DIR" 2>/dev/null || echo "  No backups found"
            return 1
        fi
    fi

    log INFO "Using backup from: $backup_path"

    # Stop application services first
    log INFO "Stopping application services..."
    cd "$DOCKER_COMPOSE_DIR"
    docker compose -f docker-compose.yml stop kp-backend kp-ai-service 2>/dev/null || true

    sleep 5

    case "$target" in
        all)
            restore_postgresql "$backup_path"
            restore_elasticsearch "$backup_path"
            restore_neo4j "$backup_path"
            ;;
        postgresql)
            restore_postgresql "$backup_path"
            ;;
        elasticsearch)
            restore_elasticsearch "$backup_path"
            ;;
        neo4j)
            restore_neo4j "$backup_path"
            ;;
        *)
            log ERROR "Unknown target: $target"
            return 1
            ;;
    esac

    # Restart application services
    log INFO "Restarting application services..."
    docker compose -f docker-compose.yml start kp-backend kp-ai-service

    log SUCCESS "=== Database Rollback Completed ==="
    return 0
}

restore_postgresql() {
    local backup_path="$1"

    local backup_file=$(find "$backup_path" -name "postgresql_*.sql.gz" | head -1)
    if [[ -z "$backup_file" ]]; then
        backup_file=$(find "$backup_path" -name "postgresql_*.sql" | head -1)
    fi

    if [[ -z "$backup_file" ]]; then
        log WARN "PostgreSQL backup file not found in $backup_path"
        return 1
    fi

    log INFO "Restoring PostgreSQL from: $backup_file"

    if [[ -z "${DB_PASSWORD:-}" ]]; then
        log ERROR "DB_PASSWORD environment variable not set"
        return 1
    fi

    # Decompress if needed
    local sql_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        sql_file="/tmp/postgresql_restore_$$.sql"
        gunzip -c "$backup_file" > "$sql_file"
    fi

    # Restore
    cat "$sql_file" | docker exec -i -e PGPASSWORD="${DB_PASSWORD}" "$POSTGRES_CONTAINER" \
        psql -U "${DB_USERNAME:-knowledge}" -d "${DB_NAME:-knowledge}" 2>/dev/null

    local result=$?

    # Cleanup
    [[ "$backup_file" == *.gz ]] && rm -f "$sql_file"

    if [[ $result -eq 0 ]]; then
        log SUCCESS "PostgreSQL restored successfully"
    else
        log ERROR "PostgreSQL restore failed"
    fi

    return $result
}

restore_elasticsearch() {
    local backup_path="$1"

    local snapshot_info="${backup_path}/elasticsearch/snapshot_info.json"
    if [[ ! -f "$snapshot_info" ]]; then
        log WARN "Elasticsearch snapshot info not found in $backup_path"
        return 1
    fi

    log INFO "Restoring Elasticsearch snapshot..."

    local es_url="http://localhost:${ELASTICSEARCH_PORT:-9200}"
    local snapshot_name=$(grep -o '"snapshot":"[^"]*"' "$snapshot_info" | cut -d'"' -f4 | head -1)

    if [[ -z "$snapshot_name" ]]; then
        log ERROR "Could not determine snapshot name"
        return 1
    fi

    log INFO "Restoring from snapshot: $snapshot_name"

    # Close all indices
    curl -s -X POST "${es_url}/_all/_close?wait_for_active_shards=0" > /dev/null

    # Restore
    local result=$(curl -s -X POST "${es_url}/_snapshot/backup_repo/${snapshot_name}/_restore?wait_for_completion=true" \
        -H "Content-Type: application/json" \
        -d '{"indices": "*", "ignore_unavailable": true, "include_global_state": true}')

    if echo "$result" | grep -q '"shards"'; then
        log SUCCESS "Elasticsearch restored successfully"
        return 0
    else
        log ERROR "Elasticsearch restore failed: $result"
        return 1
    fi
}

restore_neo4j() {
    local backup_path="$1"

    local backup_file=$(find "$backup_path" -name "neo4j_*.tar.gz" | head -1)
    if [[ -z "$backup_file" ]]; then
        log WARN "Neo4j backup file not found in $backup_path"
        return 1
    fi

    log INFO "Restoring Neo4j from: $backup_file"

    if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
        log ERROR "NEO4J_PASSWORD environment variable not set"
        return 1
    fi

    # Extract backup
    local restore_dir="/tmp/neo4j_restore_$$"
    mkdir -p "$restore_dir"
    tar -xzf "$backup_file" -C "$restore_dir"

    # Find cypher or json file
    local import_file=$(find "$restore_dir" -name "*.cypher" -o -name "*.json" | head -1)
    if [[ -z "$import_file" ]]; then
        log ERROR "No importable file found in Neo4j backup"
        rm -rf "$restore_dir"
        return 1
    fi

    # Clear existing data
    log INFO "Clearing existing Neo4j data..."
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASSWORD" \
        "MATCH (n) DETACH DELETE n" 2>/dev/null

    # Copy and import
    docker cp "$import_file" "${NEO4J_CONTAINER}:/import/restore_data"

    if [[ "$import_file" == *.cypher ]]; then
        docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASSWORD" \
            -f "/import/restore_data" 2>/dev/null
    else
        docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u "${NEO4J_USER:-neo4j}" -p "$NEO4J_PASSWORD" \
            "CALL apoc.import.json('/import/restore_data')" 2>/dev/null
    fi

    local result=$?

    # Cleanup
    docker exec "$NEO4J_CONTAINER" rm -f /import/restore_data 2>/dev/null
    rm -rf "$restore_dir"

    if [[ $result -eq 0 ]]; then
        log SUCCESS "Neo4j restored successfully"
    else
        log ERROR "Neo4j restore failed"
    fi

    return $result
}

# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

wait_for_health() {
    local retries=$HEALTH_CHECK_RETRIES
    local interval=$HEALTH_CHECK_INTERVAL
    local all_healthy=false

    log INFO "Waiting for services to be healthy (max ${retries} attempts)..."

    for ((i=1; i<=retries; i++)); do
        log INFO "Health check attempt $i/$retries..."

        local healthy_count=0
        local total_services=4

        # Check Backend
        if check_service_health "kp-backend" "http://localhost:8081/actuator/health"; then
            ((healthy_count++))
        fi

        # Check AI Service
        if check_service_health "kp-ai-service" "http://localhost:8000/api/v1/health"; then
            ((healthy_count++))
        fi

        # Check API Gateway
        if check_service_health "kp-api-gateway" "http://localhost:8080/actuator/health"; then
            ((healthy_count++))
        fi

        # Check Frontend
        if check_service_health "kp-frontend" "http://localhost:80/"; then
            ((healthy_count++))
        fi

        log INFO "Healthy services: $healthy_count/$total_services"

        if [[ $healthy_count -eq $total_services ]]; then
            all_healthy=true
            break
        fi

        sleep $interval
    done

    if [[ "$all_healthy" == "true" ]]; then
        log SUCCESS "All services are healthy"
        return 0
    else
        log ERROR "Health check timeout - some services are not healthy"
        return 1
    fi
}

check_service_health() {
    local container="$1"
    local health_url="$2"

    if ! check_container "$container"; then
        log WARN "Container $container is not running"
        return 1
    fi

    local status=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null)
    if [[ "$status" == "200" ]] || [[ "$status" == "204" ]]; then
        return 0
    else
        return 1
    fi
}

# =============================================================================
# AUTO-ROLLBACK FUNCTIONS
# =============================================================================

monitor_and_auto_rollback() {
    local previous_version="$1"
    local duration="${2:-300}"  # Default 5 minutes monitoring
    local check_interval="${3:-10}"

    log INFO "=== Starting Auto-Rollback Monitor ==="
    log INFO "Previous Version: $previous_version"
    log INFO "Monitoring Duration: ${duration}s"

    local end_time=$(($(date +%s) + duration))
    local consecutive_failures=0

    while [[ $(date +%s) -lt $end_time ]]; do
        # Check all services health
        if ! check_all_services_healthy; then
            ((consecutive_failures++))
            log WARN "Health check failed ($consecutive_failures/$AUTO_ROLLBACK_HEALTH_FAILURES)"

            if [[ $consecutive_failures -ge $AUTO_ROLLBACK_HEALTH_FAILURES ]]; then
                log CRITICAL "Auto-rollback threshold reached! Initiating rollback..."
                send_notification "AUTO-ROLLBACK TRIGGERED: Health check failures exceeded threshold"
                rollback_application "$previous_version" "Auto-rollback: Health check failures"
                return $?
            fi
        else
            consecutive_failures=0  # Reset on success
        fi

        # Check error rate from metrics (if available)
        if check_error_rate_threshold; then
            log CRITICAL "Error rate threshold exceeded! Initiating auto-rollback..."
            send_notification "AUTO-ROLLBACK TRIGGERED: Error rate exceeded threshold"
            rollback_application "$previous_version" "Auto-rollback: High error rate"
            return $?
        fi

        sleep $check_interval
    done

    log SUCCESS "Monitoring period completed without triggering auto-rollback"
    return 0
}

check_all_services_healthy() {
    check_service_health "kp-backend" "http://localhost:8081/actuator/health" && \
    check_service_health "kp-ai-service" "http://localhost:8000/api/v1/health" && \
    check_service_health "kp-api-gateway" "http://localhost:8080/actuator/health"
}

check_error_rate_threshold() {
    # Query Prometheus for error rate (if available)
    local prom_url="http://localhost:9090"

    if ! curl -s "$prom_url/-/healthy" >/dev/null 2>&1; then
        return 1  # Prometheus not available, skip check
    fi

    # Query error rate: (5xx responses / total responses) * 100
    local query='sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m]))/sum(rate(http_server_requests_seconds_count[5m]))*100'
    local error_rate=$(curl -s "${prom_url}/api/v1/query?query=${query}" 2>/dev/null | \
        grep -o '"value":\[[^]]*\]' | grep -o '[0-9.]*"$' | tr -d '"')

    if [[ -n "$error_rate" ]]; then
        local threshold=$AUTO_ROLLBACK_ERROR_THRESHOLD
        if (( $(echo "$error_rate > $threshold" | bc -l 2>/dev/null) )); then
            log WARN "Error rate ($error_rate%) exceeds threshold ($threshold%)"
            return 0  # Threshold exceeded
        fi
    fi

    return 1  # Below threshold or unable to check
}

# =============================================================================
# UTILITY COMMANDS
# =============================================================================

list_available_versions() {
    log INFO "Available container versions:"
    echo ""

    # List local images
    echo "Local images:"
    docker images --filter "reference=*knowledge-platform*" --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}" | head -20

    echo ""
    echo "Available backups:"
    if [[ -d "$BACKUP_BASE_DIR" ]]; then
        ls -la "$BACKUP_BASE_DIR" | tail -10
    else
        echo "  No backup directory found"
    fi

    echo ""
    echo "Rollback history:"
    if [[ -f "$ROLLBACK_HISTORY_FILE" ]]; then
        tail -10 "$ROLLBACK_HISTORY_FILE"
    else
        echo "  No rollback history"
    fi
}

verify_rollback() {
    log INFO "=== Verifying Current Deployment ==="

    echo ""
    echo "Container Status:"
    docker compose -f "$DOCKER_COMPOSE_FILE" ps 2>/dev/null || docker ps --filter "name=kp-"

    echo ""
    echo "Container Versions:"
    for container in kp-backend kp-ai-service kp-api-gateway kp-frontend; do
        if check_container "$container"; then
            local version=$(get_container_image_version "$container")
            echo "  $container: $version"
        else
            echo "  $container: NOT RUNNING"
        fi
    done

    echo ""
    echo "Health Check Results:"

    local services=(
        "Backend|http://localhost:8081/actuator/health"
        "AI Service|http://localhost:8000/api/v1/health"
        "API Gateway|http://localhost:8080/actuator/health"
        "Frontend|http://localhost:80/"
    )

    for service_info in "${services[@]}"; do
        local name=$(echo "$service_info" | cut -d'|' -f1)
        local url=$(echo "$service_info" | cut -d'|' -f2)
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "FAIL")

        if [[ "$status" == "200" ]] || [[ "$status" == "204" ]]; then
            echo -e "  $name: ${GREEN}HEALTHY${NC} ($status)"
        else
            echo -e "  $name: ${RED}UNHEALTHY${NC} ($status)"
        fi
    done

    echo ""
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

show_help() {
    cat << EOF
Hybrid RAG Knowledge Platform - Rollback Script

Usage: $(basename "$0") <command> [options]

Commands:
    app <version> [reason]      Rollback application to specified version
    db <backup_date> [target]   Rollback database from backup
    monitor <prev_ver> [dur]    Monitor and auto-rollback if needed
    list                        List available versions and backups
    verify                      Verify current deployment status

Options:
    -h, --help                  Show this help message
    -f, --force                 Skip confirmation prompts
    -q, --quiet                 Reduce output verbosity

Examples:
    # Rollback application to specific version
    ./rollback.sh app v1.2.0 "Bug in new version"

    # Rollback database from backup
    ./rollback.sh db 2026-02-03 postgresql

    # Monitor and auto-rollback
    ./rollback.sh monitor v1.2.0 300

    # List available versions
    ./rollback.sh list

    # Verify current deployment
    ./rollback.sh verify

Environment Variables:
    REGISTRY                    Docker registry URL
    BACKUP_DIR                  Backup directory path
    HEALTH_CHECK_RETRIES        Number of health check retries (default: 30)
    HEALTH_CHECK_INTERVAL       Seconds between health checks (default: 10)
    AUTO_ROLLBACK_ERROR_THRESHOLD   Error rate % to trigger auto-rollback (default: 5)
    AUTO_ROLLBACK_HEALTH_FAILURES   Consecutive failures to trigger auto-rollback (default: 3)

EOF
}

# Parse global options
FORCE_MODE=false
QUIET_MODE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE_MODE=true
            shift
            ;;
        -q|--quiet)
            QUIET_MODE=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Override confirm function in force mode
if [[ "$FORCE_MODE" == "true" ]]; then
    confirm() { return 0; }
fi

# Main command routing
if [[ $# -lt 1 ]]; then
    show_help
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    app|application)
        if [[ $# -lt 1 ]]; then
            echo "Usage: $(basename "$0") app <version> [reason]"
            exit 1
        fi
        VERSION="$1"
        REASON="${2:-Manual rollback}"
        rollback_application "$VERSION" "$REASON"
        ;;
    db|database)
        if [[ $# -lt 1 ]]; then
            echo "Usage: $(basename "$0") db <backup_date> [target]"
            exit 1
        fi
        BACKUP_DATE="$1"
        TARGET="${2:-all}"
        rollback_database "$BACKUP_DATE" "$TARGET"
        ;;
    monitor)
        if [[ $# -lt 1 ]]; then
            echo "Usage: $(basename "$0") monitor <previous_version> [duration_seconds]"
            exit 1
        fi
        PREV_VERSION="$1"
        DURATION="${2:-300}"
        monitor_and_auto_rollback "$PREV_VERSION" "$DURATION"
        ;;
    list)
        list_available_versions
        ;;
    verify)
        verify_rollback
        ;;
    *)
        echo "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac
