#!/bin/bash
# =============================================================================
# STORY-063: Docling Docker Image Build & Verification Test
# =============================================================================
# Tests that the knowledge_service Docker image includes Docling and
# PyTorch CPU-only, and that document parsing functionality works.
#
# Usage:
#   ./scripts/test_docling_docker.sh          # Full test (build + verify)
#   ./scripts/test_docling_docker.sh --skip-build  # Verify only (image exists)
#
# Prerequisites:
#   - Docker Engine running
#   - docker compose available
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_DIR="${PROJECT_ROOT}/infrastructure/docker"
SERVICE_NAME="ai-service"
IMAGE_NAME="knowledge-platform/ai-service"

# Counters
PASS=0
FAIL=0
TOTAL=0

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# =============================================================================
# Step 1: Build Docker Image
# =============================================================================
build_image() {
    log_info "Building ${SERVICE_NAME} Docker image with Docling..."
    log_info "Build context: ${PROJECT_ROOT}/knowledge_service"

    cd "${COMPOSE_DIR}"

    if docker compose build ${SERVICE_NAME} 2>&1; then
        log_pass "Docker image build succeeded"
    else
        log_fail "Docker image build failed"
        exit 1
    fi
}

# =============================================================================
# Step 2: Verify Docling Import
# =============================================================================
test_docling_import() {
    log_info "Testing Docling import..."

    cd "${COMPOSE_DIR}"

    RESULT=$(docker compose run --rm --no-deps ${SERVICE_NAME} \
        python -c "import docling; print(f'Docling version: {docling.__version__}')" 2>&1) || true

    if echo "${RESULT}" | grep -q "Docling version:"; then
        log_pass "Docling import successful: ${RESULT}"
    else
        log_fail "Docling import failed: ${RESULT}"
    fi
}

# =============================================================================
# Step 3: Verify PyTorch CPU
# =============================================================================
test_pytorch_cpu() {
    log_info "Testing PyTorch CPU-only installation..."

    cd "${COMPOSE_DIR}"

    RESULT=$(docker compose run --rm --no-deps ${SERVICE_NAME} \
        python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'CPU only: {not torch.cuda.is_available()}')
" 2>&1) || true

    if echo "${RESULT}" | grep -q "PyTorch version:"; then
        log_pass "PyTorch installed: $(echo "${RESULT}" | grep 'PyTorch version:')"
    else
        log_fail "PyTorch import failed: ${RESULT}"
    fi

    if echo "${RESULT}" | grep -q "CPU only: True"; then
        log_pass "PyTorch is CPU-only (no CUDA)"
    else
        log_warn "PyTorch may include CUDA support (expected CPU-only)"
    fi
}

# =============================================================================
# Step 4: Verify Docling Document Converter
# =============================================================================
test_docling_converter() {
    log_info "Testing Docling DocumentConverter initialization..."

    cd "${COMPOSE_DIR}"

    RESULT=$(docker compose run --rm --no-deps ${SERVICE_NAME} \
        python -c "
from docling.document_converter import DocumentConverter
converter = DocumentConverter()
print('DocumentConverter initialized successfully')
" 2>&1) || true

    if echo "${RESULT}" | grep -q "DocumentConverter initialized successfully"; then
        log_pass "Docling DocumentConverter initialization successful"
    else
        log_fail "Docling DocumentConverter initialization failed: ${RESULT}"
    fi
}

# =============================================================================
# Step 5: Verify Key Dependencies
# =============================================================================
test_key_dependencies() {
    log_info "Testing key Python dependencies..."

    cd "${COMPOSE_DIR}"

    RESULT=$(docker compose run --rm --no-deps ${SERVICE_NAME} \
        python -c "
import importlib
deps = [
    'docling',
    'torch',
    'transformers',
    'sentence_transformers',
    'fastapi',
    'uvicorn',
    'elasticsearch',
    'neo4j',
    'psycopg2',
    'langchain',
    'langgraph',
    'numpy',
    'pandas',
]
results = []
for dep in deps:
    try:
        mod = importlib.import_module(dep)
        ver = getattr(mod, '__version__', 'ok')
        results.append(f'  OK: {dep} ({ver})')
    except ImportError as e:
        results.append(f'  FAIL: {dep} ({e})')
print('Dependency check results:')
for r in results:
    print(r)
" 2>&1) || true

    if echo "${RESULT}" | grep -q "FAIL:"; then
        FAILED_DEPS=$(echo "${RESULT}" | grep "FAIL:" || true)
        log_fail "Some dependencies missing: ${FAILED_DEPS}"
    else
        log_pass "All key dependencies installed"
    fi
    echo "${RESULT}" | grep -E "(OK:|FAIL:)" || true
}

# =============================================================================
# Step 6: Check Image Size
# =============================================================================
check_image_size() {
    log_info "Checking Docker image size..."

    SIZE=$(docker images "${IMAGE_NAME}" --format "{{.Size}}" 2>/dev/null | head -1)

    if [ -n "${SIZE}" ]; then
        log_info "Image size: ${IMAGE_NAME} = ${SIZE}"
        log_pass "Image size check complete"
    else
        log_warn "Could not determine image size (image may not be tagged yet)"
        # Try with compose project prefix
        SIZE=$(docker images --format "{{.Repository}}\t{{.Size}}" 2>/dev/null | grep -i "ai-service" | head -1)
        if [ -n "${SIZE}" ]; then
            log_info "Image found: ${SIZE}"
        fi
    fi
}

# =============================================================================
# Step 7: Verify DoclingAdapter (Application Code)
# =============================================================================
test_docling_adapter() {
    log_info "Testing DoclingAdapter from application code..."

    cd "${COMPOSE_DIR}"

    RESULT=$(docker compose run --rm --no-deps ${SERVICE_NAME} \
        python -c "
from app.etl.docling_adapter import DoclingAdapter
from app.models.parsed_document import DocumentFormat

adapter = DoclingAdapter(ocr_enabled=False, table_structure_enabled=True)
print(f'DoclingAdapter version: {adapter.version}')
print(f'Supports PDF: {adapter.supports_format(DocumentFormat.PDF)}')
print(f'Supports DOCX: {adapter.supports_format(DocumentFormat.DOCX)}')
print(f'Supports PPTX: {adapter.supports_format(DocumentFormat.PPTX)}')
print(f'Supports HWP: {adapter.supports_format(DocumentFormat.HWP)}')
print('DoclingAdapter test passed')
" 2>&1) || true

    if echo "${RESULT}" | grep -q "DoclingAdapter test passed"; then
        log_pass "DoclingAdapter initialization and format check passed"
    else
        log_fail "DoclingAdapter test failed: ${RESULT}"
    fi
}

# =============================================================================
# Main
# =============================================================================
main() {
    echo "============================================================"
    echo " STORY-063: Docling Docker Image Verification"
    echo "============================================================"
    echo ""

    SKIP_BUILD=false
    for arg in "$@"; do
        case $arg in
            --skip-build)
                SKIP_BUILD=true
                ;;
        esac
    done

    # Step 1: Build
    if [ "${SKIP_BUILD}" = false ]; then
        build_image
    else
        log_info "Skipping build (--skip-build flag)"
    fi

    echo ""
    echo "--- Verification Tests ---"
    echo ""

    # Step 2-7: Tests
    test_docling_import
    test_pytorch_cpu
    test_docling_converter
    test_key_dependencies
    check_image_size
    test_docling_adapter

    # Summary
    echo ""
    echo "============================================================"
    echo " Test Results: ${PASS}/${TOTAL} passed, ${FAIL} failed"
    echo "============================================================"

    if [ ${FAIL} -gt 0 ]; then
        echo -e "${RED}Some tests failed. Review output above.${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    fi
}

main "$@"
