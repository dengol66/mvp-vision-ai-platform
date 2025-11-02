#!/bin/bash

# Start MLflow server in background
echo "Starting MLflow server on port 5000..."
mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri sqlite:///mlflow.db \
    --default-artifact-root /app/mlruns \
    &

# Wait for MLflow to be ready
echo "Waiting for MLflow server to start..."
sleep 5

# Start FastAPI application
echo "Starting FastAPI application on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
