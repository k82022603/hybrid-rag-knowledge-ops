#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Restore Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-01-22
# Description: Restore script for PostgreSQL, Elasticsearch, Neo4j, MinIO
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

# Docker container names
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-kp-postgresql}"
ELASTICSEARCH_CONTAINER="${ELASTICSEARCH_CONTAINER:-kp-elasticsearch}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-kp-neo4j}"
MINIO_CONTAINER="${MINIO_CONTAINER:-kp-minio}"

# Database credentials
DB_USERNAME="${DB_USERNAME:-knowledge}"
DB_NAME="${DB_NAME:-knowledge}"
NEO4J_USER="${NEO4J_USER:-neo4j}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
        INFO)  echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" ;;
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

confirm() {
    local message="$1"
    echo -e "${YELLOW}WARNING: $message${NC}"
    read -p "Are you sure you want to continue? (yes/no): " response
    if [[ "$response" != "yes" ]]; then
        echo "Aborted."
        exit 1
    fi
}

# =============================================================================
# RESTORE FUNCTIONS
# =============================================================================

restore_postgresql() {
    local backup_file="$1"

    log INFO "Starting PostgreSQL restore from: $backup_file"

    if ! check_container "$POSTGRES_CONTAINER"; then
        log ERROR "PostgreSQL container '$POSTGRES_CONTAINER' is not running"
        return 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        log ERROR "Backup file not found: $backup_file"
        return 1
    fi

    if [[ -z "${DB_PASSWORD:-}" ]]; then
        log ERROR "DB_PASSWORD environment variable is not set"
        return 1
    fi

    confirm "This will DROP and recreate the database '${DB_NAME}'. All existing data will be lost!"

    # Decompress if needed
    local sql_file="$backup_file"
    local temp_file=""

    if [[ "$backup_file" == *.gz ]]; then
        log INFO "Decompressing backup file..."
        temp_file="/tmp/postgresql_restore_$$.sql"
        gunzip -c "$backup_file" > "$temp_file"
        sql_file="$temp_file"
    fi

    # Drop and recreate database
    log INFO "Dropping and recreating database '${DB_NAME}'..."
    docker exec -e PGPASSWORD="${DB_PASSWORD}" "$POSTGRES_CONTAINER" \
        psql -U "$DB_USERNAME" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    docker exec -e PGPASSWORD="${DB_PASSWORD}" "$POSTGRES_CONTAINER" \
        psql -U "$DB_USERNAME" -d postgres -c "CREATE DATABASE ${DB_NAME};"

    # Restore
    log INFO "Restoring database..."
    if cat "$sql_file" | docker exec -i -e PGPASSWORD="${DB_PASSWORD}" "$POSTGRES_CONTAINER" \
        psql -U "$DB_USERNAME" -d "$DB_NAME" 2>/dev/null; then

        log SUCCESS "PostgreSQL restore completed successfully"

        # Cleanup temp file
        [[ -n "$temp_file" ]] && rm -f "$temp_file"

        return 0
    else
        log ERROR "PostgreSQL restore failed"
        [[ -n "$temp_file" ]] && rm -f "$temp_file"
        return 1
    fi
}

restore_elasticsearch() {
    local snapshot_name="$1"

    log INFO "Starting Elasticsearch restore from snapshot: $snapshot_name"

    if ! check_container "$ELASTICSEARCH_CONTAINER"; then
        log ERROR "Elasticsearch container '$ELASTICSEARCH_CONTAINER' is not running"
        return 1
    fi

    local es_url="http://localhost:${ELASTICSEARCH_PORT:-9200}"
    local snapshot_repo="backup_repo"

    confirm "This will close and restore all indices. Existing data will be overwritten!"

    # Check if snapshot exists
    log INFO "Checking snapshot..."
    if ! curl -s "${es_url}/_snapshot/${snapshot_repo}/${snapshot_name}" | grep -q '"state"'; then
        log ERROR "Snapshot '${snapshot_name}' not found"
        return 1
    fi

    # Close all indices
    log INFO "Closing all indices..."
    curl -s -X POST "${es_url}/_all/_close?wait_for_active_shards=0" > /dev/null

    # Restore snapshot
    log INFO "Restoring snapshot..."
    local restore_result
    restore_result=$(curl -s -X POST "${es_url}/_snapshot/${snapshot_repo}/${snapshot_name}/_restore?wait_for_completion=true" \
        -H "Content-Type: application/json" \
        -d '{
            "indices": "*",
            "ignore_unavailable": true,
            "include_global_state": true
        }')

    if echo "$restore_result" | grep -q '"shards"'; then
        log SUCCESS "Elasticsearch restore completed"
        return 0
    else
        log ERROR "Elasticsearch restore failed: $restore_result"
        return 1
    fi
}

restore_neo4j() {
    local backup_file="$1"

    log INFO "Starting Neo4j restore from: $backup_file"

    if ! check_container "$NEO4J_CONTAINER"; then
        log ERROR "Neo4j container '$NEO4J_CONTAINER' is not running"
        return 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        log ERROR "Backup file not found: $backup_file"
        return 1
    fi

    if [[ -z "${NEO4J_PASSWORD:-}" ]]; then
        log ERROR "NEO4J_PASSWORD environment variable is not set"
        return 1
    fi

    confirm "This will DELETE all existing data in Neo4j!"

    # Extract backup if compressed
    local restore_dir="/tmp/neo4j_restore_$$"
    mkdir -p "$restore_dir"

    if [[ "$backup_file" == *.tar.gz ]]; then
        log INFO "Extracting backup..."
        tar -xzf "$backup_file" -C "$restore_dir"
    fi

    # Find the cypher or json file
    local import_file
    import_file=$(find "$restore_dir" -name "*.cypher" -o -name "*.json" | head -1)

    if [[ -z "$import_file" ]]; then
        log ERROR "No importable file found in backup"
        rm -rf "$restore_dir"
        return 1
    fi

    # Clear existing data
    log INFO "Clearing existing Neo4j data..."
    docker exec "$NEO4J_CONTAINER" cypher-shell \
        -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
        "MATCH (n) DETACH DELETE n"

    # Copy import file to container
    docker cp "$import_file" "${NEO4J_CONTAINER}:/import/restore_data"

    # Import data
    log INFO "Importing Neo4j data..."
    if [[ "$import_file" == *.cypher ]]; then
        docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
            -f "/import/restore_data"
    else
        docker exec "$NEO4J_CONTAINER" cypher-shell \
            -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" \
            "CALL apoc.import.json('/import/restore_data')"
    fi

    if [[ $? -eq 0 ]]; then
        log SUCCESS "Neo4j restore completed"
        docker exec "$NEO4J_CONTAINER" rm -f /import/restore_data
        rm -rf "$restore_dir"
        return 0
    else
        log ERROR "Neo4j restore failed"
        rm -rf "$restore_dir"
        return 1
    fi
}

restore_minio() {
    local backup_file="$1"

    log INFO "Starting MinIO restore from: $backup_file"

    if ! check_container "$MINIO_CONTAINER"; then
        log ERROR "MinIO container '$MINIO_CONTAINER' is not running"
        return 1
    fi

    if [[ ! -f "$backup_file" ]]; then
        log ERROR "Backup file not found: $backup_file"
        return 1
    fi

    if [[ -z "${MINIO_ACCESS_KEY:-}" ]] || [[ -z "${MINIO_SECRET_KEY:-}" ]]; then
        log ERROR "MINIO_ACCESS_KEY or MINIO_SECRET_KEY environment variable is not set"
        return 1
    fi

    confirm "This will overwrite existing files in MinIO!"

    local restore_dir="/tmp/minio_restore_$$"
    mkdir -p "$restore_dir"

    # Extract backup
    log INFO "Extracting backup..."
    tar -xzf "$backup_file" -C "$restore_dir"

    # Find extracted directory
    local data_dir
    data_dir=$(find "$restore_dir" -maxdepth 1 -type d -name "minio_*" | head -1)

    if [[ -z "$data_dir" ]]; then
        # Try volume backup format
        data_dir="$restore_dir"
    fi

    # Configure mc
    local minio_url="http://localhost:${MINIO_API_PORT:-9000}"

    if command -v mc &> /dev/null; then
        MC_CMD="mc"
    else
        local mc_binary="/tmp/mc"
        if [[ ! -f "$mc_binary" ]]; then
            curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o "$mc_binary"
            chmod +x "$mc_binary"
        fi
        MC_CMD="$mc_binary"
    fi

    $MC_CMD alias set restore_minio "$minio_url" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY"

    # Restore each bucket
    for bucket_dir in "$data_dir"/*/; do
        local bucket_name=$(basename "$bucket_dir")

        log INFO "Restoring bucket: $bucket_name"

        # Create bucket if not exists
        $MC_CMD mb --ignore-existing "restore_minio/${bucket_name}" 2>/dev/null || true

        # Mirror files
        $MC_CMD mirror --overwrite "$bucket_dir" "restore_minio/${bucket_name}"
    done

    log SUCCESS "MinIO restore completed"

    # Cleanup
    rm -rf "$restore_dir"

    return 0
}

# =============================================================================
# MAIN
# =============================================================================

show_help() {
    cat << EOF
Hybrid RAG Knowledge Platform - Restore Script

Usage: $(basename "$0") [OPTIONS] <target> <backup_file>

Targets:
    postgresql      Restore PostgreSQL database
    elasticsearch   Restore Elasticsearch (specify snapshot name)
    neo4j           Restore Neo4j database
    minio           Restore MinIO storage

Options:
    -h, --help      Show this help message

Examples:
    # Restore PostgreSQL from backup
    ./restore.sh postgresql ./backups/2026-01-22/postgresql_20260122_020000.sql.gz

    # Restore Elasticsearch from snapshot
    ./restore.sh elasticsearch snapshot_20260122_020000

    # Restore Neo4j from backup
    ./restore.sh neo4j ./backups/2026-01-22/neo4j_20260122_020000.tar.gz

    # Restore MinIO from backup
    ./restore.sh minio ./backups/2026-01-22/minio_20260122_020000.tar.gz

EOF
}

# Parse arguments
if [[ $# -lt 1 ]]; then
    show_help
    exit 1
fi

case "$1" in
    -h|--help)
        show_help
        exit 0
        ;;
    postgresql)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $(basename "$0") postgresql <backup_file>"
            exit 1
        fi
        restore_postgresql "$2"
        ;;
    elasticsearch)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $(basename "$0") elasticsearch <snapshot_name>"
            exit 1
        fi
        restore_elasticsearch "$2"
        ;;
    neo4j)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $(basename "$0") neo4j <backup_file>"
            exit 1
        fi
        restore_neo4j "$2"
        ;;
    minio)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $(basename "$0") minio <backup_file>"
            exit 1
        fi
        restore_minio "$2"
        ;;
    *)
        echo "Unknown target: $1"
        show_help
        exit 1
        ;;
esac
