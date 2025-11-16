"""
Model Export and Deployment API endpoints.

Provides endpoints for:
- Export: Converting trained checkpoints to production formats
- Deployment: Deploying exported models to various targets
- Platform Inference: Running inference on deployed models
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import json
import logging
from datetime import datetime
from pathlib import Path

from app.db.database import get_db
from app.db import models
from app.schemas import export as export_schemas

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/export", tags=["export"])


# ========== Export Capabilities ==========

# Framework capability matrix (static for now, can be loaded from trainer services later)
EXPORT_CAPABILITIES = {
    "ultralytics": {
        "object_detection": {
            "supported_formats": [
                {
                    "format": "onnx",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": ["dynamic_quantization"]
                },
                {
                    "format": "tensorrt",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": ["fp16", "int8"]
                },
                {
                    "format": "coreml",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": []
                },
                {
                    "format": "torchscript",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": []
                },
                {
                    "format": "openvino",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": []
                }
            ],
            "default_format": "onnx"
        },
        "instance_segmentation": {
            "supported_formats": [
                {
                    "format": "onnx",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": ["dynamic_quantization"]
                },
                {
                    "format": "tensorrt",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": ["fp16"]
                }
            ],
            "default_format": "onnx"
        },
        "pose_estimation": {
            "supported_formats": [
                {
                    "format": "onnx",
                    "supported": True,
                    "native_support": True,
                    "requires_conversion": False,
                    "optimization_options": ["dynamic_quantization"]
                }
            ],
            "default_format": "onnx"
        }
    },
    "timm": {
        "image_classification": {
            "supported_formats": [
                {
                    "format": "onnx",
                    "supported": True,
                    "native_support": False,
                    "requires_conversion": True,
                    "optimization_options": ["dynamic_quantization"]
                },
                {
                    "format": "torchscript",
                    "supported": True,
                    "native_support": False,
                    "requires_conversion": True,
                    "optimization_options": []
                }
            ],
            "default_format": "onnx"
        }
    }
}


@router.get("/capabilities", response_model=export_schemas.ExportCapabilitiesResponse)
async def get_export_capabilities(
    framework: str = Query(..., description="Framework name (ultralytics, timm, etc.)"),
    task_type: str = Query(..., description="Task type (object_detection, image_classification, etc.)"),
    db: Session = Depends(get_db)
):
    """
    Get export capabilities for a specific framework and task type.

    Returns supported export formats, optimization options, and recommended defaults.

    Args:
        framework: Framework name
        task_type: Task type
        db: Database session

    Returns:
        ExportCapabilitiesResponse with supported formats and options
    """
    # Check if framework is supported
    if framework not in EXPORT_CAPABILITIES:
        raise HTTPException(
            status_code=404,
            detail=f"Framework '{framework}' not supported. Supported: {list(EXPORT_CAPABILITIES.keys())}"
        )

    # Check if task type is supported for this framework
    if task_type not in EXPORT_CAPABILITIES[framework]:
        raise HTTPException(
            status_code=404,
            detail=f"Task type '{task_type}' not supported for framework '{framework}'. "
                   f"Supported: {list(EXPORT_CAPABILITIES[framework].keys())}"
        )

    capabilities = EXPORT_CAPABILITIES[framework][task_type]

    return export_schemas.ExportCapabilitiesResponse(
        framework=framework,
        task_type=task_type,
        supported_formats=[
            export_schemas.ExportFormatCapability(**fmt)
            for fmt in capabilities["supported_formats"]
        ],
        default_format=capabilities["default_format"]
    )


# ========== Export Job Endpoints ==========

@router.post("/jobs", response_model=export_schemas.ExportJobResponse, status_code=201)
async def create_export_job(
    request: export_schemas.ExportJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new export job to convert a trained checkpoint to production format.

    Supports ONNX, TensorRT, CoreML, TFLite, TorchScript, OpenVINO formats
    with optional optimizations (quantization, pruning) and validation.

    Args:
        request: Export job configuration
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        ExportJobResponse with job metadata
    """
    # Check if training job exists
    training_job = db.query(models.TrainingJob).filter(
        models.TrainingJob.id == request.training_job_id
    ).first()

    if not training_job:
        raise HTTPException(
            status_code=404,
            detail=f"Training job {request.training_job_id} not found"
        )

    # Determine checkpoint path
    checkpoint_path = request.checkpoint_path
    if not checkpoint_path:
        # Use best checkpoint from training job
        checkpoint_path = training_job.best_checkpoint_path
        if not checkpoint_path:
            raise HTTPException(
                status_code=400,
                detail="No checkpoint specified and training job has no best checkpoint"
            )

    # Check if checkpoint exists (skip validation for now - will be validated in subprocess)
    # checkpoint_file = Path(checkpoint_path)
    # if not checkpoint_file.exists():
    #     raise HTTPException(
    #         status_code=404,
    #         detail=f"Checkpoint not found: {checkpoint_path}"
    #     )

    # Determine next version number
    existing_exports = db.query(models.ExportJob).filter(
        models.ExportJob.training_job_id == request.training_job_id
    ).all()
    next_version = len(existing_exports) + 1

    # If set_as_default, unset any existing default
    if request.set_as_default:
        db.query(models.ExportJob).filter(
            models.ExportJob.training_job_id == request.training_job_id,
            models.ExportJob.is_default == True
        ).update({"is_default": False})

    # Create export job record
    export_job = models.ExportJob(
        training_job_id=request.training_job_id,
        export_format=request.export_format,
        checkpoint_path=checkpoint_path,
        version=next_version,
        is_default=request.set_as_default or (next_version == 1),  # First export is default
        framework=training_job.framework,
        task_type=training_job.task_type,
        model_name=training_job.model_name,
        export_config=request.export_config.model_dump() if request.export_config else None,
        optimization_config=request.optimization_config.model_dump() if request.optimization_config else None,
        validation_config=request.validation_config.model_dump() if request.validation_config else None,
        status=models.ExportJobStatus.PENDING,
        created_at=datetime.utcnow()
    )

    db.add(export_job)
    db.commit()
    db.refresh(export_job)

    # TODO: Launch background task to run export
    # background_tasks.add_task(run_export_task, export_job.id)

    logger.info(f"Created export job {export_job.id} for training job {request.training_job_id}")

    return export_schemas.ExportJobResponse.model_validate(export_job)


@router.get("/training/{training_job_id}/exports", response_model=export_schemas.ExportJobListResponse)
async def get_export_jobs(
    training_job_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all export jobs for a training job.

    Returns export jobs ordered by version (descending).

    Args:
        training_job_id: Training job ID
        skip: Number of results to skip (pagination)
        limit: Maximum number of results to return
        db: Database session

    Returns:
        ExportJobListResponse with all export jobs
    """
    # Check if training job exists
    training_job = db.query(models.TrainingJob).filter(
        models.TrainingJob.id == training_job_id
    ).first()

    if not training_job:
        raise HTTPException(
            status_code=404,
            detail=f"Training job {training_job_id} not found"
        )

    # Query export jobs
    query = db.query(models.ExportJob).filter(
        models.ExportJob.training_job_id == training_job_id
    ).order_by(models.ExportJob.version.desc())

    total_count = query.count()
    export_jobs = query.offset(skip).limit(limit).all()

    export_jobs_data = [
        export_schemas.ExportJobResponse.model_validate(job)
        for job in export_jobs
    ]

    return export_schemas.ExportJobListResponse(
        training_job_id=training_job_id,
        total_count=total_count,
        export_jobs=export_jobs_data
    )


@router.get("/jobs/{export_job_id}", response_model=export_schemas.ExportJobResponse)
async def get_export_job(
    export_job_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific export job.

    Returns export job details including status, results, and file size.

    Args:
        export_job_id: Export job ID
        db: Database session

    Returns:
        ExportJobResponse with job details
    """
    export_job = db.query(models.ExportJob).filter(
        models.ExportJob.id == export_job_id
    ).first()

    if not export_job:
        raise HTTPException(
            status_code=404,
            detail=f"Export job {export_job_id} not found"
        )

    return export_schemas.ExportJobResponse.model_validate(export_job)


# ========== Deployment Endpoints (Placeholder) ==========

@router.post("/deployments", response_model=export_schemas.DeploymentResponse, status_code=201)
async def create_deployment(
    request: export_schemas.DeploymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new deployment for an exported model.

    Supports deployment types: download, platform_endpoint, edge_package, container.

    Args:
        request: Deployment configuration
        background_tasks: FastAPI background tasks
        db: Database session

    Returns:
        DeploymentResponse with deployment metadata
    """
    # Check if export job exists
    export_job = db.query(models.ExportJob).filter(
        models.ExportJob.id == request.export_job_id
    ).first()

    if not export_job:
        raise HTTPException(
            status_code=404,
            detail=f"Export job {request.export_job_id} not found"
        )

    # Check if export is completed
    if export_job.status != models.ExportJobStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Export job {request.export_job_id} is not completed (status: {export_job.status})"
        )

    # Create deployment record
    deployment = models.DeploymentTarget(
        export_job_id=request.export_job_id,
        training_job_id=export_job.training_job_id,
        deployment_type=request.deployment_type,
        deployment_name=request.deployment_name,
        deployment_config=request.deployment_config.model_dump() if request.deployment_config else None,
        cpu_limit=request.cpu_limit,
        memory_limit=request.memory_limit,
        gpu_enabled=request.gpu_enabled,
        status=models.DeploymentStatus.PENDING,
        created_at=datetime.utcnow()
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    # TODO: Launch background task to deploy
    # background_tasks.add_task(deploy_task, deployment.id)

    logger.info(f"Created deployment {deployment.id} for export job {request.export_job_id}")

    return export_schemas.DeploymentResponse.model_validate(deployment)


@router.get("/deployments", response_model=export_schemas.DeploymentListResponse)
async def list_deployments(
    training_job_id: Optional[int] = Query(None, description="Filter by training job ID"),
    export_job_id: Optional[int] = Query(None, description="Filter by export job ID"),
    deployment_type: Optional[str] = Query(None, description="Filter by deployment type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    List deployments with optional filters.

    Args:
        training_job_id: Filter by training job ID
        export_job_id: Filter by export job ID
        deployment_type: Filter by deployment type
        status: Filter by status
        skip: Number of results to skip (pagination)
        limit: Maximum number of results to return
        db: Database session

    Returns:
        DeploymentListResponse with matching deployments
    """
    query = db.query(models.DeploymentTarget)

    if training_job_id:
        query = query.filter(models.DeploymentTarget.training_job_id == training_job_id)

    if export_job_id:
        query = query.filter(models.DeploymentTarget.export_job_id == export_job_id)

    if deployment_type:
        query = query.filter(models.DeploymentTarget.deployment_type == deployment_type)

    if status:
        query = query.filter(models.DeploymentTarget.status == status)

    query = query.order_by(models.DeploymentTarget.created_at.desc())

    total_count = query.count()
    deployments = query.offset(skip).limit(limit).all()

    deployments_data = [
        export_schemas.DeploymentResponse.model_validate(dep)
        for dep in deployments
    ]

    return export_schemas.DeploymentListResponse(
        total_count=total_count,
        deployments=deployments_data
    )


@router.get("/deployments/{deployment_id}", response_model=export_schemas.DeploymentResponse)
async def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific deployment.

    Returns deployment details including endpoint URL, usage stats, and status.

    Args:
        deployment_id: Deployment ID
        db: Database session

    Returns:
        DeploymentResponse with deployment details
    """
    deployment = db.query(models.DeploymentTarget).filter(
        models.DeploymentTarget.id == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment {deployment_id} not found"
        )

    return export_schemas.DeploymentResponse.model_validate(deployment)
