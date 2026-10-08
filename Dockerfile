# CertFlow Dockerfile
# Multi-stage build: slim Python image for production-oriented deployment.

FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
# so logs appear immediately in Docker.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by psycopg2-binary
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (Docker layer caching: dependencies
# change less often than source code, so this layer is cached).
COPY pyproject.toml ./
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir ".[dev]"

# Copy application source code
COPY . .

# Create storage directory
RUN mkdir -p /app/storage

# Default command: run the FastAPI application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
