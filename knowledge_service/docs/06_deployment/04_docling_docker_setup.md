# Docling Docker Image Setup Guide

**STORY-063** | Sprint 04 | Infra Engineer

---

## Overview

This document describes how Docling (document parsing library) is integrated into the AI Service Docker image. Docling enables parsing of PDF, DOCX, and PPTX documents with table extraction, OCR, and image recognition capabilities.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| PyTorch CPU-only | Reduces image size by ~1.5GB (no CUDA libraries) |
| Multi-stage build | Separates build dependencies from runtime, reducing final image |
| python:3.11-slim base | Smaller than full python image, includes necessary C libraries |
| Lazy loading in DoclingAdapter | Docling converter initialized on first use, not at import time |

---

## Architecture

### Docker Image Structure

```
knowledge_service/Dockerfile (Multi-stage)
|
+-- Stage 1: builder (python:3.11-slim)
|   +-- System build deps (gcc, libgl1, libglib2.0-0, libpq-dev)
|   +-- Poetry -> requirements.txt export
|   +-- PyTorch CPU-only install (torch==2.5.1+cpu)
|   +-- pip install remaining dependencies (including docling>=2.60.0)
|
+-- Stage 2: runtime (python:3.11-slim)
    +-- Runtime system deps only (libgl1, libglib2.0-0, libpq5, wget)
    +-- Copy site-packages from builder
    +-- Copy application source code
    +-- Non-root user (appuser:1001)
    +-- Health check on :8000/health
```

### Build Context

```
knowledge_service/           <-- Docker build context
+-- Dockerfile               <-- NEW (STORY-063)
+-- .dockerignore             <-- NEW (STORY-063)
+-- pyproject.toml            <-- Dependency declarations
+-- poetry.lock               <-- Locked versions
+-- src/
    +-- app/                  <-- Application source
        +-- etl/
            +-- docling_adapter.py  <-- Docling integration
```

---

## Dockerfile Details

### File Location

```
knowledge_service/Dockerfile
```

### Previously Used Stub

The previous stub Dockerfile at `infrastructure/docker/ai-service/Dockerfile` provided only a health endpoint without any actual AI service functionality. The docker-compose.yml already pointed to `knowledge_service/Dockerfile`, so no compose file changes were needed.

### PyTorch CPU-Only Installation

PyTorch GPU libraries (CUDA, cuDNN) add approximately 1.5-2GB to the image. Since this project runs inference via the DeepSeek API (not local GPU inference), we use CPU-only PyTorch.

```dockerfile
# Install PyTorch CPU-only first (separate layer for caching)
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu
```

The `+cpu` suffix ensures only CPU wheels are downloaded from the PyTorch index.

### System Dependencies

Docling requires these system libraries for PDF rendering and image processing:

| Package | Purpose |
|---------|---------|
| `libgl1` | OpenGL support for image/PDF rendering |
| `libglib2.0-0` | GLib library (dependency of OpenCV) |
| `libpq5` / `libpq-dev` | PostgreSQL client library (psycopg2) |
| `curl` / `wget` | Health checks |

---

## Docker Compose Integration

### Service Definition (unchanged)

The `ai-service` in `infrastructure/docker/docker-compose.yml` already references the correct build path:

```yaml
ai-service:
  build:
    context: ../../knowledge_service
    dockerfile: Dockerfile
  container_name: kp-ai-service
  # ... (rest of configuration unchanged)
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 8G    # Docling + PyTorch requires more memory
      reservations:
        memory: 4G
```

### Resource Requirements

With Docling and PyTorch CPU, the ai-service container requires:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Memory | 4GB | 8GB |
| CPU | 2 cores | 4 cores |
| Disk (image) | ~3GB | ~3GB |

---

## Build and Test

### Manual Build

```bash
# From project root
cd infrastructure/docker
docker compose build ai-service
```

### Automated Test Script

```bash
# Full test (build + verify)
./scripts/test_docling_docker.sh

# Verify only (skip build)
./scripts/test_docling_docker.sh --skip-build
```

The test script verifies:
1. Docker image builds successfully
2. `import docling` succeeds
3. PyTorch is CPU-only (no CUDA)
4. DocumentConverter initializes correctly
5. All key Python dependencies are present
6. Image size is reported
7. DoclingAdapter from application code works

### Quick Verification

```bash
# Test Docling import
docker compose run --rm ai-service python -c \
    "import docling; print(f'Docling {docling.__version__}')"

# Test DoclingAdapter
docker compose run --rm ai-service python -c \
    "from app.etl.docling_adapter import DoclingAdapter; \
     a = DoclingAdapter(); print(f'Version: {a.version}')"
```

---

## Test Skip Marks

The following test has a `@pytest.mark.skip` that should be removed once Docling is confirmed working in Docker:

| File | Class | Test | Skip Reason |
|------|-------|------|-------------|
| `src/tests/unit/test_document_parser.py` | `TestDoclingAdapter` | `test_parse_pdf_with_tables` | `"Requires Docling installation"` |

**Note**: Removing the skip mark is the ETL Engineer's responsibility (secondary assignee on STORY-063).

---

## Image Size Comparison

| Configuration | Estimated Size |
|---------------|---------------|
| Stub (python:3.11-alpine, health only) | ~60MB |
| Full (python:3.11-slim, PyTorch GPU + Docling) | ~5GB |
| **Optimized (python:3.11-slim, PyTorch CPU + Docling)** | **~3GB** |

The multi-stage build and CPU-only PyTorch save approximately 2GB compared to a naive full installation.

---

## Troubleshooting

### Build Failures

**Problem**: `poetry export` fails
```
Solution: Ensure poetry.lock exists and is up to date.
Run: cd knowledge_service && poetry lock
```

**Problem**: PyTorch CPU wheel not found
```
Solution: Check the PyTorch version compatibility with Python 3.11.
The --extra-index-url must point to https://download.pytorch.org/whl/cpu
```

**Problem**: libGL errors at runtime
```
Solution: Ensure libgl1 and libglib2.0-0 are installed in the runtime stage.
These are required for Docling's PDF rendering pipeline.
```

### Runtime Issues

**Problem**: Docling converter takes long to initialize
```
This is expected on first use (~10-30 seconds).
The DoclingAdapter uses lazy loading to avoid startup delay.
```

**Problem**: Out of memory during document parsing
```
Large PDF files (100+ pages with tables) may require more memory.
Increase the memory limit in docker-compose.yml:
  deploy.resources.limits.memory: 12G
```

---

## Related Files

| File | Description |
|------|-------------|
| `knowledge_service/Dockerfile` | Production Dockerfile with Docling |
| `knowledge_service/.dockerignore` | Build context exclusions |
| `infrastructure/docker/docker-compose.yml` | Service definitions (ai-service) |
| `infrastructure/docker/ai-service/Dockerfile` | DEPRECATED stub Dockerfile |
| `scripts/test_docling_docker.sh` | Build and verification test script |
| `knowledge_service/src/app/etl/docling_adapter.py` | Docling integration code |
| `knowledge_service/src/tests/unit/test_document_parser.py` | Tests (skip mark to remove) |
| `backlog/stories/STORY-063-docling-docker-setup.md` | Story definition |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-01-28 | Initial creation (STORY-063) | Infra Engineer |
