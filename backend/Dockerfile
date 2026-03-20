# Build stage - compile dependencies
FROM python:3.11-alpine AS builder

WORKDIR /build

# Install build dependencies (Alpine-specific)
RUN apk add --no-cache gcc musl-dev g++ libffi-dev openssl-dev

COPY requirements.txt .

# Build wheels in builder stage
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Production stage - minimal runtime
FROM python:3.11-alpine

WORKDIR /app

# Install only runtime dependencies (Alpine-specific)
RUN apk add --no-cache libffi openssl

# Copy pre-built wheels from builder
COPY --from=builder /build/wheels /wheels
COPY requirements.txt .

# Install from wheels (much faster, already compiled)
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Copy only necessary app files (exclude test/, migrations, __pycache__, etc.)
COPY app/ app/
COPY .env.example .env.example

# Create non-root user for security (Alpine-specific)
RUN addgroup -g 1000 appuser && adduser -D -u 1000 -G appuser appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
