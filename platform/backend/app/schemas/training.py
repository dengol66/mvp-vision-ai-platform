"""
Training API Schemas

Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import JobStatus


# ==================== Request Schemas ====================


class TrainingJobCreate(BaseModel):
    """Request schema for creating a training job."""

    user_id: str = Field(..., min_length=1, max_length=255)
    model_name: str = Field(..., min_length=1, max_length=255, examples=["yolo11n"])
    framework: str = Field(..., min_length=1, max_length=100, examples=["ultralytics"])
    dataset_s3_uri: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        examples=["s3://vision-platform/datasets/my-dataset/"],
    )
    config: Optional[Dict[str, Any]] = Field(
        default=None,
        examples=[{"epochs": 50, "batch_size": 16}],
    )


class TrainingUpdate(BaseModel):
    """Callback schema for training service to update job status."""

    job_id: str
    status: JobStatus
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    message: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None  # e.g., {"epoch": 10, "loss": 0.5}
    checkpoint_s3_uri: Optional[str] = None
    error: Optional[str] = None


# ==================== Response Schemas ====================


class TrainingJobResponse(BaseModel):
    """Response schema for training job."""

    id: UUID
    user_id: str
    model_name: str
    framework: str
    dataset_s3_uri: str
    config: Optional[Dict[str, Any]]
    status: JobStatus
    progress: float
    message: Optional[str]
    checkpoint_s3_uri: Optional[str]
    error: Optional[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TrainingMetricResponse(BaseModel):
    """Response schema for training metric."""

    id: int
    job_id: UUID
    epoch: int
    step: Optional[int]
    loss: Optional[float]
    accuracy: Optional[float]
    metrics: Optional[Dict[str, Any]]
    created_at: datetime

    model_config = {"from_attributes": True}
