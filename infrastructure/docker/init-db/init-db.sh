#!/bin/bash
# ============================================================================
# Database Initialization Script for Hybrid RAG Knowledge Platform
# Version: 1.0
# Created: 2026-01-20
# Description: Initialize PostgreSQL, Elasticsearch, and Neo4j databases
# ============================================================================

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration (can be overridden by environment variables)
POSTGRES_HOST="${POSTGRES_HOST:-postgresql}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-knowledge}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-knowledge}"
POSTGRES_DB="${POSTGRES_DB:-knowledge}"

ELASTICSEARCH_HOST="${ELASTICSEARCH_HOST:-elasticsearch}"
ELASTICSEARCH_PORT="${ELASTICSEARCH_PORT:-9200}"

NEO4J_HOST="${NEO4J_HOST:-neo4j}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-7687}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-neo4j}"

# Retry configuration
MAX_RETRIES="${MAX_RETRIES:-30}"
RETRY_INTERVAL="${RETRY_INTERVAL:-5}"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

wait_for_service() {
    local service_name=$1
    local host=$2
    local port=$3
    local check_cmd=$4
    local retries=0

    log_info "Waiting for $service_name to be ready..."

    while [ $retries -lt $MAX_RETRIES ]; do
        if eval "$check_cmd" > /dev/null 2>&1; then
            log_success "$service_name is ready!"
            return 0
        fi
        retries=$((retries + 1))
        log_info "Waiting for $service_name... (attempt $retries/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done

    log_error "$service_name did not become ready in time"
    return 1
}

# ============================================================================
# POSTGRESQL INITIALIZATION
# ============================================================================

init_postgresql() {
    log_info "=========================================="
    log_info "Initializing PostgreSQL..."
    log_info "=========================================="

    # Wait for PostgreSQL to be ready
    wait_for_service "PostgreSQL" "$POSTGRES_HOST" "$POSTGRES_PORT" \
        "pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER"

    # Check if schema already exists
    TABLES_EXIST=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users');" 2>/dev/null || echo "f")

    if [ "$TABLES_EXIST" = "t" ]; then
        log_warning "PostgreSQL schema already exists. Skipping initialization."
        return 0
    fi

    # Execute schema SQL
    if [ -f "$SCRIPT_DIR/01_postgresql_schema.sql" ]; then
        log_info "Executing PostgreSQL schema..."
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -f "$SCRIPT_DIR/01_postgresql_schema.sql"
        log_success "PostgreSQL schema created successfully!"
    else
        log_error "PostgreSQL schema file not found: $SCRIPT_DIR/01_postgresql_schema.sql"
        return 1
    fi

    # Verify tables
    TABLE_COUNT=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null || echo "0")
    log_info "PostgreSQL tables created: $TABLE_COUNT"
}

# ============================================================================
# ELASTICSEARCH INITIALIZATION
# ============================================================================

init_elasticsearch() {
    log_info "=========================================="
    log_info "Initializing Elasticsearch..."
    log_info "=========================================="

    # Wait for Elasticsearch to be ready
    wait_for_service "Elasticsearch" "$ELASTICSEARCH_HOST" "$ELASTICSEARCH_PORT" \
        "curl -s http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_cluster/health | grep -q '\"status\":\"green\"\\|\"status\":\"yellow\"'"

    # Check if index templates already exist
    TEMPLATE_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_index_template/knowledge-chunks" 2>/dev/null || echo "404")

    if [ "$TEMPLATE_EXISTS" = "200" ]; then
        log_warning "Elasticsearch index templates already exist. Skipping initialization."
        return 0
    fi

    # Read mapping configuration
    if [ ! -f "$SCRIPT_DIR/02_elasticsearch_mapping.json" ]; then
        log_error "Elasticsearch mapping file not found: $SCRIPT_DIR/02_elasticsearch_mapping.json"
        return 1
    fi

    # Install Nori plugin for Korean analysis (if not already installed)
    log_info "Checking Nori plugin..."
    NORI_INSTALLED=$(curl -s "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_cat/plugins" | grep -c "analysis-nori" || echo "0")
    if [ "$NORI_INSTALLED" = "0" ]; then
        log_warning "Nori plugin not installed. Korean analysis may not work properly."
        log_warning "Install with: elasticsearch-plugin install analysis-nori"
    fi

    log_info "Creating Elasticsearch index templates..."

    # Create knowledge-chunks template
    curl -s -X PUT "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_index_template/knowledge-chunks" \
        -H "Content-Type: application/json" \
        -d '{
          "index_patterns": ["knowledge-chunks-*"],
          "priority": 100,
          "template": {
            "settings": {
              "number_of_shards": 1,
              "number_of_replicas": 0,
              "index.codec": "best_compression"
            },
            "mappings": {
              "properties": {
                "chunk_id": {"type": "keyword"},
                "document_id": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "text": {"type": "text"},
                "dense_vector": {
                  "type": "dense_vector",
                  "dims": 1024,
                  "index": true,
                  "similarity": "cosine"
                },
                "sparse_vector": {"type": "sparse_vector"},
                "heading": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "token_count": {"type": "integer"},
                "metadata": {
                  "type": "object",
                  "properties": {
                    "document_type": {"type": "keyword"},
                    "project_name": {"type": "keyword"},
                    "project_code": {"type": "keyword"},
                    "author_name": {"type": "keyword"},
                    "valid_start_date": {"type": "date", "format": "yyyy-MM-dd||epoch_millis"},
                    "valid_end_date": {"type": "date", "format": "yyyy-MM-dd||epoch_millis"},
                    "categories": {"type": "keyword"},
                    "keywords": {"type": "keyword"}
                  }
                },
                "neo4j_entity_ids": {"type": "keyword"},
                "neo4j_community_id": {"type": "keyword"},
                "total_chunks": {"type": "integer"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
              }
            }
          }
        }' && log_success "Created knowledge-chunks template"

    # Create knowledge-documents template
    curl -s -X PUT "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_index_template/knowledge-documents" \
        -H "Content-Type: application/json" \
        -d '{
          "index_patterns": ["knowledge-documents-*"],
          "priority": 100,
          "template": {
            "settings": {
              "number_of_shards": 1,
              "number_of_replicas": 0
            },
            "mappings": {
              "properties": {
                "document_id": {"type": "keyword"},
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "document_type": {"type": "keyword"},
                "project": {
                  "type": "object",
                  "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "code": {"type": "keyword"}
                  }
                },
                "author": {
                  "type": "object",
                  "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "department": {"type": "keyword"}
                  }
                },
                "valid_start_date": {"type": "date"},
                "valid_end_date": {"type": "date"},
                "categories": {
                  "type": "nested",
                  "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "code": {"type": "keyword"},
                    "level": {"type": "integer"}
                  }
                },
                "entities": {
                  "type": "nested",
                  "properties": {
                    "id": {"type": "keyword"},
                    "name": {"type": "keyword"},
                    "type": {"type": "keyword"},
                    "relevance_score": {"type": "float"}
                  }
                },
                "file_info": {
                  "type": "object",
                  "properties": {
                    "name": {"type": "keyword"},
                    "size": {"type": "long"},
                    "type": {"type": "keyword"}
                  }
                },
                "chunk_count": {"type": "integer"},
                "entity_count": {"type": "integer"},
                "processing_status": {"type": "keyword"},
                "keywords": {"type": "keyword"},
                "summary": {"type": "text"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"}
              }
            }
          }
        }' && log_success "Created knowledge-documents template"

    # Create knowledge-search-logs template
    curl -s -X PUT "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_index_template/knowledge-search-logs" \
        -H "Content-Type: application/json" \
        -d '{
          "index_patterns": ["knowledge-search-logs-*"],
          "priority": 100,
          "template": {
            "settings": {
              "number_of_shards": 1,
              "number_of_replicas": 0
            },
            "mappings": {
              "properties": {
                "search_id": {"type": "keyword"},
                "user_id": {"type": "keyword"},
                "query_text": {"type": "text"},
                "intent": {"type": "keyword"},
                "filters": {"type": "object", "enabled": false},
                "result_count": {"type": "integer"},
                "search_duration_ms": {"type": "integer"},
                "search_type": {"type": "keyword"},
                "timestamp": {"type": "date"}
              }
            }
          }
        }' && log_success "Created knowledge-search-logs template"

    # Create initial indices with aliases
    log_info "Creating initial indices..."

    curl -s -X PUT "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/knowledge-chunks-v1" \
        -H "Content-Type: application/json" \
        -d '{"aliases": {"knowledge-chunks": {}}}' && log_success "Created knowledge-chunks-v1 index"

    curl -s -X PUT "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/knowledge-documents-v1" \
        -H "Content-Type: application/json" \
        -d '{"aliases": {"knowledge-documents": {}}}' && log_success "Created knowledge-documents-v1 index"

    curl -s -X PUT "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/knowledge-search-logs-v1" \
        -H "Content-Type: application/json" \
        -d '{"aliases": {"knowledge-search-logs": {}}}' && log_success "Created knowledge-search-logs-v1 index"

    # Verify indices
    INDEX_COUNT=$(curl -s "http://$ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT/_cat/indices?h=index" | grep -c "knowledge" || echo "0")
    log_info "Elasticsearch indices created: $INDEX_COUNT"

    log_success "Elasticsearch initialization completed!"
}

# ============================================================================
# NEO4J INITIALIZATION
# ============================================================================

init_neo4j() {
    log_info "=========================================="
    log_info "Initializing Neo4j..."
    log_info "=========================================="

    # Wait for Neo4j to be ready
    wait_for_service "Neo4j" "$NEO4J_HOST" "$NEO4J_HTTP_PORT" \
        "curl -s http://$NEO4J_HOST:$NEO4J_HTTP_PORT"

    # Check if constraints already exist
    CONSTRAINT_COUNT=$(curl -s -X POST "http://$NEO4J_HOST:$NEO4J_HTTP_PORT/db/neo4j/tx/commit" \
        -H "Content-Type: application/json" \
        -u "$NEO4J_USER:$NEO4J_PASSWORD" \
        -d '{"statements": [{"statement": "SHOW CONSTRAINTS YIELD name RETURN count(*) as count"}]}' 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*' || echo "0")

    if [ "$CONSTRAINT_COUNT" -gt "5" ]; then
        log_warning "Neo4j constraints already exist ($CONSTRAINT_COUNT found). Skipping initialization."
        return 0
    fi

    log_info "Executing Neo4j constraints and indexes..."

    # Execute Cypher statements
    if [ -f "$SCRIPT_DIR/03_neo4j_constraints.cypher" ]; then
        # Read and execute Cypher file line by line (skip comments and empty lines)
        while IFS= read -r line || [ -n "$line" ]; do
            # Skip empty lines and comments
            if [[ -z "$line" ]] || [[ "$line" =~ ^[[:space:]]*// ]] || [[ "$line" =~ ^[[:space:]]*$ ]]; then
                continue
            fi

            # Execute statement
            RESPONSE=$(curl -s -X POST "http://$NEO4J_HOST:$NEO4J_HTTP_PORT/db/neo4j/tx/commit" \
                -H "Content-Type: application/json" \
                -u "$NEO4J_USER:$NEO4J_PASSWORD" \
                -d "{\"statements\": [{\"statement\": \"$line\"}]}" 2>/dev/null)

            # Check for errors
            if echo "$RESPONSE" | grep -q '"errors":\[\]'; then
                log_info "Executed: ${line:0:60}..."
            elif echo "$RESPONSE" | grep -q "already exists"; then
                log_warning "Already exists: ${line:0:50}..."
            else
                ERROR_MSG=$(echo "$RESPONSE" | grep -o '"message":"[^"]*"' | head -1)
                if [ -n "$ERROR_MSG" ]; then
                    log_warning "Statement result: $ERROR_MSG"
                fi
            fi
        done < "$SCRIPT_DIR/03_neo4j_constraints.cypher"

        log_success "Neo4j constraints and indexes created!"
    else
        log_error "Neo4j constraints file not found: $SCRIPT_DIR/03_neo4j_constraints.cypher"
        return 1
    fi

    # Verify constraints and indexes
    FINAL_CONSTRAINT_COUNT=$(curl -s -X POST "http://$NEO4J_HOST:$NEO4J_HTTP_PORT/db/neo4j/tx/commit" \
        -H "Content-Type: application/json" \
        -u "$NEO4J_USER:$NEO4J_PASSWORD" \
        -d '{"statements": [{"statement": "SHOW CONSTRAINTS YIELD name RETURN count(*) as count"}]}' 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*' || echo "0")

    FINAL_INDEX_COUNT=$(curl -s -X POST "http://$NEO4J_HOST:$NEO4J_HTTP_PORT/db/neo4j/tx/commit" \
        -H "Content-Type: application/json" \
        -u "$NEO4J_USER:$NEO4J_PASSWORD" \
        -d '{"statements": [{"statement": "SHOW INDEXES YIELD name RETURN count(*) as count"}]}' 2>/dev/null | grep -o '"count":[0-9]*' | grep -o '[0-9]*' || echo "0")

    log_info "Neo4j constraints: $FINAL_CONSTRAINT_COUNT, indexes: $FINAL_INDEX_COUNT"
    log_success "Neo4j initialization completed!"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log_info "=========================================="
    log_info "Database Initialization Script"
    log_info "Hybrid RAG Knowledge Platform"
    log_info "=========================================="
    log_info ""
    log_info "Configuration:"
    log_info "  PostgreSQL: $POSTGRES_HOST:$POSTGRES_PORT"
    log_info "  Elasticsearch: $ELASTICSEARCH_HOST:$ELASTICSEARCH_PORT"
    log_info "  Neo4j: $NEO4J_HOST:$NEO4J_BOLT_PORT"
    log_info ""

    # Parse command line arguments
    INIT_POSTGRES=true
    INIT_ELASTIC=true
    INIT_NEO4J=true

    while [[ $# -gt 0 ]]; do
        case $1 in
            --postgres-only)
                INIT_ELASTIC=false
                INIT_NEO4J=false
                shift
                ;;
            --elasticsearch-only)
                INIT_POSTGRES=false
                INIT_NEO4J=false
                shift
                ;;
            --neo4j-only)
                INIT_POSTGRES=false
                INIT_ELASTIC=false
                shift
                ;;
            --skip-postgres)
                INIT_POSTGRES=false
                shift
                ;;
            --skip-elasticsearch)
                INIT_ELASTIC=false
                shift
                ;;
            --skip-neo4j)
                INIT_NEO4J=false
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --postgres-only       Initialize only PostgreSQL"
                echo "  --elasticsearch-only  Initialize only Elasticsearch"
                echo "  --neo4j-only          Initialize only Neo4j"
                echo "  --skip-postgres       Skip PostgreSQL initialization"
                echo "  --skip-elasticsearch  Skip Elasticsearch initialization"
                echo "  --skip-neo4j          Skip Neo4j initialization"
                echo "  --help, -h            Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Initialize databases
    if [ "$INIT_POSTGRES" = true ]; then
        init_postgresql || log_error "PostgreSQL initialization failed"
    fi

    if [ "$INIT_ELASTIC" = true ]; then
        init_elasticsearch || log_error "Elasticsearch initialization failed"
    fi

    if [ "$INIT_NEO4J" = true ]; then
        init_neo4j || log_error "Neo4j initialization failed"
    fi

    log_info ""
    log_info "=========================================="
    log_success "Database initialization completed!"
    log_info "=========================================="

    # Summary
    echo ""
    echo "Summary:"
    echo "--------"
    if [ "$INIT_POSTGRES" = true ]; then
        echo "  PostgreSQL: Initialized"
    fi
    if [ "$INIT_ELASTIC" = true ]; then
        echo "  Elasticsearch: Initialized"
    fi
    if [ "$INIT_NEO4J" = true ]; then
        echo "  Neo4j: Initialized"
    fi
    echo ""
}

# Run main function
main "$@"
