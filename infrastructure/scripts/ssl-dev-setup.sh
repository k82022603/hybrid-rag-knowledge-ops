#!/bin/bash
# =============================================================================
# Hybrid RAG Knowledge Platform - Development SSL/TLS Setup Script
# =============================================================================
# Version: 1.0.0
# Created: 2026-02-04
# Description: Generate self-signed certificates for local development
# Usage: ./ssl-dev-setup.sh [--domain localhost]
# =============================================================================

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DOCKER_DIR="${PROJECT_ROOT}/infrastructure/docker"
NGINX_CERTS_DIR="${DOCKER_DIR}/nginx/certs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DOMAIN="${DOMAIN:-localhost}"
DAYS_VALID=365
KEY_SIZE=2048
COUNTRY="KR"
STATE="Seoul"
CITY="Seoul"
ORG="Development"
ORG_UNIT="Knowledge Platform"

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

check_dependencies() {
    log INFO "Checking dependencies..."

    if ! command -v openssl &> /dev/null; then
        log ERROR "OpenSSL is required but not installed"
        exit 1
    fi

    log SUCCESS "OpenSSL is available: $(openssl version)"
}

# =============================================================================
# CERTIFICATE GENERATION FUNCTIONS
# =============================================================================

prepare_directories() {
    log INFO "Preparing directories..."

    mkdir -p "$NGINX_CERTS_DIR"
    chmod 700 "$NGINX_CERTS_DIR"

    log SUCCESS "Certificate directory ready: $NGINX_CERTS_DIR"
}

generate_ca_certificate() {
    log INFO "Generating CA (Certificate Authority) certificate..."

    local ca_key="${NGINX_CERTS_DIR}/ca.key"
    local ca_cert="${NGINX_CERTS_DIR}/ca.pem"

    # Generate CA private key
    openssl genrsa -out "$ca_key" 4096 2>/dev/null

    # Generate CA certificate
    openssl req -new -x509 \
        -days $DAYS_VALID \
        -key "$ca_key" \
        -out "$ca_cert" \
        -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${ORG_UNIT}/CN=Development CA"

    chmod 600 "$ca_key"
    chmod 644 "$ca_cert"

    log SUCCESS "CA certificate generated: $ca_cert"
}

generate_server_certificate() {
    log INFO "Generating server certificate for domain: $DOMAIN"

    local ca_key="${NGINX_CERTS_DIR}/ca.key"
    local ca_cert="${NGINX_CERTS_DIR}/ca.pem"
    local server_key="${NGINX_CERTS_DIR}/privkey.pem"
    local server_csr="${NGINX_CERTS_DIR}/server.csr"
    local server_cert="${NGINX_CERTS_DIR}/fullchain.pem"
    local chain_cert="${NGINX_CERTS_DIR}/chain.pem"
    local ext_file="${NGINX_CERTS_DIR}/server.ext"

    # Generate server private key
    openssl genrsa -out "$server_key" $KEY_SIZE 2>/dev/null

    # Generate Certificate Signing Request (CSR)
    openssl req -new \
        -key "$server_key" \
        -out "$server_csr" \
        -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORG}/OU=${ORG_UNIT}/CN=${DOMAIN}"

    # Create extensions file for SAN (Subject Alternative Names)
    cat > "$ext_file" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = ${DOMAIN}
DNS.2 = *.${DOMAIN}
DNS.3 = localhost
DNS.4 = *.localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

    # Sign the certificate with CA
    openssl x509 -req \
        -in "$server_csr" \
        -CA "$ca_cert" \
        -CAkey "$ca_key" \
        -CAcreateserial \
        -out "$server_cert" \
        -days $DAYS_VALID \
        -extfile "$ext_file" 2>/dev/null

    # Copy CA cert as chain
    cp "$ca_cert" "$chain_cert"

    # Set permissions
    chmod 600 "$server_key"
    chmod 644 "$server_cert"
    chmod 644 "$chain_cert"

    # Cleanup temporary files
    rm -f "$server_csr" "$ext_file" "${NGINX_CERTS_DIR}/ca.srl"

    log SUCCESS "Server certificate generated: $server_cert"
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

    # For development, disable OCSP stapling (self-signed certs don't support it)
    sed -i 's/ssl_stapling on;/ssl_stapling off;/g' "$ssl_config"
    sed -i 's/ssl_stapling_verify on;/ssl_stapling_verify off;/g' "$ssl_config"

    # Comment out trusted certificate line (not needed for self-signed)
    sed -i 's/^\(\s*ssl_trusted_certificate\)/#\1/g' "$ssl_config"

    log SUCCESS "SSL configuration enabled at ${ssl_config}"
}

verify_certificates() {
    log INFO "Verifying generated certificates..."

    local ca_cert="${NGINX_CERTS_DIR}/ca.pem"
    local server_cert="${NGINX_CERTS_DIR}/fullchain.pem"
    local server_key="${NGINX_CERTS_DIR}/privkey.pem"

    echo ""
    echo "CA Certificate:"
    echo "==============="
    openssl x509 -in "$ca_cert" -noout -subject -issuer -dates

    echo ""
    echo "Server Certificate:"
    echo "==================="
    openssl x509 -in "$server_cert" -noout -subject -issuer -dates

    echo ""
    echo "Subject Alternative Names:"
    echo "=========================="
    openssl x509 -in "$server_cert" -noout -ext subjectAltName 2>/dev/null || echo "No SAN extension found"

    # Verify certificate chain
    echo ""
    echo "Certificate Chain Verification:"
    echo "================================"
    if openssl verify -CAfile "$ca_cert" "$server_cert" 2>/dev/null; then
        log SUCCESS "Certificate chain is valid"
    else
        log WARN "Certificate chain verification failed (expected for self-signed)"
    fi

    # Verify key matches certificate
    echo ""
    echo "Key-Certificate Match:"
    echo "======================"
    local cert_modulus
    local key_modulus
    cert_modulus=$(openssl x509 -in "$server_cert" -noout -modulus | md5sum)
    key_modulus=$(openssl rsa -in "$server_key" -noout -modulus 2>/dev/null | md5sum)

    if [[ "$cert_modulus" == "$key_modulus" ]]; then
        log SUCCESS "Private key matches certificate"
    else
        log ERROR "Private key does NOT match certificate!"
    fi
}

show_browser_trust_instructions() {
    echo ""
    echo "============================================================================="
    echo "BROWSER TRUST INSTRUCTIONS"
    echo "============================================================================="
    echo ""
    echo "To trust this certificate in your browser, you need to import the CA certificate."
    echo ""
    echo "CA Certificate location:"
    echo "  ${NGINX_CERTS_DIR}/ca.pem"
    echo ""
    echo "Chrome/Edge (Windows):"
    echo "  1. Open Settings > Privacy and security > Security > Manage certificates"
    echo "  2. Go to 'Trusted Root Certification Authorities' tab"
    echo "  3. Click 'Import' and select ca.pem"
    echo "  4. Restart browser"
    echo ""
    echo "Firefox:"
    echo "  1. Open Settings > Privacy & Security > Certificates > View Certificates"
    echo "  2. Go to 'Authorities' tab"
    echo "  3. Click 'Import' and select ca.pem"
    echo "  4. Check 'Trust this CA to identify websites'"
    echo "  5. Restart browser"
    echo ""
    echo "macOS (System-wide):"
    echo "  sudo security add-trusted-cert -d -r trustRoot \\"
    echo "    -k /Library/Keychains/System.keychain ${NGINX_CERTS_DIR}/ca.pem"
    echo ""
    echo "Linux (Debian/Ubuntu):"
    echo "  sudo cp ${NGINX_CERTS_DIR}/ca.pem /usr/local/share/ca-certificates/knowledge-platform-ca.crt"
    echo "  sudo update-ca-certificates"
    echo ""
    echo "Linux (RHEL/CentOS):"
    echo "  sudo cp ${NGINX_CERTS_DIR}/ca.pem /etc/pki/ca-trust/source/anchors/"
    echo "  sudo update-ca-trust"
    echo ""
    echo "============================================================================="
}

restart_nginx() {
    log INFO "Checking if Nginx needs to be restarted..."

    cd "$DOCKER_DIR"

    if docker compose ps nginx 2>/dev/null | grep -q "Up"; then
        log INFO "Restarting Nginx container..."
        docker compose restart nginx

        # Wait for nginx to be healthy
        local max_wait=30
        local waited=0
        while [[ $waited -lt $max_wait ]]; do
            if docker compose ps nginx 2>/dev/null | grep -q "healthy"; then
                log SUCCESS "Nginx restarted and healthy"
                return 0
            fi
            sleep 1
            ((waited++))
        done

        log WARN "Nginx restarted but health check not confirmed"
    else
        log INFO "Nginx is not running. Start it with: docker compose up -d nginx"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

show_help() {
    cat << EOF
Hybrid RAG Knowledge Platform - Development SSL/TLS Setup

Usage: $(basename "$0") [OPTIONS]

Options:
    -h, --help              Show this help message
    -d, --domain DOMAIN     Domain name (default: localhost)
    --days DAYS             Certificate validity in days (default: 365)
    --key-size SIZE         RSA key size (default: 2048)
    --country CODE          Country code (default: KR)
    --state STATE           State/Province (default: Seoul)
    --city CITY             City (default: Seoul)
    --org ORG               Organization name (default: Development)
    --no-enable             Don't enable SSL config in Nginx
    --no-restart            Don't restart Nginx after setup

Examples:
    # Basic setup for localhost
    ./ssl-dev-setup.sh

    # Setup for custom domain
    ./ssl-dev-setup.sh --domain dev.example.local

    # Setup with custom validity
    ./ssl-dev-setup.sh --domain localhost --days 730

Notes:
    - Self-signed certificates are for DEVELOPMENT ONLY
    - Browsers will show security warnings until CA is trusted
    - Never use self-signed certificates in production

EOF
}

main() {
    local enable_config=true
    local restart_nginx_flag=true

    echo "============================================================================="
    echo "Hybrid RAG Knowledge Platform - Development SSL/TLS Setup"
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
            --days)
                DAYS_VALID="$2"
                shift 2
                ;;
            --key-size)
                KEY_SIZE="$2"
                shift 2
                ;;
            --country)
                COUNTRY="$2"
                shift 2
                ;;
            --state)
                STATE="$2"
                shift 2
                ;;
            --city)
                CITY="$2"
                shift 2
                ;;
            --org)
                ORG="$2"
                shift 2
                ;;
            --no-enable)
                enable_config=false
                shift
                ;;
            --no-restart)
                restart_nginx_flag=false
                shift
                ;;
            *)
                log ERROR "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Display configuration
    echo "Configuration:"
    echo "  Domain:       $DOMAIN"
    echo "  Validity:     $DAYS_VALID days"
    echo "  Key Size:     $KEY_SIZE bits"
    echo "  Organization: $ORG"
    echo "  Location:     $CITY, $STATE, $COUNTRY"
    echo ""

    # Check dependencies
    check_dependencies

    # Prepare directories
    prepare_directories

    # Generate CA certificate
    generate_ca_certificate

    # Generate server certificate
    generate_server_certificate

    # Enable SSL config
    if $enable_config; then
        enable_ssl_config
    fi

    # Verify certificates
    verify_certificates

    # Restart nginx
    if $restart_nginx_flag; then
        restart_nginx
    fi

    # Show browser trust instructions
    show_browser_trust_instructions

    echo ""
    echo "============================================================================="
    echo "DEVELOPMENT SSL SETUP COMPLETE"
    echo "============================================================================="
    echo ""
    echo "Generated files:"
    echo "  - CA Certificate:     ${NGINX_CERTS_DIR}/ca.pem"
    echo "  - Server Certificate: ${NGINX_CERTS_DIR}/fullchain.pem"
    echo "  - Private Key:        ${NGINX_CERTS_DIR}/privkey.pem"
    echo "  - Chain Certificate:  ${NGINX_CERTS_DIR}/chain.pem"
    echo ""
    echo "Access your application at:"
    echo "  https://${DOMAIN}"
    echo ""
    echo "WARNING: This is a SELF-SIGNED certificate for DEVELOPMENT ONLY!"
    echo "         Do NOT use in production environments."
    echo ""
    echo "============================================================================="
}

# Run main function
main "$@"
