"""Admin API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.database import get_db
from app.db.models import Project, TrainingJob, User
from app.schemas.project import ProjectResponse
from app.schemas.user import UserResponse
from app.utils.dependencies import get_current_active_user

router = APIRouter(tags=["admin"])


def require_admin(current_user: User = Depends(get_current_active_user)):
    """Dependency to check if user is admin or superadmin."""
    if current_user.system_role not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required"
        )
    return current_user


@router.get("/projects")
def list_all_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all projects in the system (admin only)."""

    # Query all projects with user info and experiment counts
    projects = (
        db.query(
            Project,
            User,
            func.count(TrainingJob.id).label("experiment_count")
        )
        .outerjoin(User, User.id == Project.user_id)
        .outerjoin(TrainingJob, TrainingJob.project_id == Project.id)
        .group_by(Project.id)
        .all()
    )

    # Format response
    result = []
    for project, user, exp_count in projects:
        result.append({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "task_type": project.task_type,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "experiment_count": exp_count,
            "owner_id": project.user_id,
            "owner_name": user.full_name if user else None,
            "owner_email": user.email if user else None,
        })

    return result


@router.get("/users")
def list_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """List all users in the system (admin only)."""

    # Query all users with project counts
    users = (
        db.query(
            User,
            func.count(Project.id).label("project_count")
        )
        .outerjoin(Project, Project.user_id == User.id)
        .group_by(User.id)
        .all()
    )

    # Format response
    result = []
    for user, project_count in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "company": user.company,
            "company_custom": user.company_custom,
            "division": user.division,
            "division_custom": user.division_custom,
            "department": user.department,
            "phone_number": user.phone_number,
            "system_role": user.system_role,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "project_count": project_count,
        })

    return result
