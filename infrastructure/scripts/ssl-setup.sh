#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - SSL/TLS Setup Script (Let's Encrypt)
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Description: Automated SSL/TLS certificate setup using Let's Encrypt
# Usage: ./ssl-setup.sh --domain knowledge.company.com --email admin@company.com
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"
NGINX_CERTS_DIR="${DOCKER_DIR}/nginx/certs"
CERTBOT_WEBROOT="/var/www/certbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOMAIN=""
EMAIL=""
STAGING=false
FORCE_RENEW=false
DRY_RUN=false

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        INFO)    echo -e "${BLUE}[INFO]${NC} ${timestamp} - $message" ;;
        WARN)    echo -e "${YELLOW}[WARN]${NC} ${timestamp} - $message" ;;
        ERROR)   echo -e "${RED}[ERROR]${NC} ${timestamp} - $message" ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} ${timestamp} - $message" ;;
    esac
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log ERROR "This script must be run as root (sudo)"
        exit 1
    fi
}

check_dependencies() {
    log INFO "Checking dependencies..."

    # Check certbot
    if ! command -v certbot &> /dev/null; then
        log WARN "Certbot not found. Installing..."
        install_certbot
    fi

    # Check docker
    if ! command -v docker &> /dev/null; then
        log ERROR "Docker is required but not installed"
        exit 1
    fi

    # Check docker compose
    if ! docker compose version &> /dev/null; then
        log ERROR "Docker Compose v2 is required but not installed"
        exit 1
    fi

    log SUCCESS "All dependencies are installed"
}

install_certbot() {
    local os_type=""

    # Detect OS
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        os_type="$ID"
    fi

    case "$os_type" in
        ubuntu|debian)
            log INFO "Installing certbot on Debian/Ubuntu..."
            apt-get update -qq
            apt-get install -y -qq certbot
            ;;
        centos|rhel|fedora)
            log INFO "Installing certbot on RHEL/CentOS/Fedora..."
            dnf install -y certbot || yum install -y certbot
            ;;
        alpine)
            log INFO "Installing certbot on Alpine..."
            apk add --no-cache certbot
            ;;
        *)
            log ERROR "Unsupported OS: $os_type. Please install certbot manually."
            exit 1
            ;;
    esac

    if command -v certbot &> /dev/null; then
        log SUCCESS "Certbot installed successfully"
    else
        log ERROR "Failed to install certbot"
        exit 1
    fi
}

validate_domain() {
    local domain="$1"

    # Basic domain validation
    if [[ ! "$domain" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$ ]]; then
        log ERROR "Invalid domain format: $domain"
        exit 1
    fi

    # Check DNS resolution
    if ! host "$domain" &> /dev/null && ! dig +short "$domain" &> /dev/null; then
        log WARN "Domain '$domain' does not resolve. Make sure DNS is configured."
    fi
}

# =============================================================================
# SSL SETUP FUNCTIONS
# =============================================================================

prepare_directories() {
    log INFO "Preparing directories..."

    # Create certificates directory
    mkdir -p "$NGINX_CERTS_DIR"
    chmod 700 "$NGINX_CERTS_DIR"

    # Create webroot for ACME challenge
    mkdir -p "$CERTBOT_WEBROOT"
    chmod 755 "$CERTBOT_WEBROOT"

    log SUCCESS "Directories prepared"
}

stop_nginx() {
    log INFO "Stopping Nginx container (if running)..."

    cd "$DOCKER_DIR"

    if docker compose ps nginx 2>/dev/null | grep -q "Up"; then
        docker compose stop nginx
        log INFO "Nginx stopped"
    else
        log INFO "Nginx is not running"
    fi
}

start_nginx() {
    log INFO "Starting Nginx container..."

    cd "$DOCKER_DIR"

    # Determine which compose files to use
    local compose_files="-f docker-compose.yml"
    if [[ -f "docker-compose.prod.yml" ]]; then
        compose_files="$compose_files -f docker-compose.prod.yml"
    fi

    docker compose $compose_files up -d nginx

    # Wait for nginx to be healthy
    local max_wait=30
    local waited=0
    while [[ $waited -lt $max_wait ]]; do
        if docker compose ps nginx 2>/dev/null | grep -q "healthy"; then
            log SUCCESS "Nginx started and healthy"
            return 0
        fi
        sleep 1
        ((waited++))
    done

    log WARN "Nginx started but health check not confirmed after ${max_wait}s"
}

obtain_certificate_standalone() {
    log INFO "Obtaining certificate using standalone mode..."

    local certbot_args=(
        "certonly"
        "--standalone"
        "--non-interactive"
        "--agree-tos"
        "--email" "$EMAIL"
        "-d" "$DOMAIN"
        "--cert-name" "$DOMAIN"
    )

    # Add staging flag for testing
    if [[ "$STAGING" == true ]]; then
        certbot_args+=("--staging")
        log WARN "Using Let's Encrypt STAGING environment (certificates will NOT be trusted)"
    fi

    # Add force renewal flag
    if [[ "$FORCE_RENEW" == true ]]; then
        certbot_args+=("--force-renewal")
    fi

    # Add dry-run flag
    if [[ "$DRY_RUN" == true ]]; then
        certbot_args+=("--dry-run")
        log INFO "Running in DRY-RUN mode (no actual certificate will be issued)"
    fi

    # Stop nginx to free port 80
    stop_nginx

    log INFO "Running certbot..."
    if certbot "${certbot_args[@]}"; then
        log SUCCESS "Certificate obtained successfully"
        return 0
    else
        log ERROR "Failed to obtain certificate"
        return 1
    fi
}

obtain_certificate_webroot() {
    log INFO "Obtaining certificate using webroot mode..."

    local certbot_args=(
        "certonly"
        "--webroot"
        "--webroot-path" "$CERTBOT_WEBROOT"
        "--non-interactive"
        "--agree-tos"
        "--email" "$EMAIL"
        "-d" "$DOMAIN"
        "--cert-name" "$DOMAIN"
    )

    # Add staging flag for testing
    if [[ "$STAGING" == true ]]; then
        certbot_args+=("--staging")
        log WARN "Using Let's Encrypt STAGING environment (certificates will NOT be trusted)"
    fi

    # Add force renewal flag
    if [[ "$FORCE_RENEW" == true ]]; then
        certbot_args+=("--force-renewal")
    fi

    # Add dry-run flag
    if [[ "$DRY_RUN" == true ]]; then
        certbot_args+=("--dry-run")
        log INFO "Running in DRY-RUN mode (no actual certificate will be issued)"
    fi

    log INFO "Running certbot..."
    if certbot "${certbot_args[@]}"; then
        log SUCCESS "Certificate obtained successfully"
        return 0
    else
        log ERROR "Failed to obtain certificate"
        return 1
    fi
}

copy_certificates() {
    log INFO "Copying certificates to Nginx directory..."

    local letsencrypt_dir="/etc/letsencrypt/live/${DOMAIN}"

    if [[ ! -d "$letsencrypt_dir" ]]; then
        log ERROR "Certificate directory not found: $letsencrypt_dir"
        return 1
    fi

    # Copy certificates
    cp "${letsencrypt_dir}/fullchain.pem" "${NGINX_CERTS_DIR}/fullchain.pem"
    cp "${letsencrypt_dir}/privkey.pem" "${NGINX_CERTS_DIR}/privkey.pem"
    cp "${letsencrypt_dir}/chain.pem" "${NGINX_CERTS_DIR}/chain.pem"

    # Set secure permissions
    chmod 644 "${NGINX_CERTS_DIR}/fullchain.pem"
    chmod 644 "${NGINX_CERTS_DIR}/chain.pem"
    chmod 600 "${NGINX_CERTS_DIR}/privkey.pem"

    log SUCCESS "Certificates copied to ${NGINX_CERTS_DIR}"
}

enable_ssl_config() {
    log INFO "Enabling SSL configuration..."

    local ssl_template="${DOCKER_DIR}/nginx/conf.d/ssl.conf.template"
    local ssl_config="${DOCKER_DIR}/nginx/conf.d/ssl.conf"

    if [[ ! -f "$ssl_template" ]]; then
        log ERROR "SSL template not found: $ssl_template"
        return 1
    fi

    # Copy template and replace domain placeholder
    sed "s/\${DOMAIN}/${DOMAIN}/g" "$ssl_template" > "$ssl_config"

    log SUCCESS "SSL configuration enabled at ${ssl_config}"
}

setup_auto_renewal() {
    log INFO "Setting up automatic certificate renewal..."

    local renewal_script="/etc/cron.d/certbot-renewal-knowledge-platform"
    local docker_compose_path="${DOCKER_DIR}"

    # Create renewal cron job
    cat > "$renewal_script" << EOF
# Automatic SSL certificate renewal for Hybrid RAG Knowledge Platform
# Runs twice daily at random minute (Let's Encrypt recommendation)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Renew certificates and reload nginx
0 0,12 * * * root certbot renew --quiet --deploy-hook "docker compose -C ${docker_compose_path} exec nginx nginx -s reload" >> /var/log/certbot-renewal.log 2>&1
EOF

    chmod 644 "$renewal_script"

    log SUCCESS "Auto-renewal configured. Cron job: $renewal_script"
}

verify_certificate() {
    log INFO "Verifying certificate..."

    local cert_file="${NGINX_CERTS_DIR}/fullchain.pem"

    if [[ ! -f "$cert_file" ]]; then
        log ERROR "Certificate file not found: $cert_file"
        return 1
    fi

    # Display certificate information
    echo ""
    echo "Certificate Information:"
    echo "========================"
    openssl x509 -in "$cert_file" -noout -subject -issuer -dates

    # Check expiration
    local expiry_date
    expiry_date=$(openssl x509 -in "$cert_file" -noout -enddate | cut -d= -f2)
    local expiry_epoch
    expiry_epoch=$(date -d "$expiry_date" +%s)
    local current_epoch
    current_epoch=$(date +%s)
    local days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))

    echo ""
    echo "Days until expiration: $days_until_expiry"

    if [[ $days_until_expiry -lt 30 ]]; then
        log WARN "Certificate expires in less than 30 days!"
    else
        log SUCCESS "Certificate is valid for $days_until_expiry days"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

show_help() {
    cat << EOF
Hybrid RAG Knowledge Platform - SSL/TLS Setup Script

Usage: $(basename "$0") [OPTIONS]

Required Options:
    -d, --domain DOMAIN     Domain name (e.g., knowledge.company.com)
    -e, --email EMAIL       Admin email for Let's Encrypt notifications

Optional Options:
    -h, --help              Show this help message
    -s, --staging           Use Let's Encrypt staging environment (for testing)
    -f, --force             Force certificate renewal
    -n, --dry-run           Test run without obtaining certificate
    -w, --webroot           Use webroot method instead of standalone
    --no-auto-renew         Skip automatic renewal setup

Examples:
    # Basic setup
    sudo ./ssl-setup.sh --domain knowledge.company.com --email admin@company.com

    # Test with staging environment
    sudo ./ssl-setup.sh --domain knowledge.company.com --email admin@company.com --staging

    # Dry run (no actual certificate)
    sudo ./ssl-setup.sh --domain knowledge.company.com --email admin@company.com --dry-run

    # Force renewal of existing certificate
    sudo ./ssl-setup.sh --domain knowledge.company.com --email admin@company.com --force

EOF
}

main() {
    local use_webroot=false
    local skip_auto_renew=false

    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - SSL/TLS Setup (Let's Encrypt)"
    echo "============================================================================="
    echo ""

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -e|--email)
                EMAIL="$2"
                shift 2
                ;;
            -s|--staging)
                STAGING=true
                shift
                ;;
            -f|--force)
                FORCE_RENEW=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -w|--webroot)
                use_webroot=true
                shift
                ;;
            --no-auto-renew)
                skip_auto_renew=true
                shift
                ;;
            *)
                log ERROR "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Validate required parameters
    if [[ -z "$DOMAIN" ]]; then
        log ERROR "Domain is required. Use --domain option."
        show_help
        exit 1
    fi

    if [[ -z "$EMAIL" ]]; then
        log ERROR "Email is required. Use --email option."
        show_help
        exit 1
    fi

    # Display configuration
    echo "Configuration:"
    echo "  Domain:      $DOMAIN"
    echo "  Email:       $EMAIL"
    echo "  Staging:     $STAGING"
    echo "  Force:       $FORCE_RENEW"
    echo "  Dry Run:     $DRY_RUN"
    echo "  Method:      $(if $use_webroot; then echo 'webroot'; else echo 'standalone'; fi)"
    echo ""

    # Check root privileges
    check_root

    # Validate domain
    validate_domain "$DOMAIN"

    # Check dependencies
    check_dependencies

    # Prepare directories
    prepare_directories

    # Obtain certificate
    if $use_webroot; then
        obtain_certificate_webroot
    else
        obtain_certificate_standalone
    fi

    # Skip remaining steps for dry run
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "Dry run completed. No certificates were issued."
        exit 0
    fi

    # Copy certificates
    copy_certificates

    # Enable SSL configuration
    enable_ssl_config

    # Setup auto renewal
    if [[ "$skip_auto_renew" == false ]]; then
        setup_auto_renewal
    fi

    # Verify certificate
    verify_certificate

    # Start nginx
    start_nginx

    echo ""
    echo "============================================================================="
    echo "SSL SETUP COMPLETE"
    echo "============================================================================="
    echo ""
    echo "Next steps:"
    echo "1. Verify HTTPS access: https://${DOMAIN}"
    echo "2. Check certificate: openssl s_client -connect ${DOMAIN}:443"
    echo "3. Monitor renewal logs: /var/log/certbot-renewal.log"
    echo ""
    echo "Certificate files:"
    echo "  - ${NGINX_CERTS_DIR}/fullchain.pem"
    echo "  - ${NGINX_CERTS_DIR}/privkey.pem"
    echo "  - ${NGINX_CERTS_DIR}/chain.pem"
    echo ""
    echo "============================================================================="
}

# Run main function
main "$@"
