# syntax=docker/dockerfile:1
# =============================================================================
# AI Service (Knowledge Service) - Production Dockerfile
# STORY-063: Docling + PyTorch CPU Docker Image Setup
# =============================================================================
# Multi-stage build for optimized image size
# - Stage 1 (builder): Install dependencies with PyTorch CPU-only
# - Stage 2 (runtime): Copy installed packages + app code
# =============================================================================
# BuildKit 필수: DOCKER_BUILDKIT=1 docker-compose build ai-service
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# System dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install pip and poetry (separate layer - rarely changes)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install poetry==2.1.1 poetry-plugin-export

# Copy ONLY dependency files first (Docker layer caching)
# Source code changes won't invalidate this layer
COPY pyproject.toml poetry.lock* ./

# Export requirements.txt from poetry
RUN poetry lock --no-update 2>/dev/null || poetry lock && \
    poetry export -f requirements.txt --without-hashes --without dev -o requirements.txt

# Pre-build wheels directory for caching
RUN mkdir -p /build/wheels

# Install PyTorch CPU-only first (biggest package ~700MB)
# BuildKit cache mount keeps downloaded packages across builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu

# Build wheels for remaining dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Build wheels for additional required packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip wheel --wheel-dir=/build/wheels \
    email-validator python-multipart onnxruntime onnxscript

# Install all packages from pre-built wheels (fast - no download needed)
RUN pip install --no-index --find-links=/build/wheels \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu && \
    pip install --no-index --find-links=/build/wheels \
    -r requirements.txt && \
    pip install --no-index --find-links=/build/wheels \
    email-validator python-multipart onnxruntime onnxscript

# Verify Docling installation
RUN pip show docling && python -c "import docling; print('Docling imported successfully')"

# Pre-download RapidOCR models to avoid runtime downloads
# These models are required for PDF OCR processing
RUN python -c "\
from rapidocr import RapidOCR; \
engine = RapidOCR(); \
print('RapidOCR models pre-downloaded successfully')" 2>/dev/null || \
    echo "RapidOCR model pre-download skipped (non-critical)"

# ---------------------------------------------------------------------------
# Stage 2: Runtime - Lean production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime system dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libpq5 \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (UID 1000 = match host user for bind mount compatibility)
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -m -s /bin/bash appuser

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy application source code (this layer changes most often)
COPY src/ /app/src/
COPY pyproject.toml /app/

# Create necessary directories + fix runtime-writable model dirs
RUN mkdir -p /app/data /app/logs /app/tmp /app/.cache/huggingface && \
    chown -R appuser:appgroup /app && \
    chmod -R a+rw /usr/local/lib/python3.11/site-packages/rapidocr/models/ 2>/dev/null || true

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    LOG_LEVEL=INFO \
    PORT=8000

# Switch to non-root user
USER appuser

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD wget -q --spider http://localhost:8000/health || exit 1

# Start the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
