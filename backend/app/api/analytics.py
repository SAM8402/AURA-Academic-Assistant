"""
Analytics API endpoints for admin dashboard.

Provides comprehensive analytics and metrics for system monitoring.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case, extract
from datetime import datetime, UTC, timedelta
from typing import Optional

from app.core.db import get_db
from app.models.user import User
from app.schemas.user_schema import UserRole
from app.models.query import Query as QueryModel, QueryResponse
from app.models.knowledge import KnowledgeSource
from app.models.chat_session import ChatSession
from app.schemas.analytics_schema import (
    OverviewMetrics,
    FAQsResponse,
    FAQItem,
    PerformanceMetrics,
    SentimentData,
    UsageStats,
    DetailedUsageResponse,
    UserActivityByRole,
    UsageByCategory
)
from app.api.dependencies import get_current_user, require_role

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=OverviewMetrics,
    summary="Get overall system metrics",
    description="""
    Get comprehensive overview metrics for the admin dashboard.

    **Metrics included:**
    - Total counts (users, queries, responses, knowledge sources)
    - Activity metrics (active users, queries by period)
    - Query status breakdown
    - Average resolution time

    **Access:** Admin only
    """
)
async def get_overview_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get overall system metrics."""

    now = datetime.now(UTC)
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)

    # Total counts
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_queries = db.query(func.count(QueryModel.id)).scalar() or 0
    total_responses = db.query(func.count(QueryResponse.id)).scalar() or 0
    total_knowledge_sources = db.query(func.count(KnowledgeSource.id)).filter(
        KnowledgeSource.is_active == True
    ).scalar() or 0
    total_chat_sessions = db.query(func.count(ChatSession.id)).scalar() or 0

    # Active users (based on query activity)
    active_users_today = db.query(func.count(func.distinct(QueryModel.student_id))).filter(
        QueryModel.created_at >= today_start
    ).scalar() or 0

    active_users_week = db.query(func.count(func.distinct(QueryModel.student_id))).filter(
        QueryModel.created_at >= week_start
    ).scalar() or 0

    # Queries by period
    queries_today = db.query(func.count(QueryModel.id)).filter(
        QueryModel.created_at >= today_start
    ).scalar() or 0

    queries_week = db.query(func.count(QueryModel.id)).filter(
        QueryModel.created_at >= week_start
    ).scalar() or 0

    # Query status counts
    from app.schemas.query_schema import QueryStatus

    open_queries = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.OPEN
    ).scalar() or 0

    resolved_queries = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.RESOLVED
    ).scalar() or 0

    # Average resolution time (for resolved queries)
    resolved_with_time = db.query(
        func.avg(
            func.julianday(QueryModel.updated_at) - func.julianday(QueryModel.created_at)
        ) * 24  # Convert days to hours
    ).filter(
        QueryModel.status == QueryStatus.RESOLVED,
        QueryModel.updated_at.isnot(None)
    ).scalar()

    average_resolution_time_hours = round(resolved_with_time, 2) if resolved_with_time else None

    return OverviewMetrics(
        total_users=total_users,
        total_queries=total_queries,
        total_responses=total_responses,
        total_knowledge_sources=total_knowledge_sources,
        total_chat_sessions=total_chat_sessions,
        active_users_today=active_users_today,
        active_users_week=active_users_week,
        queries_today=queries_today,
        queries_week=queries_week,
        open_queries=open_queries,
        resolved_queries=resolved_queries,
        average_resolution_time_hours=average_resolution_time_hours
    )


@router.get(
    "/faqs",
    response_model=FAQsResponse,
    summary="Get frequently asked questions",
    description="""
    Get top FAQs and recurring questions based on query patterns.

    **Features:**
    - Top questions by frequency
    - Category breakdown
    - Last asked timestamp
    - Common resolution status

    **Query Parameters:**
    - `limit`: Number of FAQs to return (default: 20)
    - `days`: Time period in days (default: 30)

    **Access:** Admin only
    """
)
async def get_faqs(
    limit: int = Query(default=20, ge=1, le=100, description="Number of FAQs to return"),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get frequently asked questions."""

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Group by similar titles (case-insensitive)
    # Count occurrences and get metadata
    faq_data = db.query(
        func.lower(QueryModel.title).label('question_lower'),
        QueryModel.title.label('question'),
        func.count(QueryModel.id).label('count'),
        QueryModel.category.label('category'),
        func.max(QueryModel.created_at).label('last_asked'),
        QueryModel.status.label('status')
    ).filter(
        QueryModel.created_at >= cutoff_date
    ).group_by(
        func.lower(QueryModel.title),
        QueryModel.title,
        QueryModel.category,
        QueryModel.status
    ).order_by(
        desc('count')
    ).limit(limit).all()

    # Get total unique questions
    total_unique = db.query(func.count(func.distinct(func.lower(QueryModel.title)))).filter(
        QueryModel.created_at >= cutoff_date
    ).scalar() or 0

    faqs = [
        FAQItem(
            question=row.question,
            count=row.count,
            category=row.category,
            last_asked=row.last_asked,
            status=row.status.value if hasattr(row.status, 'value') else str(row.status)
        )
        for row in faq_data
    ]

    return FAQsResponse(
        total_unique_questions=total_unique,
        faqs=faqs,
        time_period=f"last_{days}_days"
    )


@router.get(
    "/performance",
    response_model=PerformanceMetrics,
    summary="Get performance metrics",
    description="""
    Get response time and resolution rate metrics.

    **Metrics included:**
    - Average response time (first response)
    - Average resolution time
    - Median resolution time
    - Resolution rate percentage
    - Query status breakdown
    - Response coverage statistics

    **Access:** Admin only
    """
)
async def get_performance_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get performance and resolution metrics."""

    from app.schemas.query_schema import QueryStatus

    # Query status counts
    status_counts = db.query(
        QueryModel.status,
        func.count(QueryModel.id)
    ).group_by(QueryModel.status).all()

    status_dict = {status.value if hasattr(status, 'value') else str(status): count
                   for status, count in status_counts}

    open_count = status_dict.get(QueryStatus.OPEN.value, 0)
    in_progress_count = status_dict.get(QueryStatus.IN_PROGRESS.value, 0)
    resolved_count = status_dict.get(QueryStatus.RESOLVED.value, 0)
    closed_count = status_dict.get(QueryStatus.CLOSED.value, 0)

    total_queries = sum(status_dict.values())
    resolution_rate = (resolved_count / total_queries * 100) if total_queries > 0 else 0

    # Average time to first response
    queries_with_responses = db.query(
        QueryModel.id,
        QueryModel.created_at,
        func.min(QueryResponse.created_at).label('first_response_at')
    ).join(
        QueryResponse, QueryModel.id == QueryResponse.query_id
    ).group_by(
        QueryModel.id, QueryModel.created_at
    ).subquery()

    avg_response_time = db.query(
        func.avg(
            (func.julianday(queries_with_responses.c.first_response_at) -
             func.julianday(queries_with_responses.c.created_at)) * 24 * 60  # minutes
        )
    ).scalar()

    # Average resolution time (for resolved queries)
    avg_resolution_time = db.query(
        func.avg(
            (func.julianday(QueryModel.updated_at) - func.julianday(QueryModel.created_at)) * 24
        )
    ).filter(
        QueryModel.status == QueryStatus.RESOLVED,
        QueryModel.updated_at.isnot(None)
    ).scalar()

    # Median resolution time (approximate using percentile)
    # For SQLite, we'll use a simpler approach
    resolved_times = db.query(
        (func.julianday(QueryModel.updated_at) - func.julianday(QueryModel.created_at)) * 24
    ).filter(
        QueryModel.status == QueryStatus.RESOLVED,
        QueryModel.updated_at.isnot(None)
    ).order_by(
        (func.julianday(QueryModel.updated_at) - func.julianday(QueryModel.created_at))
    ).all()

    median_resolution_time = None
    if resolved_times:
        times = [t[0] for t in resolved_times if t[0] is not None]
        if times:
            median_idx = len(times) // 2
            median_resolution_time = times[median_idx]

    # Response coverage
    queries_with_resp = db.query(func.count(func.distinct(QueryResponse.query_id))).scalar() or 0
    queries_without_resp = total_queries - queries_with_resp

    # Average responses per query
    total_responses = db.query(func.count(QueryResponse.id)).scalar() or 0
    avg_responses = (total_responses / total_queries) if total_queries > 0 else 0

    return PerformanceMetrics(
        average_response_time_minutes=round(avg_response_time, 2) if avg_response_time else None,
        average_resolution_time_hours=round(avg_resolution_time, 2) if avg_resolution_time else None,
        median_resolution_time_hours=round(median_resolution_time, 2) if median_resolution_time else None,
        resolution_rate_percentage=round(resolution_rate, 2),
        open_query_count=open_count,
        in_progress_count=in_progress_count,
        resolved_count=resolved_count,
        closed_count=closed_count,
        queries_with_responses=queries_with_resp,
        queries_without_responses=queries_without_resp,
        average_responses_per_query=round(avg_responses, 2)
    )


@router.get(
    "/sentiment",
    response_model=SentimentData,
    summary="Get sentiment analysis",
    description="""
    Get aggregate feedback sentiment analysis.

    **Note:** This endpoint provides estimated sentiment based on query status
    and response patterns. For accurate sentiment, integrate with a feedback system.

    **Sentiment estimation:**
    - Positive: Resolved queries with responses
    - Neutral: In-progress queries
    - Negative: Open queries without responses (aging)

    **Access:** Admin only
    """
)
async def get_sentiment_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get aggregate feedback sentiment."""

    from app.schemas.query_schema import QueryStatus

    # Estimate sentiment based on query outcomes
    # Positive: Resolved queries
    positive_count = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.RESOLVED
    ).scalar() or 0

    # Neutral: In-progress or recently created open queries
    neutral_count = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status.in_([QueryStatus.IN_PROGRESS, QueryStatus.CLOSED])
    ).scalar() or 0

    # Negative: Open queries older than 24 hours with no responses
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    negative_count = db.query(func.count(QueryModel.id)).filter(
        and_(
            QueryModel.status == QueryStatus.OPEN,
            QueryModel.created_at < cutoff,
            ~QueryModel.responses.any()
        )
    ).scalar() or 0

    total_feedback = positive_count + neutral_count + negative_count

    if total_feedback > 0:
        positive_pct = (positive_count / total_feedback) * 100
        neutral_pct = (neutral_count / total_feedback) * 100
        negative_pct = (negative_count / total_feedback) * 100
    else:
        positive_pct = neutral_pct = negative_pct = 0

    # Estimate average rating (1-5 scale)
    # Positive = 5, Neutral = 3, Negative = 2
    if total_feedback > 0:
        avg_rating = (positive_count * 5 + neutral_count * 3 + negative_count * 2) / total_feedback
    else:
        avg_rating = None

    return SentimentData(
        positive_count=positive_count,
        neutral_count=neutral_count,
        negative_count=negative_count,
        total_feedback=total_feedback,
        positive_percentage=round(positive_pct, 2),
        neutral_percentage=round(neutral_pct, 2),
        negative_percentage=round(negative_pct, 2),
        average_rating=round(avg_rating, 2) if avg_rating else None
    )


@router.get(
    "/usage",
    response_model=DetailedUsageResponse,
    summary="Get usage statistics",
    description="""
    Get comprehensive usage statistics including:

    **User Activity:**
    - Active users by time period (today, week, month)
    - User breakdown by role

    **Session Statistics:**
    - Total chat sessions
    - Sessions by time period
    - Average session length

    **API Usage:**
    - Estimated API calls
    - Knowledge base queries
    - Chatbot interactions

    **Patterns:**
    - Peak usage hours
    - User growth rate
    - Usage by category

    **Access:** Admin only
    """
)
async def get_usage_statistics(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    """Get active users, API calls, and session stats."""

    now = datetime.now(UTC)
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)

    # Active users by period (based on query activity)
    active_today = db.query(func.count(func.distinct(QueryModel.student_id))).filter(
        QueryModel.created_at >= today_start
    ).scalar() or 0

    active_week = db.query(func.count(func.distinct(QueryModel.student_id))).filter(
        QueryModel.created_at >= week_start
    ).scalar() or 0

    active_month = db.query(func.count(func.distinct(QueryModel.student_id))).filter(
        QueryModel.created_at >= month_start
    ).scalar() or 0

    # Chat sessions
    total_sessions = db.query(func.count(ChatSession.id)).scalar() or 0

    sessions_today = db.query(func.count(ChatSession.id)).filter(
        ChatSession.created_at >= today_start
    ).scalar() or 0

    sessions_week = db.query(func.count(ChatSession.id)).filter(
        ChatSession.created_at >= week_start
    ).scalar() or 0

    # Knowledge base and chatbot usage
    kb_queries = db.query(func.count(KnowledgeSource.id)).filter(
        KnowledgeSource.is_active == True
    ).scalar() or 0

    chatbot_interactions = total_sessions

    # Estimate API calls (queries + responses + sessions * avg interactions)
    total_queries = db.query(func.count(QueryModel.id)).scalar() or 0
    total_responses = db.query(func.count(QueryResponse.id)).scalar() or 0

    api_calls_estimated = total_queries + total_responses + (chatbot_interactions * 5)
    api_calls_today = int(api_calls_estimated * (sessions_today / max(total_sessions, 1)))
    api_calls_week = int(api_calls_estimated * (sessions_week / max(total_sessions, 1)))

    # Peak usage hour (based on query creation time)
    peak_hour_data = db.query(
        extract('hour', QueryModel.created_at).label('hour'),
        func.count(QueryModel.id).label('count')
    ).group_by('hour').order_by(desc('count')).first()

    peak_hour = int(peak_hour_data.hour) if peak_hour_data else None

    # User growth rate (compare last month to previous month)
    two_months_ago = now - timedelta(days=60)
    users_last_month = db.query(func.count(User.id)).filter(
        User.created_at >= month_start
    ).scalar() or 0

    users_prev_month = db.query(func.count(User.id)).filter(
        and_(
            User.created_at >= two_months_ago,
            User.created_at < month_start
        )
    ).scalar() or 1  # Avoid division by zero

    growth_rate = ((users_last_month - users_prev_month) / users_prev_month * 100) if users_prev_month > 0 else 0

    # Users by role
    users_by_role = db.query(
        User.role,
        func.count(User.id).label('count')
    ).group_by(User.role).all()

    # Get active users by role (based on query activity in the last week)
    active_users_by_role = {}
    for role, _ in users_by_role:
        active_count = db.query(func.count(func.distinct(User.id))).join(
            QueryModel, User.id == QueryModel.student_id
        ).filter(
            User.role == role,
            QueryModel.created_at >= week_start
        ).scalar() or 0
        active_users_by_role[role] = active_count

    role_breakdown = [
        UserActivityByRole(
            role=role.value if hasattr(role, 'value') else str(role),
            count=count,
            active_count=active_users_by_role.get(role, 0)
        )
        for role, count in users_by_role
    ]

    # Queries by category
    queries_by_cat = db.query(
        QueryModel.category,
        func.count(QueryModel.id).label('count')
    ).group_by(QueryModel.category).all()

    total_cat_queries = sum(count for _, count in queries_by_cat)
    category_breakdown = [
        UsageByCategory(
            category=category,
            count=count,
            percentage=round((count / total_cat_queries * 100), 2) if total_cat_queries > 0 else 0
        )
        for category, count in queries_by_cat
    ]

    usage_stats = UsageStats(
        active_users_today=active_today,
        active_users_week=active_week,
        active_users_month=active_month,
        total_chat_sessions=total_sessions,
        chat_sessions_today=sessions_today,
        chat_sessions_week=sessions_week,
        average_session_length_minutes=None,  # Would need session duration tracking
        api_calls_today=api_calls_today,
        api_calls_week=api_calls_week,
        knowledge_base_queries_count=kb_queries,
        chatbot_interactions_count=chatbot_interactions,
        peak_usage_hour=peak_hour,
        user_growth_rate_percentage=round(growth_rate, 2)
    )

    return DetailedUsageResponse(
        usage_stats=usage_stats,
        users_by_role=role_breakdown,
        queries_by_category=category_breakdown,
        time_period="last_30_days"
    )
