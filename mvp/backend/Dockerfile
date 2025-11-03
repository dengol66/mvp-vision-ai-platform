FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
# Note: Railway build context is at repository root
COPY mvp/backend/requirements.txt .

# Install Python dependencies (backend only - lightweight)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mvp/backend/ .

# Copy sample datasets to /app/datasets (shared via volume in production)
COPY mvp/backend/sample_datasets/ /app/datasets/

# Copy necessary training files for config schema (no heavy dependencies)
# config_schemas.py and adapters/base.py have no torch/ML dependencies
COPY mvp/training/config_schemas.py /app/training/config_schemas.py
COPY mvp/training/adapters/__init__.py /app/training/adapters/__init__.py
COPY mvp/training/adapters/base.py /app/training/adapters/base.py
COPY mvp/training/platform_sdk/ /app/training/platform_sdk/

# Note: Heavy training code (model implementations) is NOT copied to Backend
# Backend communicates with Training Services via HTTP API
# model_registry imports are handled dynamically with try/except

# Create necessary directories
RUN mkdir -p outputs uploads /app/data/outputs /app/data/logs /app/mlruns

# Make start script executable
RUN chmod +x start.sh

# Expose ports (Railway will set PORT env var for FastAPI)
EXPOSE ${PORT:-8000}
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT:-8000}/health')" || exit 1

# Start both MLflow server and FastAPI application
CMD ["./start.sh"]
