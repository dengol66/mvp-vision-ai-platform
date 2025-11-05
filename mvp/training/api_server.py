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
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import model registry
try:
    from model_registry import get_all_models, get_model_info
    from model_registry.timm_models import TIMM_MODEL_REGISTRY
    from model_registry.ultralytics_models import ULTRALYTICS_MODEL_REGISTRY
    from model_registry.huggingface_models import HUGGINGFACE_MODEL_REGISTRY
    MODEL_REGISTRY_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Model registry not available: {e}")
    MODEL_REGISTRY_AVAILABLE = False
    TIMM_MODEL_REGISTRY = {}
    ULTRALYTICS_MODEL_REGISTRY = {}
    HUGGINGFACE_MODEL_REGISTRY = {}

# Detect framework from environment variable
FRAMEWORK = os.environ.get("FRAMEWORK", "unknown")

app = FastAPI(title=f"Training Service ({FRAMEWORK})")

# In-memory job status (in production, use Redis/DB)
job_status: Dict[int, Dict[str, Any]] = {}
# Track running processes for job cancellation
job_processes: Dict[int, subprocess.Popen] = {}


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
    advanced_config: Optional[dict] = None  # Advanced configuration from Backend
    project_id: Optional[int] = None  # Project ID for checkpoint organization


class InferenceRequest(BaseModel):
    """Inference request schema."""
    training_job_id: int
    image_path: str
    framework: str
    model_name: str
    task_type: str
    num_classes: int
    dataset_path: str
    output_dir: str
    checkpoint_path: Optional[str] = None
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    max_detections: int = 100
    top_k: int = 5


def run_training(request: TrainingRequest):
    """Execute training in background."""
    job_id = request.job_id

    try:
        job_status[job_id] = {"status": "running", "error": None}

        # Get train.py path (works for both local and Railway)
        train_script = os.path.join(os.path.dirname(__file__), "train.py")

        # Determine Python interpreter
        # Try venv-{framework} first, fallback to regular python
        training_dir = os.path.dirname(__file__)
        venv_python = os.path.join(training_dir, f"venv-{request.framework}", "Scripts", "python.exe")

        if os.path.exists(venv_python):
            python_exe = venv_python
            print(f"[run_training] Using framework-specific venv: {venv_python}")
        else:
            python_exe = "python"
            print(f"[run_training] Using system python (venv not found at {venv_python})")

        sys.stdout.flush()

        # Build command
        cmd = [
            python_exe, train_script,
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

        # Add advanced_config if provided
        if request.advanced_config:
            cmd.extend(["--advanced_config", json.dumps(request.advanced_config)])

        # Add project_id if provided
        if request.project_id is not None:
            cmd.extend(["--project_id", str(request.project_id)])

        # Execute training (use Popen for process control)
        print(f"[run_training] Executing command: {' '.join(cmd)}")
        sys.stdout.flush()

        # Start process
        process = subprocess.Popen(cmd)
        job_processes[job_id] = process

        # Wait for completion
        try:
            returncode = process.wait(timeout=3600)  # 1 hour timeout

            if returncode == 0:
                job_status[job_id] = {"status": "completed", "error": None}
            else:
                job_status[job_id] = {
                    "status": "failed",
                    "error": f"Training failed with return code {returncode}"
                }
        except subprocess.TimeoutExpired:
            process.kill()
            job_status[job_id] = {"status": "failed", "error": "Training timeout (1 hour)"}
        finally:
            # Cleanup process reference
            if job_id in job_processes:
                del job_processes[job_id]

    except Exception as e:
        job_status[job_id] = {"status": "failed", "error": str(e)}
        # Cleanup process reference
        if job_id in job_processes:
            del job_processes[job_id]


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


@app.post("/training/stop/{job_id}")
async def stop_training(job_id: int):
    """
    Stop a running training job.

    Terminates the training process and updates job status to 'stopped'.
    """
    # Check if job exists
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Check if job is running
    if job_status[job_id]["status"] != "running":
        return {
            "job_id": job_id,
            "status": "already_stopped",
            "message": f"Job {job_id} is not running (status: {job_status[job_id]['status']})"
        }

    # Check if process exists
    if job_id not in job_processes:
        # Job marked as running but no process found - update status
        job_status[job_id] = {"status": "stopped", "error": "Process not found"}
        return {
            "job_id": job_id,
            "status": "stopped",
            "message": f"Job {job_id} process not found, status updated to stopped"
        }

    # Terminate the process
    try:
        process = job_processes[job_id]
        process.terminate()  # Send SIGTERM

        # Wait for graceful shutdown (max 5 seconds)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if not stopped gracefully
            process.kill()
            process.wait()

        # Update status
        job_status[job_id] = {"status": "stopped", "error": None}

        # Cleanup process reference
        del job_processes[job_id]

        return {
            "job_id": job_id,
            "status": "stopped",
            "message": f"Training job {job_id} stopped successfully"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop job {job_id}: {str(e)}"
        )


@app.get("/models/list")
async def list_models():
    """
    List all models available in this Training Service.

    Returns models specific to this framework (timm, ultralytics, or huggingface).
    """
    if not MODEL_REGISTRY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Model registry not available in this Training Service"
        )

    # Get models for this framework
    models = []

    if FRAMEWORK == "timm":
        for model_name, info in TIMM_MODEL_REGISTRY.items():
            models.append({
                "framework": "timm",
                "model_name": model_name,
                **info
            })
    elif FRAMEWORK == "ultralytics":
        for model_name, info in ULTRALYTICS_MODEL_REGISTRY.items():
            models.append({
                "framework": "ultralytics",
                "model_name": model_name,
                **info
            })
    elif FRAMEWORK == "huggingface":
        for model_name, info in HUGGINGFACE_MODEL_REGISTRY.items():
            models.append({
                "framework": "huggingface",
                "model_name": model_name,
                **info
            })
    else:
        # Unknown framework - return all models
        models = get_all_models()

    return {
        "framework": FRAMEWORK,
        "model_count": len(models),
        "models": models
    }


@app.get("/models/{model_name}")
async def get_model(model_name: str):
    """Get detailed information for a specific model."""
    if not MODEL_REGISTRY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Model registry not available in this Training Service"
        )

    model_info = get_model_info(FRAMEWORK, model_name)

    if not model_info:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found in framework '{FRAMEWORK}'"
        )

    return {
        "framework": FRAMEWORK,
        "model_name": model_name,
        **model_info
    }


@app.post("/inference/quick")
async def quick_inference(
    file: UploadFile = File(...),
    training_job_id: int = Form(...),
    framework: str = Form(...),
    model_name: str = Form(...),
    task_type: str = Form(...),
    num_classes: int = Form(...),
    dataset_path: str = Form(""),
    output_dir: str = Form(""),
    checkpoint_path: Optional[str] = Form(None),
    confidence_threshold: float = Form(0.25),
    iou_threshold: float = Form(0.45),
    max_detections: int = Form(100),
    top_k: int = Form(5)
):
    """
    Run quick inference on uploaded image.

    Accepts multipart/form-data with image file.
    Returns JSON with Base64-encoded result images (masks, overlays).

    Args:
        file: Uploaded image file (supports BytesIO from memory)
        training_job_id: Training job ID
        framework: Framework name (ultralytics, timm, etc.)
        model_name: Model name
        task_type: Task type
        num_classes: Number of classes
        dataset_path: Dataset path
        output_dir: Output directory
        checkpoint_path: Optional checkpoint path
        confidence_threshold: Confidence threshold
        iou_threshold: IoU threshold
        max_detections: Max detections
        top_k: Top-K predictions

    Returns:
        JSON with predictions and Base64-encoded result images
    """
    import uuid
    import base64
    import tempfile

    # Save uploaded file to temp location (OS-agnostic)
    temp_dir = tempfile.gettempdir()
    temp_image_path = os.path.join(temp_dir, f"inference_{uuid.uuid4()}.jpg")

    try:
        # Write uploaded file
        with open(temp_image_path, "wb") as f:
            f.write(await file.read())

        print(f"[quick_inference] Saved uploaded image to {temp_image_path}")
        sys.stdout.flush()

        # Determine Python interpreter
        training_dir = os.path.dirname(__file__)
        venv_python = os.path.join(training_dir, f"venv-{framework}", "Scripts", "python.exe")

        if os.path.exists(venv_python):
            python_exe = venv_python
            print(f"[quick_inference] Using framework-specific venv: {venv_python}")
        else:
            python_exe = "python"
            print(f"[quick_inference] Using system python (venv not found)")

        inference_script = os.path.join(training_dir, "run_quick_inference.py")

        # Build command
        cmd = [
            python_exe,
            inference_script,
            "--training_job_id", str(training_job_id),
            "--image_path", temp_image_path,
            "--framework", framework,
            "--model_name", model_name,
            "--task_type", task_type,
            "--num_classes", str(num_classes),
            "--dataset_path", dataset_path,
            "--output_dir", output_dir,
            "--confidence_threshold", str(confidence_threshold),
            "--iou_threshold", str(iou_threshold),
            "--max_detections", str(max_detections),
            "--top_k", str(top_k)
        ]

        if checkpoint_path:
            cmd.extend(["--checkpoint_path", checkpoint_path])

        print(f"[quick_inference] Running inference subprocess...")
        sys.stdout.flush()

        # Run inference
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        print(f"[quick_inference] Return code: {result.returncode}")
        sys.stdout.flush()

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"[quick_inference ERROR] {error_msg}")
            sys.stdout.flush()
            raise HTTPException(
                status_code=500,
                detail=f"Inference failed: {error_msg}"
            )

        # Parse JSON result (last line of stdout)
        try:
            # Get last non-empty line (which should be the JSON output)
            output_lines = result.stdout.strip().split('\n')
            json_line = output_lines[-1]

            print(f"[quick_inference] Parsing JSON from last line ({len(json_line)} chars)")
            sys.stdout.flush()

            inference_result = json.loads(json_line)
        except json.JSONDecodeError as e:
            print(f"[quick_inference ERROR] Failed to parse JSON: {e}")
            print(f"[quick_inference] Last line: {output_lines[-1][:500] if output_lines else 'N/A'}")
            print(f"[quick_inference] Full stdout ({len(result.stdout)} chars):")
            print(result.stdout[-2000:])  # Last 2000 chars
            sys.stdout.flush()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to parse inference result: {str(e)}"
            )

        # Encode result images as Base64
        result_image_fields = [
            'predicted_mask_path',
            'overlay_path',
            'upscaled_image_path'
        ]

        for field in result_image_fields:
            path_key = field
            base64_key = field.replace('_path', '_base64')

            if inference_result.get(path_key):
                image_path = inference_result[path_key]

                if os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as img_file:
                            img_bytes = img_file.read()
                            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

                        # Add Base64 to result
                        inference_result[base64_key] = img_base64
                        print(f"[quick_inference] Encoded {path_key} as Base64 ({len(img_base64)} chars)")

                        # Remove file path from result
                        del inference_result[path_key]

                        # Delete temp result image
                        os.remove(image_path)
                        print(f"[quick_inference] Deleted temp file: {image_path}")

                    except Exception as e:
                        print(f"[quick_inference WARNING] Failed to encode {path_key}: {e}")

        sys.stdout.flush()
        return inference_result

    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=504,
            detail="Inference timed out (max 5 minutes)"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[quick_inference ERROR] {e}")
        traceback.print_exc()
        sys.stdout.flush()
        raise HTTPException(
            status_code=500,
            detail=f"Inference error: {str(e)}"
        )
    finally:
        # Cleanup temp input image
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
            print(f"[quick_inference] Cleaned up temp image: {temp_image_path}")
            sys.stdout.flush()


@app.get("/config-schema")
async def get_config_schema(task_type: str):
    """
    Return configuration schema for this framework and task type.

    This endpoint provides the advanced configuration options available
    for training jobs, allowing the frontend to dynamically generate
    configuration forms.

    Args:
        task_type: Task type (e.g., image_classification, object_detection)

    Returns:
        ConfigSchema with fields organized by groups
    """
    try:
        # Import config schemas (lightweight, no torch dependencies)
        # Use conditional imports to handle frameworks that don't have schemas yet
        from config_schemas import get_timm_schema, get_ultralytics_schema

        # Map framework to schema getter
        schema_map = {
            'timm': get_timm_schema,
            'ultralytics': get_ultralytics_schema,
        }

        # Try to import huggingface schema if available
        try:
            from config_schemas import get_huggingface_schema
            schema_map['huggingface'] = get_huggingface_schema
        except ImportError:
            pass  # huggingface schema not implemented yet

        schema_getter = schema_map.get(FRAMEWORK.lower())
        if not schema_getter:
            raise HTTPException(
                status_code=404,
                detail=f"No config schema available for framework '{FRAMEWORK}'"
            )

        # Get schema
        schema = schema_getter()

        # Use the built-in to_dict() method for proper serialization
        schema_dict = schema.to_dict()

        return {
            "framework": FRAMEWORK,
            "task_type": task_type,
            "schema": schema_dict
        }

    except ImportError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Config schemas not available in this Training Service: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting config schema: {e}"
        )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
