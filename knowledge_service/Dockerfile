# =============================================================================
# AI Service (Knowledge Service) - Production Dockerfile
# STORY-063: Docling + PyTorch CPU Docker Image Setup
# =============================================================================
# Multi-stage build for optimized image size
# - Stage 1 (builder): Install dependencies with PyTorch CPU-only
# - Stage 2 (runtime): Copy installed packages + app code
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# System dependencies required for building Python packages
# - build-essential: gcc/g++ for compiled extensions
# - libgl1, libglib2.0-0: OpenCV/image processing (Docling PDF rendering)
# - libpq-dev: psycopg2 PostgreSQL adapter
# - curl: health checks and downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency files first (Docker layer caching)
COPY pyproject.toml poetry.lock* ./

# Install pip and poetry with export plugin
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry==2.1.1 poetry-plugin-export

# Regenerate poetry.lock if it's inconsistent, then export requirements
RUN poetry lock --no-update 2>/dev/null || poetry lock && \
    poetry export -f requirements.txt --without-hashes --without dev -o requirements.txt

# Install PyTorch CPU-only first (before other deps to leverage caching)
# This avoids downloading the ~2GB CUDA-enabled PyTorch
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    torch==2.5.1+cpu

# Install remaining dependencies from exported requirements
# Skip torch since we already installed CPU-only version
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Install additional required packages explicitly
# - email-validator: required for pydantic[email] EmailStr validation
# - python-multipart: required for FastAPI file upload (form data)
RUN pip install --no-cache-dir email-validator python-multipart

# Verify Docling installation (use pip show since docling has no __version__ attribute)
RUN pip show docling && python -c "import docling; print('Docling imported successfully')"

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

# Create non-root user for security
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -s /bin/bash appuser

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

WORKDIR /app

# Copy application source code
COPY src/ /app/src/
COPY pyproject.toml /app/

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/tmp && \
    chown -R appuser:appgroup /app

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
