"""Projects API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.database import get_db
from app.db.models import Project, TrainingJob, User
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithExperimentsResponse,
)
from app.utils.dependencies import get_current_active_user

router = APIRouter(tags=["projects"])


@router.post("", response_model=ProjectResponse)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new project."""

    # Check if project with same name already exists for this user
    existing = db.query(Project).filter(
        Project.name == project.name,
        Project.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project with this name already exists")

    db_project = Project(
        name=project.name,
        description=project.description,
        task_type=project.task_type,
        user_id=current_user.id,  # Set the owner
    )

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project


@router.get("", response_model=List[ProjectWithExperimentsResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all projects owned by the current user with experiment counts."""

    # Query projects with experiment counts - only for current user
    projects = (
        db.query(
            Project,
            func.count(TrainingJob.id).label("experiment_count")
        )
        .filter(Project.user_id == current_user.id)  # Filter by current user
        .outerjoin(TrainingJob, TrainingJob.project_id == Project.id)
        .group_by(Project.id)
        .all()
    )

    # Format response
    result = []
    for project, exp_count in projects:
        result.append(
            ProjectWithExperimentsResponse(
                id=project.id,
                name=project.name,
                description=project.description,
                task_type=project.task_type,
                created_at=project.created_at,
                updated_at=project.updated_at,
                experiment_count=exp_count,
            )
        )

    return result


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific project by ID."""

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a project."""

    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if db_project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this project")

    # Update fields if provided
    if project_update.name is not None:
        # Check if new name conflicts with existing project for this user
        existing = db.query(Project).filter(
            Project.name == project_update.name,
            Project.id != project_id,
            Project.user_id == current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Project with this name already exists")
        db_project.name = project_update.name

    if project_update.description is not None:
        db_project.description = project_update.description

    if project_update.task_type is not None:
        db_project.task_type = project_update.task_type

    db.commit()
    db.refresh(db_project)

    return db_project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a project and all its experiments."""

    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if db_project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")

    # Prevent deletion of default "Uncategorized" project
    if db_project.name == "Uncategorized":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the default 'Uncategorized' project"
        )

    # Get experiment count
    exp_count = db.query(TrainingJob).filter(TrainingJob.project_id == project_id).count()

    # Delete project (cascade will delete experiments)
    db.delete(db_project)
    db.commit()

    return {
        "message": f"Project '{db_project.name}' deleted successfully",
        "deleted_experiments": exp_count
    }


@router.get("/{project_id}/experiments")
def get_project_experiments(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all experiments for a specific project."""

    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check permission
    if project.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this project")

    # Get all experiments for this project
    experiments = (
        db.query(TrainingJob)
        .filter(TrainingJob.project_id == project_id)
        .order_by(TrainingJob.created_at.desc())
        .all()
    )

    from app.schemas.training import TrainingJobResponse
    return [TrainingJobResponse.from_orm(exp) for exp in experiments]
