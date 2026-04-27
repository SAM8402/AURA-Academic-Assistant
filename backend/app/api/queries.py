"""
API endpoints for query/doubt management.

Provides endpoints for:
- Listing queries (with filtering by status, category)
- Creating new queries
- Getting query details with responses
- Adding responses to queries
- Updating query status
"""

from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query as QueryParam
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from typing import Optional, List
from datetime import datetime, UTC

from config.db import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.query import Query, QueryResponse
from app.schemas.query_schema import QueryStatus, QueryPriority, QueryCategory
from pydantic import BaseModel, Field


router = APIRouter(prefix="/queries", tags=["Queries"])


# ============================================================================
# Pydantic Schemas
# ============================================================================


class QueryCreate(BaseModel):
    """Schema for creating a new query."""
    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10)
    category: Optional[QueryCategory] = QueryCategory.GENERAL
    priority: Optional[QueryPriority] = QueryPriority.MEDIUM
    tags: Optional[List[str]] = []


class QueryResponseCreate(BaseModel):
    """Schema for creating a query response."""
    content: str = Field(..., min_length=5)
    is_solution: Optional[bool] = False


class QueryStatusUpdate(BaseModel):
    """Schema for updating query status."""
    status: QueryStatus
    resolution_notes: Optional[str] = None


# ============================================================================
# Helper Functions
# ============================================================================


def serialize_query(query: Query, include_responses: bool = False) -> dict:
    """
    Serialize a Query object to dictionary.

    Args:
        query: Query model instance
        include_responses: Whether to include responses

    Returns:
        Serialized query dictionary
    """
    result = {
        "id": query.id,
        "title": query.title,
        "description": query.description,
        "status": query.status.value if hasattr(query.status, 'value') else str(query.status),
        "priority": query.priority.value if hasattr(query.priority, 'value') else str(query.priority),
        "category": query.category.value if hasattr(query.category, 'value') else str(query.category),
        "student_id": query.student_id,
        "student_name": query.student.full_name if query.student else "Unknown",
        "assigned_to_id": query.assigned_to_id,
        "assigned_to_name": query.assigned_to.full_name if query.assigned_to else None,
        "tags": query.tags or [],
        "view_count": query.view_count,
        "resolution_notes": query.resolution_notes,
        "created_at": query.created_at.isoformat() if query.created_at else None,
        "updated_at": query.updated_at.isoformat() if query.updated_at else None,
        "resolved_at": query.resolved_at.isoformat() if query.resolved_at else None,
        "response_count": len(query.responses) if query.responses else 0
    }

    if include_responses and query.responses:
        result["responses"] = [
            {
                "id": r.id,
                "content": r.content,
                "is_solution": r.is_solution,
                "user_id": r.user_id,
                "user_name": r.user.full_name if r.user else "Unknown",
                "user_role": r.user.role.value if r.user and hasattr(r.user.role, 'value') else "unknown",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None
            }
            for r in query.responses
        ]

    return result


# ============================================================================
# Query Endpoints
# ============================================================================


@router.get(
    "/",
    summary="List queries",
    description="""
    Get list of queries with filtering options.

    Students see only their own queries.
    TAs/Instructors/Admins see all queries.
    """
)
async def list_queries(
    status_filter: Optional[str] = QueryParam(None, alias="status", description="Filter by status (OPEN, IN_PROGRESS, RESOLVED)"),
    category: Optional[str] = QueryParam(None, description="Filter by category"),
    priority: Optional[str] = QueryParam(None, description="Filter by priority"),
    limit: int = QueryParam(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = QueryParam(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of queries with filters."""
    try:
        # Base query
        query = db.query(Query)

        # Students see only their queries
        if current_user.role.value == "student":
            query = query.filter(Query.student_id == current_user.id)

        # Apply filters
        if status_filter:
            try:
                # QueryStatus enum uses uppercase names with lowercase values
                # e.g., QueryStatus.OPEN = "open"
                status_enum = QueryStatus[status_filter.upper()]
                query = query.filter(Query.status == status_enum)
            except KeyError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status_filter}. Valid values: OPEN, IN_PROGRESS, RESOLVED"
                )

        if category:
            try:
                category_enum = QueryCategory[category.upper()]
                query = query.filter(Query.category == category_enum)
            except KeyError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid category: {category}. Valid values: TECHNICAL, CONCEPTUAL, ASSIGNMENT, EXAM, GENERAL, OTHER"
                )

        if priority:
            try:
                priority_enum = QueryPriority[priority.upper()]
                query = query.filter(Query.priority == priority_enum)
            except KeyError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid priority: {priority}. Valid values: LOW, MEDIUM, HIGH, URGENT"
                )

        # Get total count
        total = query.count()

        # Apply ordering and pagination
        queries = query.order_by(desc(Query.created_at)).offset(offset).limit(limit).all()

        return {
            "queries": [serialize_query(q) for q in queries],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch queries: {str(e)}"
        )


@router.get(
    "/{query_id}",
    summary="Get query details",
    description="Get detailed information about a specific query including all responses."
)
async def get_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific query with responses."""
    try:
        # Fetch query with eager loading of responses
        query = db.query(Query).options(joinedload(Query.responses)).filter(Query.id == query_id).first()

        if not query:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )

        # Check access permission
        if current_user.role.value == "student" and query.student_id != current_user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this query"
            )

        # Increment view count
        query.view_count += 1
        db.commit()

        return serialize_query(query, include_responses=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch query: {str(e)}"
        )


@router.post(
    "/",
    summary="Create new query",
    description="Create a new query/doubt. Only students can create queries.",
    status_code=http_status.HTTP_201_CREATED
)
async def create_query(
    query_data: QueryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new query."""
    try:
        # Only students can create queries
        if current_user.role.value != "student":
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only students can create queries"
            )

        # Create query
        new_query = Query(
            title=query_data.title,
            description=query_data.description,
            category=query_data.category,
            priority=query_data.priority,
            tags=query_data.tags or [],
            student_id=current_user.id,
            status=QueryStatus.OPEN
        )

        db.add(new_query)
        db.commit()
        db.refresh(new_query)

        return {
            "message": "Query created successfully",
            "query": serialize_query(new_query)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create query: {str(e)}"
        )


@router.post(
    "/{query_id}/response",
    summary="Add response to query",
    description="Add a response to a query. TAs/Instructors can mark responses as solutions.",
    status_code=http_status.HTTP_201_CREATED
)
async def add_query_response(
    query_id: int,
    response_data: QueryResponseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a response to a query."""
    try:
        # Fetch query
        query = db.query(Query).filter(Query.id == query_id).first()

        if not query:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )

        # Create response
        new_response = QueryResponse(
            query_id=query_id,
            user_id=current_user.id,
            content=response_data.content,
            is_solution=response_data.is_solution and current_user.role.value in ["ta", "instructor", "admin"]
        )

        db.add(new_response)

        # Update query status if it's the first response
        if query.status == QueryStatus.OPEN and not query.responses:
            query.status = QueryStatus.IN_PROGRESS

        # If marked as solution, resolve query
        if new_response.is_solution:
            query.status = QueryStatus.RESOLVED
            query.resolved_at = datetime.now(UTC)

        db.commit()
        db.refresh(new_response)

        return {
            "message": "Response added successfully",
            "response": {
                "id": new_response.id,
                "content": new_response.content,
                "is_solution": new_response.is_solution,
                "created_at": new_response.created_at.isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add response: {str(e)}"
        )


@router.put(
    "/{query_id}/status",
    summary="Update query status",
    description="Update the status of a query. Only TAs/Instructors/Admins can update status."
)
async def update_query_status(
    query_id: int,
    status_data: QueryStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update query status."""
    try:
        # Only TAs/Instructors/Admins can update status
        if current_user.role.value not in ["ta", "instructor", "admin"]:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Only TAs/Instructors/Admins can update query status"
            )

        # Fetch query
        query = db.query(Query).filter(Query.id == query_id).first()

        if not query:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Query {query_id} not found"
            )

        # Update status
        query.status = status_data.status

        if status_data.resolution_notes:
            query.resolution_notes = status_data.resolution_notes

        if status_data.status == QueryStatus.RESOLVED:
            query.resolved_at = datetime.now(UTC)

        db.commit()

        return {
            "message": "Query status updated successfully",
            "query": serialize_query(query)
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update query status: {str(e)}"
        )


@router.get(
    "/statistics/summary",
    summary="Get query statistics",
    description="Get statistics about queries (total, by status, by category, etc.)"
)
async def get_query_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get query statistics."""
    try:
        # Base query - students see only their stats
        base_query = db.query(Query)
        if current_user.role.value == "student":
            base_query = base_query.filter(Query.student_id == current_user.id)

        # Total queries
        total_queries = base_query.count()

        # By status
        open_count = base_query.filter(Query.status == QueryStatus.OPEN).count()
        in_progress_count = base_query.filter(Query.status == QueryStatus.IN_PROGRESS).count()
        resolved_count = base_query.filter(Query.status == QueryStatus.RESOLVED).count()

        # By priority
        high_priority_count = base_query.filter(Query.priority == QueryPriority.HIGH).count()

        # By category
        category_stats = db.query(
            Query.category,
            func.count(Query.id).label('count')
        )

        if current_user.role.value == "student":
            category_stats = category_stats.filter(Query.student_id == current_user.id)

        category_stats = category_stats.group_by(Query.category).all()

        return {
            "total_queries": total_queries,
            "by_status": {
                "open": open_count,
                "in_progress": in_progress_count,
                "resolved": resolved_count
            },
            "by_priority": {
                "high": high_priority_count
            },
            "by_category": {
                cat.value if hasattr(cat, 'value') else str(cat): count
                for cat, count in category_stats
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )
