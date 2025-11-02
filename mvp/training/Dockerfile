FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies for CV libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy training requirements
# Note: Railway build context is at repository root
COPY mvp/training/requirements.txt .

# Install training dependencies with NumPy 1.x for compatibility
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "numpy<2.0" && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir fastapi uvicorn

# Copy training code
COPY mvp/training/ /workspace/training/

# Create necessary directories
RUN mkdir -p /workspace/data/outputs /workspace/data/logs /workspace/mlruns

# Set Python path
ENV PYTHONPATH=/workspace/training:$PYTHONPATH

# Expose port
EXPOSE ${PORT:-8001}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT:-8001}/health')" || exit 1

# Start Training API server
CMD ["python", "/workspace/training/api_server.py"]
