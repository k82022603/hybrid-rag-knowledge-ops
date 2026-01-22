#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Automated Backup Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-01-22
# Description: Backup script for PostgreSQL, Elasticsearch, Neo4j, MinIO
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Load environment variables
if [[ -f "${SCRIPT_DIR}/../docker/.env" ]]; then
    source "${SCRIPT_DIR}/../docker/.env"
elif [[ -f "${PROJECT_ROOT}/infrastructure/docker/.env" ]]; then
    source "${PROJECT_ROOT}/infrastructure/docker/.env"
fi

# Backup configuration
BACKUP_BASE_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${BACKUP_BASE_DIR}/${DATE}"
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Docker container names (from docker-compose.yml)
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-kp-postgresql}"
ELASTICSEARCH_CONTAINER="${ELASTICSEARCH_CONTAINER:-kp-elasticsearch}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-kp-neo4j}"
MINIO_CONTAINER="${MINIO_CONTAINER:-kp-minio}"

# Database credentials from environment
DB_USERNAME="${DB_USERNAME:-knowledge}"
DB_NAME="${DB_NAME:-knowledge}"
NEO4J_USER="${NEO4J_USER:-neo4j}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)  echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" | tee -a "$LOG_FILE" ;;
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

get_backup_size() {
    local file="$1"
    if [[ -f "$file" ]]; then
        du -h "$file" | cut -f1
    else
        echo "N/A"
    fi
}

# =============================================================================
# BACKUP FUNCTIONS
# =============================================================================

backup_postgresql() {
    log INFO "Starting PostgreSQL backup..."

    if ! check_container "$POSTGRES_CONTAINER"; then
        log ERROR "PostgreSQL container '$POSTGRES_CONTAINER' is not running"
        return 1
    fi

    local backup_file="${BACKUP_DIR}/postgresql_${TIMESTAMP}.sql"
    local compressed_file="${backup_file}.gz"

    # Check for required password
    if [[ -z "${DB_PASSWORD:-}" ]]; then
        log ERROR "DB_PASSWORD environment variable is not set"
        return 1
    fi

    # Run pg_dump inside container
    log INFO "Running pg_dump for database '${DB_NAME}'..."
    if docker exec -e PGPASSWORD="${DB_PASSWORD}" "$POSTGRES_CONTAINER" \
        pg_dump -U "$DB_USERNAME" -d "$DB_NAME" --format=plain --no-owner --no-acl \
        > "$backup_file" 2>>"$LOG_FILE"; then

        # Compress the backup
        log INFO "Compressing PostgreSQL backup..."
        gzip -9 "$backup_file"

        local size=$(get_backup_size "$compressed_file")
        log SUCCESS "PostgreSQL backup completed: $compressed_file ($size)"
        return 0
    else
        log ERROR "PostgreSQL backup failed"
        rm -f "$backup_file" 2>/dev/null
        return 1
    fi
}

backup_elasticsearch() {
    log INFO "Starting Elasticsearch backup..."

    if ! check_container "$ELASTICSEARCH_CONTAINER"; then
        log ERROR "Elasticsearch container '$ELASTICSEARCH_CONTAINER' is not running"
        return 1
    fi

    local es_url="http://localhost:${ELASTICSEARCH_PORT:-9200}"
    local snapshot_repo="backup_repo"
    local snapshot_name="snapshot_${TIMESTAMP}"
    local backup_path="${BACKUP_DIR}/elasticsearch"

    mkdir -p "$backup_path"

    # Check Elasticsearch health
    log INFO "Checking Elasticsearch cluster health..."
    local health_status
    health_status=$(curl -s "${es_url}/_cluster/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

    if [[ "$health_status" != "green" && "$health_status" != "yellow" ]]; then
        log ERROR "Elasticsearch cluster is not healthy (status: $health_status)"
        return 1
    fi

    log INFO "Elasticsearch cluster status: $health_status"

    # Create snapshot repository (if not exists)
    log INFO "Configuring snapshot repository..."

    # First, check if repository exists
    if ! curl -s "${es_url}/_snapshot/${snapshot_repo}" | grep -q "\"type\""; then
        # Create backup directory inside container
        docker exec "$ELASTICSEARCH_CONTAINER" mkdir -p /usr/share/elasticsearch/backup 2>/dev/null || true

        # Register repository
        curl -s -X PUT "${es_url}/_snapshot/${snapshot_repo}" \
            -H "Content-Type: application/json" \
            -d '{
                "type": "fs",
                "settings": {
                    "location": "/usr/share/elasticsearch/backup"
                }
            }' >> "$LOG_FILE" 2>&1
    fi

    # Create snapshot
    log INFO "Creating Elasticsearch snapshot '${snapshot_name}'..."
    local snapshot_result
    snapshot_result=$(curl -s -X PUT "${es_url}/_snapshot/${snapshot_repo}/${snapshot_name}?wait_for_completion=true" \
        -H "Content-Type: application/json" \
        -d '{
            "indices": "*",
            "ignore_unavailable": true,
            "include_global_state": true
        }')

    if echo "$snapshot_result" | grep -q '"state":"SUCCESS"'; then
        # Export indices list and mappings
        log INFO "Exporting index information..."
        curl -s "${es_url}/_cat/indices?v" > "${backup_path}/indices_list.txt" 2>>"$LOG_FILE"
        curl -s "${es_url}/_all/_mapping" > "${backup_path}/all_mappings.json" 2>>"$LOG_FILE"

        # Save snapshot info
        echo "$snapshot_result" > "${backup_path}/snapshot_info.json"

        log SUCCESS "Elasticsearch snapshot completed: ${snapshot_name}"
        return 0
    else
        log ERROR "Elasticsearch snapshot failed: $snapshot_result"
        return 1
    fi
}

backup_neo4j() {
    log INFO "Starting Neo4j backup..."

    if ! check_container "$NEO4J_CONTAINER"; then
        log ERROR "Neo4j container '$NEO4J_CONTAINER' is not running"
        return 1
    fi

    local backup_file="${BACKUP_DIR}/neo4j_${TIMESTAMP}.dump"
    local compressed_file="${backup_file}.gz"

    # Check for required password
    if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
        log ERROR "NEO4J_PASSWORD environment variable is not set"
        return 1
    fi

    # Stop transactions for consistent backup (Neo4j Community Edition)
    # Note: Community Edition doesn't support online backup, so we export data instead
    log INFO "Exporting Neo4j data using Cypher..."

    # Create backup directory inside container
    docker exec "$NEO4J_CONTAINER" mkdir -p /backup 2>/dev/null || true

    # Export nodes and relationships using cypher-shell
    log INFO "Exporting nodes..."
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "CALL apoc.export.cypher.all('/backup/export.cypher', {format: 'cypher-shell'})" \
        2>>"$LOG_FILE" || {
            # Fallback: Export as JSON
            log WARN "APOC export failed, trying JSON export..."
            docker exec "$NEO4J_CONTAINER" cypher-shell \
                -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
                "CALL apoc.export.json.all('/backup/export.json', {})" \
                2>>"$LOG_FILE" || {
                    log ERROR "Neo4j export failed"
                    return 1
                }
        }

    # Copy backup from container
    log INFO "Copying backup from container..."
    if docker cp "${NEO4J_CONTAINER}:/backup/." "${BACKUP_DIR}/neo4j_data_${TIMESTAMP}/" 2>>"$LOG_FILE"; then

        # Compress the backup
        log INFO "Compressing Neo4j backup..."
        tar -czf "${BACKUP_DIR}/neo4j_${TIMESTAMP}.tar.gz" \
            -C "${BACKUP_DIR}" "neo4j_data_${TIMESTAMP}" 2>>"$LOG_FILE"

        # Cleanup uncompressed data
        rm -rf "${BACKUP_DIR}/neo4j_data_${TIMESTAMP}"

        local size=$(get_backup_size "${BACKUP_DIR}/neo4j_${TIMESTAMP}.tar.gz")
        log SUCCESS "Neo4j backup completed: neo4j_${TIMESTAMP}.tar.gz ($size)"

        # Cleanup container backup directory
        docker exec "$NEO4J_CONTAINER" rm -rf /backup/* 2>/dev/null || true

        return 0
    else
        log ERROR "Failed to copy Neo4j backup from container"
        return 1
    fi
}

backup_minio() {
    log INFO "Starting MinIO backup..."

    if ! check_container "$MINIO_CONTAINER"; then
        log ERROR "MinIO container '$MINIO_CONTAINER' is not running"
        return 1
    fi

    local backup_path="${BACKUP_DIR}/minio_${TIMESTAMP}"
    mkdir -p "$backup_path"

    # Check for required credentials
    if [[ -z "${MINIO_ACCESS_KEY:-}" ]] || [[ -z "${MINIO_SECRET_KEY:-}" ]]; then
        log ERROR "MINIO_ACCESS_KEY or MINIO_SECRET_KEY environment variable is not set"
        return 1
    fi

    # Check if mc (MinIO Client) is available
    if ! command -v mc &> /dev/null; then
        log WARN "MinIO Client (mc) not found. Installing..."

        # Try to download mc
        local mc_binary="/tmp/mc"
        if curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o "$mc_binary" 2>>"$LOG_FILE"; then
            chmod +x "$mc_binary"
            MC_CMD="$mc_binary"
        else
            log ERROR "Failed to download MinIO Client. Falling back to volume backup..."

            # Fallback: Backup MinIO volume directly
            log INFO "Backing up MinIO volume data..."
            if docker run --rm \
                -v kp-minio-data:/data:ro \
                -v "${backup_path}:/backup" \
                alpine tar czf /backup/minio_data.tar.gz /data 2>>"$LOG_FILE"; then

                local size=$(get_backup_size "${backup_path}/minio_data.tar.gz")
                log SUCCESS "MinIO volume backup completed: minio_data.tar.gz ($size)"
                return 0
            else
                log ERROR "MinIO volume backup failed"
                return 1
            fi
        fi
    else
        MC_CMD="mc"
    fi

    # Configure mc alias
    log INFO "Configuring MinIO Client..."
    local minio_url="http://localhost:${MINIO_API_PORT:-9000}"
    $MC_CMD alias set backup_minio "$minio_url" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" 2>>"$LOG_FILE" || {
        log ERROR "Failed to configure MinIO Client"
        return 1
    }

    # List and backup all buckets
    log INFO "Listing MinIO buckets..."
    local buckets
    buckets=$($MC_CMD ls backup_minio/ 2>>"$LOG_FILE" | awk '{print $NF}' | tr -d '/')

    if [[ -z "$buckets" ]]; then
        log WARN "No buckets found in MinIO"
        return 0
    fi

    for bucket in $buckets; do
        log INFO "Mirroring bucket: $bucket"
        mkdir -p "${backup_path}/${bucket}"

        if $MC_CMD mirror "backup_minio/${bucket}" "${backup_path}/${bucket}" 2>>"$LOG_FILE"; then
            log INFO "Bucket '$bucket' mirrored successfully"
        else
            log WARN "Failed to mirror bucket '$bucket'"
        fi
    done

    # Compress the backup
    log INFO "Compressing MinIO backup..."
    tar -czf "${BACKUP_DIR}/minio_${TIMESTAMP}.tar.gz" \
        -C "${BACKUP_DIR}" "minio_${TIMESTAMP}" 2>>"$LOG_FILE"

    # Cleanup uncompressed data
    rm -rf "$backup_path"

    local size=$(get_backup_size "${BACKUP_DIR}/minio_${TIMESTAMP}.tar.gz")
    log SUCCESS "MinIO backup completed: minio_${TIMESTAMP}.tar.gz ($size)"

    return 0
}

# =============================================================================
# CLEANUP FUNCTIONS
# =============================================================================

cleanup_old_backups() {
    log INFO "Cleaning up backups older than ${RETENTION_DAYS} days..."

    local deleted_count=0

    # Find and delete old backup directories
    if [[ -d "$BACKUP_BASE_DIR" ]]; then
        while IFS= read -r -d '' old_backup; do
            log INFO "Deleting old backup: $old_backup"
            rm -rf "$old_backup"
            ((deleted_count++))
        done < <(find "$BACKUP_BASE_DIR" -maxdepth 1 -type d -mtime +${RETENTION_DAYS} -print0 2>/dev/null)
    fi

    if [[ $deleted_count -gt 0 ]]; then
        log SUCCESS "Deleted $deleted_count old backup(s)"
    else
        log INFO "No old backups to delete"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    local start_time=$(date +%s)
    local failed_backups=()
    local successful_backups=()

    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - Automated Backup"
    echo "============================================================================="
    echo "Date: $(date)"
    echo "Backup Directory: $BACKUP_DIR"
    echo "Retention: ${RETENTION_DAYS} days"
    echo "============================================================================="

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    # Initialize log file
    echo "Backup started at $(date)" > "$LOG_FILE"
    echo "Configuration:" >> "$LOG_FILE"
    echo "  - Backup Directory: $BACKUP_DIR" >> "$LOG_FILE"
    echo "  - Retention Days: $RETENTION_DAYS" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    # Run backups
    echo ""
    echo "Running backups..."
    echo ""

    # PostgreSQL
    if backup_postgresql; then
        successful_backups+=("PostgreSQL")
    else
        failed_backups+=("PostgreSQL")
    fi

    echo ""

    # Elasticsearch
    if backup_elasticsearch; then
        successful_backups+=("Elasticsearch")
    else
        failed_backups+=("Elasticsearch")
    fi

    echo ""

    # Neo4j
    if backup_neo4j; then
        successful_backups+=("Neo4j")
    else
        failed_backups+=("Neo4j")
    fi

    echo ""

    # MinIO
    if backup_minio; then
        successful_backups+=("MinIO")
    else
        failed_backups+=("MinIO")
    fi

    echo ""

    # Cleanup old backups
    cleanup_old_backups

    # Calculate duration
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Summary
    echo ""
    echo "============================================================================="
    echo "BACKUP SUMMARY"
    echo "============================================================================="
    echo "Duration: ${duration} seconds"
    echo ""

    if [[ ${#successful_backups[@]} -gt 0 ]]; then
        echo -e "${GREEN}Successful:${NC}"
        for backup in "${successful_backups[@]}"; do
            echo "  - $backup"
        done
    fi

    if [[ ${#failed_backups[@]} -gt 0 ]]; then
        echo -e "${RED}Failed:${NC}"
        for backup in "${failed_backups[@]}"; do
            echo "  - $backup"
        done
    fi

    echo ""
    echo "Backup files:"
    ls -lh "$BACKUP_DIR"/*.{sql.gz,tar.gz,json} 2>/dev/null || echo "  No backup files found"

    echo ""
    echo "Log file: $LOG_FILE"
    echo "============================================================================="

    # Exit with error if any backup failed
    if [[ ${#failed_backups[@]} -gt 0 ]]; then
        log ERROR "Backup completed with ${#failed_backups[@]} failure(s)"
        exit 1
    else
        log SUCCESS "All backups completed successfully"
        exit 0
    fi
}

# =============================================================================
# COMMAND LINE OPTIONS
# =============================================================================

show_help() {
    cat << EOF
Hybrid RAG Knowledge Platform - Backup Script

Usage: $(basename "$0") [OPTIONS]

Options:
    -h, --help          Show this help message
    -d, --dir DIR       Backup directory (default: ./backups)
    -r, --retention N   Retention days (default: 7)
    --postgresql        Backup PostgreSQL only
    --elasticsearch     Backup Elasticsearch only
    --neo4j             Backup Neo4j only
    --minio             Backup MinIO only

Environment Variables:
    DB_PASSWORD              PostgreSQL password (required)
    NEO4J_PASSWORD           Neo4j password (required)
    MINIO_ACCESS_KEY         MinIO access key (required)
    MINIO_SECRET_KEY         MinIO secret key (required)
    BACKUP_DIR               Base backup directory
    BACKUP_RETENTION_DAYS    Retention period in days

Examples:
    # Run full backup
    ./backup.sh

    # Backup PostgreSQL only
    ./backup.sh --postgresql

    # Custom backup directory and retention
    ./backup.sh -d /data/backups -r 14

EOF
}

# Parse command line arguments
BACKUP_TARGETS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dir)
            BACKUP_BASE_DIR="$2"
            shift 2
            ;;
        -r|--retention)
            RETENTION_DAYS="$2"
            shift 2
            ;;
        --postgresql)
            BACKUP_TARGETS+=("postgresql")
            shift
            ;;
        --elasticsearch)
            BACKUP_TARGETS+=("elasticsearch")
            shift
            ;;
        --neo4j)
            BACKUP_TARGETS+=("neo4j")
            shift
            ;;
        --minio)
            BACKUP_TARGETS+=("minio")
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# If specific targets are specified, run only those
if [[ ${#BACKUP_TARGETS[@]} -gt 0 ]]; then
    mkdir -p "$BACKUP_DIR"
    echo "Backup started at $(date)" > "$LOG_FILE"

    for target in "${BACKUP_TARGETS[@]}"; do
        case $target in
            postgresql)
                backup_postgresql
                ;;
            elasticsearch)
                backup_elasticsearch
                ;;
            neo4j)
                backup_neo4j
                ;;
            minio)
                backup_minio
                ;;
        esac
    done

    cleanup_old_backups
    exit $?
fi

# Run full backup
main
