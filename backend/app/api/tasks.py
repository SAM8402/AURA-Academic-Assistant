"""
Task Management API Endpoints for AURA.

Provides endpoints for monitoring and managing background tasks.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from config.db import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.models.enums import TaskStatusEnum, TaskTypeEnum
from app.schemas.knowledge_schema import TaskOut


router = APIRouter(prefix="/tasks", tags=["Background Tasks"])


@router.get("/", response_model=list[TaskOut])
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all background tasks with pagination and filters.

    - **task_type**: Filter by EMBEDDING or QUERY
    - **status**: Filter by PENDING, IN_PROGRESS, COMPLETED, or FAILED
    """
    try:
        query = db.query(Task)

        # Apply filters
        if task_type:
            query = query.filter(Task.task_type == task_type)
        if status:
            query = query.filter(Task.status == status)

        # Apply pagination
        query = query.order_by(Task.created_at.desc())
        skip = (page - 1) * size
        tasks = query.offset(skip).limit(size).all()

        return tasks

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tasks: {str(e)}"
        )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get details of a specific task by ID.

    Returns complete information including status, errors, and metadata.
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a task record.

    Only completed or failed tasks can be deleted.
    """
    task = db.query(Task).filter(Task.id == task_id).first()

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    if task.status in [TaskStatusEnum.PENDING.value, TaskStatusEnum.IN_PROGRESS.value]:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete task that is pending or in progress"
        )

    try:
        db.delete(task)
        db.commit()
        return None

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete task: {str(e)}"
        )


@router.get("/statistics/summary")
async def get_task_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get summary statistics for all tasks.

    Returns counts by status and type.
    """
    try:
        total_tasks = db.query(Task).count()
        pending = db.query(Task).filter(Task.status == TaskStatusEnum.PENDING.value).count()
        in_progress = db.query(Task).filter(Task.status == TaskStatusEnum.IN_PROGRESS.value).count()
        completed = db.query(Task).filter(Task.status == TaskStatusEnum.COMPLETED.value).count()
        failed = db.query(Task).filter(Task.status == TaskStatusEnum.FAILED.value).count()

        embedding_tasks = db.query(Task).filter(Task.task_type == TaskTypeEnum.EMBEDDING.value).count()
        query_tasks = db.query(Task).filter(Task.task_type == TaskTypeEnum.QUERY.value).count()

        return {
            "total": total_tasks,
            "by_status": {
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "failed": failed
            },
            "by_type": {
                "embedding": embedding_tasks,
                "query": query_tasks
            },
            "success_rate": round((completed / total_tasks * 100), 2) if total_tasks > 0 else 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve task statistics: {str(e)}"
        )
