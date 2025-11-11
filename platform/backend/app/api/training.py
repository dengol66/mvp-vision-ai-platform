"""
Training Job API Endpoints

Provides CRUD operations for training jobs and handles callbacks from Training Services.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import TrainingJob, TrainingMetric, JobStatus
from app.db.session import get_db
from app.schemas.training import (
    TrainingJobCreate,
    TrainingJobResponse,
    TrainingUpdate,
    TrainingMetricResponse,
)

router = APIRouter()


# ==================== Training Job CRUD ====================


@router.post("/jobs", response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
async def create_training_job(
    job_data: TrainingJobCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new training job.

    The job is created in PENDING status. Call POST /jobs/{id}/start to begin training.
    """
    # Construct callback URL
    callback_url = f"{settings.BACKEND_BASE_URL}/api/v1/training/jobs/{{job_id}}/callback"

    # Create job
    job = TrainingJob(
        user_id=job_data.user_id,
        model_name=job_data.model_name,
        framework=job_data.framework,
        dataset_s3_uri=job_data.dataset_s3_uri,
        config=job_data.config,
        status=JobStatus.PENDING,
        callback_url=callback_url.format(job_id="{id}"),  # Placeholder, will be filled later
    )

    db.add(job)
    await db.flush()  # Get the generated ID

    # Update callback_url with actual job ID
    job.callback_url = callback_url.format(job_id=str(job.id))
    await db.commit()
    await db.refresh(job)

    return job


@router.get("/jobs", response_model=List[TrainingJobResponse])
async def list_training_jobs(
    user_id: str | None = None,
    status_filter: JobStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    List training jobs with optional filters.
    """
    query = select(TrainingJob)

    # Apply filters
    if user_id:
        query = query.where(TrainingJob.user_id == user_id)
    if status_filter:
        query = query.where(TrainingJob.status == status_filter)

    # Order by created_at desc
    query = query.order_by(TrainingJob.created_at.desc())

    # Pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return jobs


@router.get("/jobs/{job_id}", response_model=TrainingJobResponse)
async def get_training_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific training job by ID."""
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    return job


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_training_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a training job.

    Sets status to CANCELLED. The Training Service should stop execution.
    """
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} status",
        )

    job.status = JobStatus.CANCELLED
    job.updated_at = datetime.utcnow()
    await db.commit()

    return None


# ==================== Callback Endpoint ====================


@router.post("/jobs/{job_id}/callback", status_code=status.HTTP_200_OK)
async def training_callback(
    job_id: UUID,
    update: TrainingUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Receive training updates from Training Service.

    This endpoint is called by Training Services to report progress, metrics, and status changes.
    """
    # Get job
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    # Update job status
    job.status = update.status
    job.progress = update.progress
    job.updated_at = datetime.utcnow()

    if update.message:
        job.message = update.message

    if update.checkpoint_s3_uri:
        job.checkpoint_s3_uri = update.checkpoint_s3_uri

    if update.error:
        job.error = update.error

    # Set timestamps
    if update.status == JobStatus.RUNNING and not job.started_at:
        job.started_at = datetime.utcnow()

    if update.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        job.completed_at = datetime.utcnow()

    # Store metrics if provided
    if update.metrics:
        metric = TrainingMetric(
            job_id=job_id,
            epoch=update.metrics.get("epoch", 0),
            step=update.metrics.get("step"),
            loss=update.metrics.get("loss"),
            accuracy=update.metrics.get("accuracy"),
            metrics=update.metrics,  # Store all metrics as JSON
        )
        db.add(metric)

    await db.commit()

    return {"status": "ok", "job_id": str(job_id)}


# ==================== Metrics ====================


@router.get("/jobs/{job_id}/metrics", response_model=List[TrainingMetricResponse])
async def get_training_metrics(
    job_id: UUID,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Get training metrics for a specific job."""
    # Verify job exists
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Training job {job_id} not found",
        )

    # Get metrics
    query = (
        select(TrainingMetric)
        .where(TrainingMetric.job_id == job_id)
        .order_by(TrainingMetric.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    metrics = result.scalars().all()

    return metrics
