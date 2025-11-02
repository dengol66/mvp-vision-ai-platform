"""
Training Service API Server

This is a separate microservice that handles training jobs.
Backend sends training requests via HTTP API.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI(title="Training Service")

# In-memory job status (in production, use Redis/DB)
job_status: Dict[int, Dict[str, Any]] = {}


class TrainingRequest(BaseModel):
    """Training job request schema."""
    job_id: int
    framework: str
    task_type: str
    model_name: str
    dataset_path: str
    dataset_format: str
    num_classes: int
    output_dir: str
    epochs: int
    batch_size: int
    learning_rate: float
    optimizer: str = "adam"
    device: str = "cpu"  # Railway doesn't have GPU
    image_size: int = 224
    pretrained: bool = True
    checkpoint_path: Optional[str] = None
    resume: bool = False


def run_training(request: TrainingRequest):
    """Execute training in background."""
    job_id = request.job_id

    try:
        job_status[job_id] = {"status": "running", "error": None}

        # Build command
        cmd = [
            "python", "/workspace/training/train.py",
            "--framework", request.framework,
            "--task_type", request.task_type,
            "--model_name", request.model_name,
            "--dataset_path", request.dataset_path,
            "--dataset_format", request.dataset_format,
            "--output_dir", request.output_dir,
            "--epochs", str(request.epochs),
            "--batch_size", str(request.batch_size),
            "--learning_rate", str(request.learning_rate),
            "--job_id", str(request.job_id),
            "--num_classes", str(request.num_classes),
        ]

        # Execute training
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )

        if result.returncode == 0:
            job_status[job_id] = {"status": "completed", "error": None}
        else:
            job_status[job_id] = {
                "status": "failed",
                "error": result.stderr
            }

    except Exception as e:
        job_status[job_id] = {"status": "failed", "error": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "training-service"}


@app.post("/training/start")
async def start_training(request: TrainingRequest, background_tasks: BackgroundTasks):
    """Start a training job in background."""
    job_id = request.job_id

    if job_id in job_status and job_status[job_id]["status"] == "running":
        raise HTTPException(status_code=409, detail=f"Job {job_id} is already running")

    # Start training in background
    background_tasks.add_task(run_training, request)

    return {
        "job_id": job_id,
        "status": "started",
        "message": f"Training job {job_id} started"
    }


@app.get("/training/status/{job_id}")
async def get_job_status(job_id: int):
    """Get training job status."""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return {
        "job_id": job_id,
        **job_status[job_id]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
