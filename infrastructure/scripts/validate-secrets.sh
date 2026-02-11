#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Secrets Validation Script
# =============================================================================
# Version: 1.0.0
# Date: 2026-02-04
# Author: DevOps Agent
# Description: Validates that all required secrets are present and meet
#              minimum security requirements before deployment.
# =============================================================================
#
# Usage:
#   ./validate-secrets.sh [environment] [options]
#
# Environments:
#   development  - Minimal validation for local development
#   staging      - Standard validation for staging environment
#   production   - Strict validation for production deployment
#
# Options:
#   --verbose    - Show detailed output
#   --ci-mode    - Exit with error code for CI/CD pipelines
#   --generate   - Generate new secrets (outputs to /tmp)
#   --debug      - Show masked secret values (dev only)
#   --help       - Show this help message
#
# Examples:
#   ./validate-secrets.sh production
#   ./validate-secrets.sh staging --verbose
#   ./validate-secrets.sh production --ci-mode
#   ./validate-secrets.sh --generate production
#
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation counters
PASSED=0
FAILED=0
WARNINGS=0

# Options
VERBOSE=false
CI_MODE=false
GENERATE=false
DEBUG=false
ENVIRONMENT=""

# =============================================================================
# Secret Definitions
# =============================================================================

# Format: "SECRET_NAME:MIN_LENGTH:REQUIRED_ENV:DESCRIPTION"
# REQUIRED_ENV: dev,staging,prod (comma-separated environments where required)

SECRETS=(
    # Database Credentials
    "DB_PASSWORD:8:dev,staging,prod:PostgreSQL database password"
    "NEO4J_PASSWORD:8:dev,staging,prod:Neo4j graph database password"
    "REDIS_PASSWORD:8:staging,prod:Redis cache password"
    "ES_PASSWORD:8:prod:Elasticsearch password"
    "KEYCLOAK_DB_PASSWORD:8:dev,staging,prod:Keycloak database password"

    # Application Secrets
    "JWT_SECRET:32:dev,staging,prod:JWT signing secret (64+ chars for production)"
    "KEYCLOAK_ADMIN:1:dev,staging,prod:Keycloak admin username"
    "KEYCLOAK_ADMIN_PASSWORD:8:dev,staging,prod:Keycloak admin password"

    # API Keys
    "DEEPSEEK_API_KEY:10:dev,staging,prod:DeepSeek LLM API key"

    # Object Storage
    "MINIO_ACCESS_KEY:8:dev,staging,prod:MinIO access key"
    "MINIO_SECRET_KEY:8:dev,staging,prod:MinIO secret key"

    # Monitoring
    "GRAFANA_ADMIN_USER:1:staging,prod:Grafana admin username"
    "GRAFANA_ADMIN_PASSWORD:8:staging,prod:Grafana admin password"
    "KIBANA_PASSWORD:8:prod:Kibana password"
)

# Production-specific requirements (increased minimums)
PROD_REQUIREMENTS=(
    "DB_PASSWORD:32"
    "NEO4J_PASSWORD:16"
    "REDIS_PASSWORD:32"
    "ES_PASSWORD:32"
    "JWT_SECRET:64"
    "KEYCLOAK_ADMIN_PASSWORD:32"
    "KEYCLOAK_DB_PASSWORD:32"
    "MINIO_SECRET_KEY:32"
    "GRAFANA_ADMIN_PASSWORD:32"
)

# Placeholder patterns to reject
PLACEHOLDER_PATTERNS=(
    "__.*__"
    "changeme"
    "password"
    "secret"
    "your_.*_here"
    "replace_me"
    "FIXME"
    "TODO"
)

# =============================================================================
# Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}  Secrets Validation - ${ENVIRONMENT^^} Environment${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
    echo ""
}

print_usage() {
    cat << EOF
Hybrid RAG Knowledge Platform - Secrets Validation Script

Usage: $(basename "$0") [environment] [options]

Environments:
  development   Minimal validation for local development
  staging       Standard validation for staging environment
  production    Strict validation for production deployment

Options:
  --verbose     Show detailed output
  --ci-mode     Exit with error code for CI/CD pipelines
  --generate    Generate new secrets (outputs to /tmp)
  --debug       Show masked secret values (dev only)
  --help        Show this help message

Examples:
  $(basename "$0") production
  $(basename "$0") staging --verbose
  $(basename "$0") production --ci-mode
  $(basename "$0") --generate production

EOF
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

log_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

# Check if secret is required for current environment
is_required() {
    local required_envs="$1"
    local env_short=""

    case "$ENVIRONMENT" in
        development) env_short="dev" ;;
        staging) env_short="staging" ;;
        production) env_short="prod" ;;
    esac

    [[ "$required_envs" == *"$env_short"* ]]
}

# Get minimum length for secret in current environment
get_min_length() {
    local secret_name="$1"
    local default_min="$2"

    if [[ "$ENVIRONMENT" == "production" ]]; then
        for req in "${PROD_REQUIREMENTS[@]}"; do
            local name="${req%%:*}"
            local min="${req##*:}"
            if [[ "$name" == "$secret_name" ]]; then
                echo "$min"
                return
            fi
        done
    fi

    echo "$default_min"
}

# Check if value is a placeholder
is_placeholder() {
    local value="$1"
    local lower_value="${value,,}"

    for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
        if [[ "$lower_value" =~ $pattern ]]; then
            return 0
        fi
    done

    return 1
}

# Mask secret value for debug output
mask_secret() {
    local value="$1"
    local length=${#value}

    if [[ $length -le 4 ]]; then
        echo "****"
    else
        local show=4
        local hidden=$((length - show))
        echo "${value:0:$show}****($hidden hidden)"
    fi
}

# Load environment file
load_env_file() {
    local env_file=""

    case "$ENVIRONMENT" in
        development)
            env_file="${DOCKER_DIR}/.env"
            if [[ ! -f "$env_file" ]]; then
                env_file="${DOCKER_DIR}/.env.example"
            fi
            ;;
        staging)
            env_file="${DOCKER_DIR}/.env.staging"
            ;;
        production)
            env_file="${DOCKER_DIR}/.env.production"
            ;;
    esac

    if [[ -f "$env_file" ]]; then
        log_info "Loading environment file: $env_file"
        # Export variables from file (skip comments and empty lines)
        set -a
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
            # Remove leading/trailing whitespace from key
            key="${key#"${key%%[![:space:]]*}"}"
            key="${key%"${key##*[![:space:]]}"}"
            # Only export if not already set (environment takes precedence)
            if [[ -z "${!key:-}" && -n "$key" ]]; then
                export "$key=$value"
            fi
        done < "$env_file"
        set +a
    else
        log_warn "Environment file not found: $env_file"
    fi
}

# Validate a single secret
validate_secret() {
    local entry="$1"

    # Parse entry
    IFS=':' read -r secret_name min_length required_envs description <<< "$entry"

    # Check if required for this environment
    if ! is_required "$required_envs"; then
        log_info "Skipping $secret_name (not required for $ENVIRONMENT)"
        return 0
    fi

    # Get environment-appropriate minimum length
    local actual_min
    actual_min=$(get_min_length "$secret_name" "$min_length")

    # Get secret value
    local value="${!secret_name:-}"

    # Check presence
    if [[ -z "$value" ]]; then
        log_fail "$secret_name - Not set (required for $ENVIRONMENT)"
        return 1
    fi

    # Check for placeholder values
    if is_placeholder "$value"; then
        log_fail "$secret_name - Contains placeholder value"
        return 1
    fi

    # Check length
    local length=${#value}
    if [[ $length -lt $actual_min ]]; then
        log_fail "$secret_name - Too short ($length chars, minimum $actual_min)"
        return 1
    fi

    # Production-specific checks
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Check for weak patterns
        if [[ "$secret_name" == *"PASSWORD"* || "$secret_name" == *"SECRET"* ]]; then
            # Check complexity (must have mixed case and numbers)
            if ! [[ "$value" =~ [A-Z] && "$value" =~ [a-z] && "$value" =~ [0-9] ]]; then
                log_warn "$secret_name - Production password should have mixed case and numbers"
            fi
        fi
    fi

    # Debug output
    if [[ "$DEBUG" == "true" && "$ENVIRONMENT" == "development" ]]; then
        log_pass "$secret_name - Valid ($(mask_secret "$value"))"
    else
        log_pass "$secret_name - Valid ($length chars)"
    fi

    return 0
}

# Generate secrets for an environment
generate_secrets() {
    local output_dir="/tmp/secrets-${ENVIRONMENT}-$(date +%Y%m%d)"
    mkdir -p "$output_dir"
    chmod 700 "$output_dir"

    echo ""
    echo -e "${BLUE}Generating secrets for ${ENVIRONMENT}...${NC}"
    echo "Output directory: $output_dir"
    echo ""

    local summary_file="${output_dir}/README.txt"
    echo "Generated Secrets for ${ENVIRONMENT^^}" > "$summary_file"
    echo "Generated: $(date)" >> "$summary_file"
    echo "" >> "$summary_file"
    echo "IMPORTANT: Store these secrets securely and delete this directory after use." >> "$summary_file"
    echo "" >> "$summary_file"

    for entry in "${SECRETS[@]}"; do
        IFS=':' read -r secret_name min_length required_envs description <<< "$entry"

        if ! is_required "$required_envs"; then
            continue
        fi

        local actual_min
        actual_min=$(get_min_length "$secret_name" "$min_length")

        # Generate appropriate secret
        local generated=""
        case "$secret_name" in
            *"PASSWORD"*|*"SECRET"*)
                generated=$(openssl rand -base64 "$actual_min" | tr -d '\n')
                ;;
            *"KEY"*)
                if [[ "$secret_name" == "DEEPSEEK_API_KEY" ]]; then
                    generated="<YOUR_DEEPSEEK_API_KEY>"
                else
                    generated=$(openssl rand -base64 "$actual_min" | tr -d '\n')
                fi
                ;;
            *"USER"*|*"ADMIN"*)
                generated="admin_$(openssl rand -hex 4)"
                ;;
            *)
                generated=$(openssl rand -base64 "$actual_min" | tr -d '\n')
                ;;
        esac

        # Save to file
        echo "$generated" > "${output_dir}/${secret_name}.txt"
        chmod 600 "${output_dir}/${secret_name}.txt"

        # Add to summary
        echo "${secret_name}:" >> "$summary_file"
        echo "  Length: ${#generated} chars" >> "$summary_file"
        echo "  Description: $description" >> "$summary_file"
        echo "" >> "$summary_file"

        echo -e "${GREEN}Generated:${NC} $secret_name (${#generated} chars)"
    done

    echo ""
    echo -e "${GREEN}Secrets generated successfully!${NC}"
    echo ""
    echo "Files saved to: $output_dir"
    echo ""
    echo -e "${YELLOW}SECURITY REMINDER:${NC}"
    echo "  1. Transfer secrets securely (not via email/chat)"
    echo "  2. Store in GitHub Secrets or secure vault"
    echo "  3. Delete generated files after use:"
    echo "     rm -rf $output_dir"
    echo ""
}

# Print summary
print_summary() {
    echo ""
    echo -e "${BLUE}=============================================================================${NC}"
    echo -e "${BLUE}  Validation Summary${NC}"
    echo -e "${BLUE}=============================================================================${NC}"
    echo ""
    echo -e "  Environment: ${ENVIRONMENT}"
    echo -e "  ${GREEN}Passed:${NC}   $PASSED"
    echo -e "  ${RED}Failed:${NC}   $FAILED"
    echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
    echo ""

    if [[ $FAILED -gt 0 ]]; then
        echo -e "${RED}VALIDATION FAILED${NC}"
        echo ""
        echo "Please ensure all required secrets are set before deployment."
        echo "See: docs/06_deployment/09_secrets_management_guide.md"
        echo ""

        if [[ "$CI_MODE" == "true" ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}VALIDATION PASSED${NC}"
        echo ""

        if [[ $WARNINGS -gt 0 ]]; then
            echo -e "${YELLOW}Note: $WARNINGS warning(s) found. Review recommendations above.${NC}"
            echo ""
        fi
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            development|staging|production)
                ENVIRONMENT="$1"
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --ci-mode)
                CI_MODE=true
                shift
                ;;
            --generate)
                GENERATE=true
                shift
                ;;
            --debug)
                DEBUG=true
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                echo -e "${RED}Error: Unknown argument '$1'${NC}"
                print_usage
                exit 1
                ;;
        esac
    done

    # Validate environment is set
    if [[ -z "$ENVIRONMENT" ]]; then
        echo -e "${RED}Error: Environment not specified${NC}"
        print_usage
        exit 1
    fi

    # Generate mode
    if [[ "$GENERATE" == "true" ]]; then
        generate_secrets
        exit 0
    fi

    # Validation mode
    print_header

    # Load environment file
    load_env_file

    echo "Validating secrets..."
    echo ""

    # Validate each secret
    for entry in "${SECRETS[@]}"; do
        validate_secret "$entry" || true
    done

    # Print summary
    print_summary
}

# Run main
main "$@"
