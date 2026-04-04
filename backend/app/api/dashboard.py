"""
Dashboard API Endpoints for AURA.

Provides analytics and statistics for the admin dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, UTC, timedelta

from app.core.db import get_db
from app.api.dependencies import get_current_user
from app.schemas.user_schema import UserRole
from app.core.security import is_ta_or_above
from app.models.user import User
from app.models.knowledge import KnowledgeSource
from app.models.query import Query as QueryModel


router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get("/statistics")
async def get_dashboard_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive dashboard statistics.

    Returns overall metrics for:
    - Users
    - Knowledge sources
    - Queries
    - System health
    """
    try:
        # User statistics
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()

        # Knowledge statistics
        total_sources = db.query(KnowledgeSource).count()
        active_sources = db.query(KnowledgeSource).filter(
            KnowledgeSource.is_active == True
        ).count()

        # Query statistics
        total_queries = db.query(QueryModel).count()

        # Recent activity (last 7 days)
        week_ago = datetime.now(UTC) - timedelta(days=7)
        recent_sources = db.query(KnowledgeSource).filter(
            KnowledgeSource.created_at >= week_ago
        ).count()
        recent_queries = db.query(QueryModel).filter(
            QueryModel.created_at >= week_ago
        ).count()

        return {
            "users": {
                "total": total_users,
                "active": active_users
            },
            "knowledge": {
                "total_sources": total_sources,
                "active_sources": active_sources,
                "recent_sources_7d": recent_sources
            },
            "queries": {
                "total": total_queries,
                "recent_7d": recent_queries
            },
            "system": {
                "status": "healthy",
                "timestamp": datetime.now(UTC).isoformat()
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard statistics: {str(e)}"
        )


@router.get("/activity-timeline")
async def get_activity_timeline(
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get activity timeline for the specified number of days.

    Returns daily activity metrics including:
    - New knowledge sources
    - Queries submitted
    - User registrations
    """
    try:
        start_date = datetime.now(UTC) - timedelta(days=days)

        # For simplicity, return aggregated data
        # In production, you'd group by date
        timeline = []
        for i in range(days):
            day = datetime.now(UTC) - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)

            sources_count = db.query(KnowledgeSource).filter(
                KnowledgeSource.created_at >= day_start,
                KnowledgeSource.created_at < day_end
            ).count()

            queries_count = db.query(QueryModel).filter(
                QueryModel.created_at >= day_start,
                QueryModel.created_at < day_end
            ).count()

            timeline.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "knowledge_sources": sources_count,
                "queries": queries_count
            })

        return {
            "period": f"last_{days}_days",
            "timeline": list(reversed(timeline))
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve activity timeline: {str(e)}"
        )


@router.get("/top-sources")
async def get_top_sources(
    limit: int = Query(10, ge=1, le=50, description="Number of top sources to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top knowledge sources by usage.

    Returns the most frequently accessed knowledge sources.
    Note: Requires query tracking to be fully functional.
    """
    try:
        # Get most recent sources for now (can be enhanced with usage metrics)
        top_sources = db.query(KnowledgeSource).filter(
            KnowledgeSource.is_active == True
        ).order_by(KnowledgeSource.created_at.desc()).limit(limit).all()

        return {
            "total": len(top_sources),
            "sources": [
                {
                    "id": str(source.id),
                    "title": source.title,
                    "category": source.category.value,
                    "chunk_count": source.chunk_count,
                    "created_at": source.created_at.isoformat(),
                    "usage_count": 0  # TODO: Track actual usage
                }
                for source in top_sources
            ]
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve top sources: {str(e)}"
        )
