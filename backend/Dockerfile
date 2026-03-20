# Build stage - compile dependencies
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (Debian-based)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build wheels in builder stage (including transitive dependencies)
RUN pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# Production stage - minimal runtime
FROM python:3.11-slim

WORKDIR /app

# Copy pre-built wheels from builder
COPY --from=builder /build/wheels /wheels
COPY requirements.txt .

# Install from wheels (much faster, already compiled)
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy only necessary app files (exclude test/, migrations, __pycache__, etc.)
COPY app/ app/

# Create non-root user for security (Debian-based)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
