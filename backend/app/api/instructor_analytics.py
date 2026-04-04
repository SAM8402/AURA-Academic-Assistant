"""
Instructor Analytics API endpoints.

Provides discussion summaries, sentiment analysis, and topic clustering
for the instructor dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case, extract, or_
from datetime import datetime, UTC, timedelta
from typing import Optional, List
from collections import defaultdict
import re

from app.core.db import get_db
from app.models.user import User
from app.schemas.user_schema import UserRole
from app.models.query import Query as QueryModel, QueryResponse
from app.models.chat_session import ChatSession
from app.schemas.query_schema import QueryStatus, QueryCategory
from app.schemas.instructor_analytics_schema import (
    DiscussionMetric,
    SentimentBreakdown,
    DiscussionTopic,
    SentimentTrendData,
    SentimentDriverData,
    SentimentInsights,
    InstructorDiscussionSummaryResponse,
    TopicCluster,
    TopicClusteringResponse,
    RealTimeSentimentPoint,
    RealTimeSentimentResponse
)
from app.api.dependencies import get_current_user, require_role

router = APIRouter(prefix="/instructor", tags=["Instructor Analytics"])


def calculate_sentiment_from_query(query: QueryModel) -> str:
    """
    Calculate sentiment based on query status and response patterns.

    Returns: 'positive', 'neutral', or 'negative'
    """
    # Resolved queries = positive sentiment
    if query.status == QueryStatus.RESOLVED:
        return 'positive'

    # In-progress queries = neutral
    if query.status == QueryStatus.IN_PROGRESS:
        return 'neutral'

    # Closed queries = neutral (completed but not marked resolved)
    if query.status == QueryStatus.CLOSED:
        return 'neutral'

    # Open queries older than 24 hours without responses = negative
    if query.status == QueryStatus.OPEN:
        age_hours = (datetime.now(UTC) - query.created_at).total_seconds() / 3600
        if age_hours > 24 and len(query.responses) == 0:
            return 'negative'
        elif age_hours > 48:
            return 'negative'
        return 'neutral'

    # Escalated = negative
    if query.status == QueryStatus.ESCALATED:
        return 'negative'

    return 'neutral'


def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text for topic clustering."""
    # Common programming/academic keywords
    keywords = []
    text_lower = text.lower()

    # Define keyword patterns
    patterns = [
        r'\b(recursion|recursive)\b',
        r'\b(sorting|sort)\b',
        r'\b(search|searching)\b',
        r'\b(tree|trees|binary tree)\b',
        r'\b(graph|graphs)\b',
        r'\b(array|arrays)\b',
        r'\b(linked list|linkedlist)\b',
        r'\b(stack|stacks)\b',
        r'\b(queue|queues)\b',
        r'\b(hash|hashing|hashtable)\b',
        r'\b(pointer|pointers)\b',
        r'\b(memory|allocation)\b',
        r'\b(algorithm|algorithms)\b',
        r'\b(complexity|big-o|time complexity)\b',
        r'\b(database|sql|query)\b',
        r'\b(api|rest|endpoint)\b',
        r'\b(assignment|homework)\b',
        r'\b(exam|quiz|test)\b',
        r'\b(deadline|due date)\b',
        r'\b(error|bug|issue)\b',
        r'\b(python|java|javascript|c\+\+)\b',
    ]

    for pattern in patterns:
        if re.search(pattern, text_lower):
            match = re.search(pattern, text_lower)
            if match:
                keywords.append(match.group(1).title())

    return list(set(keywords))[:5]  # Return max 5 unique keywords


@router.get(
    "/discussion-summaries",
    response_model=InstructorDiscussionSummaryResponse,
    summary="Get discussion summaries for instructor dashboard",
    description="""
    Get comprehensive discussion analytics including:

    **Overview Metrics:**
    - Total discussions count
    - Active threads
    - Average sentiment
    - Unresolved queries

    **Sentiment Analysis:**
    - Trend over time (monthly)
    - Sentiment by topic/category
    - Key insights by sentiment type

    **Discussion Topics:**
    - Top discussions with sentiment breakdown
    - Participant information
    - Thread counts

    **Access:** Instructor, TA, or Admin
    """
)
async def get_discussion_summaries(
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of topics to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.INSTRUCTOR, UserRole.TA, UserRole.ADMIN]))
):
    """Get discussion summaries with sentiment analysis."""

    now = datetime.now(UTC)
    cutoff_date = now - timedelta(days=days)

    # ========== OVERVIEW METRICS ==========

    # Total discussions (queries)
    total_discussions = db.query(func.count(QueryModel.id)).filter(
        QueryModel.created_at >= cutoff_date
    ).scalar() or 0

    # Active threads (open + in_progress)
    active_threads = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status.in_([QueryStatus.OPEN, QueryStatus.IN_PROGRESS]),
        QueryModel.created_at >= cutoff_date
    ).scalar() or 0

    # Unresolved queries (open only)
    unresolved = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.OPEN
    ).scalar() or 0

    # Calculate average sentiment
    all_queries = db.query(QueryModel).filter(
        QueryModel.created_at >= cutoff_date
    ).all()

    sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}
    for q in all_queries:
        sentiment = calculate_sentiment_from_query(q)
        sentiment_counts[sentiment] += 1

    total_sentiment = sum(sentiment_counts.values())
    avg_sentiment_pct = round(
        (sentiment_counts['positive'] / total_sentiment * 100) if total_sentiment > 0 else 0
    )

    metrics = [
        DiscussionMetric(
            title="Total Discussions",
            value=str(total_discussions),
            subtitle=f"Last {days} days"
        ),
        DiscussionMetric(
            title="Active Threads",
            value=str(active_threads),
            subtitle="Open & In Progress"
        ),
        DiscussionMetric(
            title="Average Sentiment",
            value=f"{avg_sentiment_pct}%",
            subtitle="Positive"
        ),
        DiscussionMetric(
            title="Unresolved Queries",
            value=str(unresolved),
            subtitle="Needs attention"
        ),
    ]

    # ========== TOP DISCUSSION TOPICS ==========

    top_queries = db.query(QueryModel).filter(
        QueryModel.created_at >= cutoff_date
    ).order_by(desc(QueryModel.created_at)).limit(limit).all()

    topics = []
    for q in top_queries:
        # Get participants (student + responders)
        participants = []
        if q.student:
            participants.append(q.student.full_name.split()[0] if q.student.full_name else "Student")

        for resp in q.responses[:3]:  # Limit to first 3 responders
            if resp.user and resp.user.full_name:
                name = resp.user.full_name.split()[0]
                if name not in participants:
                    participants.append(name)

        # Calculate sentiment for this query
        sentiment = calculate_sentiment_from_query(q)

        # Create sentiment breakdown (simplified for single query)
        if sentiment == 'positive':
            sent_breakdown = SentimentBreakdown(positive=80, neutral=15, negative=5)
        elif sentiment == 'negative':
            sent_breakdown = SentimentBreakdown(positive=20, neutral=30, negative=50)
        else:
            sent_breakdown = SentimentBreakdown(positive=40, neutral=45, negative=15)

        topics.append(DiscussionTopic(
            id=q.id,
            title=q.title[:100],  # Truncate long titles
            description=q.description[:200] if q.description else "No description",
            participants=participants[:5],  # Limit participants shown
            sentiment=sent_breakdown,
            thread_count=len(q.responses),
            category=q.category.value if hasattr(q.category, 'value') else str(q.category) if q.category else None,
            created_at=q.created_at,
            status=q.status.value if hasattr(q.status, 'value') else str(q.status)
        ))

    # ========== SENTIMENT TREND DATA (Monthly) ==========

    # Get last 6 months of data
    months_data = []
    for i in range(5, -1, -1):
        month_start = now - timedelta(days=30 * (i + 1))
        month_end = now - timedelta(days=30 * i)

        month_queries = db.query(QueryModel).filter(
            QueryModel.created_at >= month_start,
            QueryModel.created_at < month_end
        ).all()

        month_sentiments = {'positive': 0, 'neutral': 0, 'negative': 0}
        for q in month_queries:
            sentiment = calculate_sentiment_from_query(q)
            month_sentiments[sentiment] += 1

        month_total = sum(month_sentiments.values()) or 1
        months_data.append({
            'month': month_start.strftime('%b'),
            'positive': round(month_sentiments['positive'] / month_total * 100),
            'neutral': round(month_sentiments['neutral'] / month_total * 100),
            'negative': round(month_sentiments['negative'] / month_total * 100)
        })

    trends = SentimentTrendData(
        months=[m['month'] for m in months_data],
        positive=[m['positive'] for m in months_data],
        neutral=[m['neutral'] for m in months_data],
        negative=[m['negative'] for m in months_data]
    )

    # ========== SENTIMENT DRIVERS (By Category) ==========

    category_sentiments = defaultdict(lambda: {'positive': 0, 'negative': 0, 'total': 0})

    for q in all_queries:
        cat = q.category.value if hasattr(q.category, 'value') else str(q.category) if q.category else 'other'
        sentiment = calculate_sentiment_from_query(q)
        category_sentiments[cat]['total'] += 1
        if sentiment == 'positive':
            category_sentiments[cat]['positive'] += 1
        elif sentiment == 'negative':
            category_sentiments[cat]['negative'] += 1

    # Get top 5 categories
    sorted_cats = sorted(category_sentiments.items(), key=lambda x: x[1]['total'], reverse=True)[:5]

    drivers = SentimentDriverData(
        labels=[cat.replace('_', ' ').title() for cat, _ in sorted_cats],
        positive=[data['positive'] for _, data in sorted_cats],
        negative=[data['negative'] for _, data in sorted_cats]
    )

    # ========== SENTIMENT INSIGHTS ==========

    positive_insights = []
    neutral_insights = []
    negative_insights = []

    # Generate insights based on actual data
    resolved_count = sentiment_counts['positive']
    if resolved_count > 0:
        positive_insights.append(f"{resolved_count} queries resolved successfully")

    quick_resolutions = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.RESOLVED,
        QueryModel.created_at >= cutoff_date,
        (func.julianday(QueryModel.updated_at) - func.julianday(QueryModel.created_at)) * 24 < 24
    ).scalar() or 0

    if quick_resolutions > 0:
        positive_insights.append(f"{quick_resolutions} queries resolved within 24 hours")

    # Add more dynamic insights
    if total_discussions > 10:
        positive_insights.append("Active student engagement observed")

    in_progress = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.IN_PROGRESS,
        QueryModel.created_at >= cutoff_date
    ).scalar() or 0

    if in_progress > 0:
        neutral_insights.append(f"{in_progress} queries currently being addressed")

    recent_queries = db.query(func.count(QueryModel.id)).filter(
        QueryModel.created_at >= now - timedelta(days=7)
    ).scalar() or 0

    if recent_queries > 0:
        neutral_insights.append(f"{recent_queries} new queries in the last week")

    # Negative insights
    old_unresolved = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.OPEN,
        QueryModel.created_at < now - timedelta(days=3)
    ).scalar() or 0

    if old_unresolved > 0:
        negative_insights.append(f"{old_unresolved} queries unresolved for more than 3 days")

    no_response = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.OPEN,
        ~QueryModel.responses.any()
    ).scalar() or 0

    if no_response > 0:
        negative_insights.append(f"{no_response} queries without any response")

    escalated = db.query(func.count(QueryModel.id)).filter(
        QueryModel.status == QueryStatus.ESCALATED
    ).scalar() or 0

    if escalated > 0:
        negative_insights.append(f"{escalated} queries escalated requiring attention")

    # Ensure we have at least some insights
    if not positive_insights:
        positive_insights.append("System is operating normally")
    if not neutral_insights:
        neutral_insights.append("No pending items requiring immediate attention")
    if not negative_insights:
        negative_insights.append("No critical issues detected")

    insights = SentimentInsights(
        positive=positive_insights[:5],
        neutral=neutral_insights[:5],
        negative=negative_insights[:5]
    )

    return InstructorDiscussionSummaryResponse(
        metrics=metrics,
        topics=topics,
        trends=trends,
        drivers=drivers,
        insights=insights,
        generated_at=now
    )


@router.get(
    "/topic-clusters",
    response_model=TopicClusteringResponse,
    summary="Get topic clustering analysis",
    description="""
    Analyze queries and group them into topic clusters based on keywords
    and content similarity.

    **Features:**
    - Automatic topic detection
    - Keyword extraction
    - Sentiment score per cluster
    - Sample queries for each cluster

    **Access:** Instructor, TA, or Admin
    """
)
async def get_topic_clusters(
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.INSTRUCTOR, UserRole.TA, UserRole.ADMIN]))
):
    """Get topic clustering for queries."""

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Get all queries in time period
    queries = db.query(QueryModel).filter(
        QueryModel.created_at >= cutoff_date
    ).all()

    # Group queries by extracted keywords
    keyword_groups = defaultdict(list)

    for q in queries:
        text = f"{q.title} {q.description or ''}"
        keywords = extract_keywords(text)

        if keywords:
            primary_keyword = keywords[0]
            keyword_groups[primary_keyword].append(q)
        else:
            # Use category as fallback
            cat = q.category.value if hasattr(q.category, 'value') else str(q.category) if q.category else 'General'
            keyword_groups[cat].append(q)

    # Create clusters
    clusters = []
    for keyword, group_queries in sorted(keyword_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        # Calculate average sentiment
        sentiments = [calculate_sentiment_from_query(q) for q in group_queries]
        positive_ratio = sentiments.count('positive') / len(sentiments) if sentiments else 0

        # Get all keywords from this cluster
        all_keywords = set()
        for q in group_queries:
            text = f"{q.title} {q.description or ''}"
            all_keywords.update(extract_keywords(text))

        clusters.append(TopicCluster(
            cluster_name=keyword,
            query_count=len(group_queries),
            keywords=list(all_keywords)[:5],
            sentiment_score=round(positive_ratio, 2),
            sample_queries=[q.title[:80] for q in group_queries[:3]]
        ))

    return TopicClusteringResponse(
        clusters=clusters,
        total_queries_analyzed=len(queries),
        time_period=f"last_{days}_days"
    )


@router.get(
    "/realtime-sentiment",
    response_model=RealTimeSentimentResponse,
    summary="Get real-time sentiment data",
    description="""
    Get sentiment data points for real-time chart updates.

    Returns hourly sentiment breakdowns for the specified period.

    **Access:** Instructor, TA, or Admin
    """
)
async def get_realtime_sentiment(
    hours: int = Query(default=24, ge=1, le=168, description="Hours of data to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.INSTRUCTOR, UserRole.TA, UserRole.ADMIN]))
):
    """Get real-time sentiment data for live charts."""

    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=hours)

    # Get queries in time range
    queries = db.query(QueryModel).filter(
        QueryModel.created_at >= cutoff
    ).order_by(QueryModel.created_at).all()

    # Group by hour
    hourly_data = defaultdict(lambda: {'positive': 0, 'neutral': 0, 'negative': 0})

    for q in queries:
        hour_key = q.created_at.replace(minute=0, second=0, microsecond=0)
        sentiment = calculate_sentiment_from_query(q)
        hourly_data[hour_key][sentiment] += 1

    # Create data points
    data_points = []
    for hour in sorted(hourly_data.keys()):
        data = hourly_data[hour]
        total = sum(data.values())
        data_points.append(RealTimeSentimentPoint(
            timestamp=hour,
            positive=data['positive'],
            neutral=data['neutral'],
            negative=data['negative'],
            total=total
        ))

    # Calculate current sentiment
    recent_queries = db.query(QueryModel).filter(
        QueryModel.created_at >= now - timedelta(hours=1)
    ).all()

    recent_sentiments = {'positive': 0, 'neutral': 0, 'negative': 0}
    for q in recent_queries:
        sentiment = calculate_sentiment_from_query(q)
        recent_sentiments[sentiment] += 1

    total_recent = sum(recent_sentiments.values()) or 1
    current_sentiment = SentimentBreakdown(
        positive=round(recent_sentiments['positive'] / total_recent * 100, 1),
        neutral=round(recent_sentiments['neutral'] / total_recent * 100, 1),
        negative=round(recent_sentiments['negative'] / total_recent * 100, 1)
    )

    # Determine trend direction
    if len(data_points) >= 2:
        recent_positive = sum(dp.positive for dp in data_points[-3:])
        earlier_positive = sum(dp.positive for dp in data_points[:3])

        if recent_positive > earlier_positive:
            trend = "improving"
        elif recent_positive < earlier_positive:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return RealTimeSentimentResponse(
        data_points=data_points,
        current_sentiment=current_sentiment,
        trend_direction=trend
    )


@router.get(
    "/discussion/{query_id}",
    summary="Get detailed discussion thread",
    description="Get full details of a specific discussion/query with all responses."
)
async def get_discussion_detail(
    query_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.INSTRUCTOR, UserRole.TA, UserRole.ADMIN]))
):
    """Get detailed discussion thread."""

    query = db.query(QueryModel).filter(QueryModel.id == query_id).first()

    if not query:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # Build response with full details
    responses = []
    for resp in query.responses:
        responses.append({
            "id": resp.id,
            "content": resp.content,
            "author": resp.user.full_name if resp.user else "Unknown",
            "author_role": resp.user.role.value if resp.user and hasattr(resp.user.role, 'value') else "user",
            "is_solution": resp.is_solution,
            "created_at": resp.created_at.isoformat() if resp.created_at else None
        })

    sentiment = calculate_sentiment_from_query(query)

    return {
        "id": query.id,
        "title": query.title,
        "description": query.description,
        "status": query.status.value if hasattr(query.status, 'value') else str(query.status),
        "category": query.category.value if hasattr(query.category, 'value') else str(query.category) if query.category else None,
        "priority": query.priority.value if hasattr(query.priority, 'value') else str(query.priority) if query.priority else None,
        "student": {
            "id": query.student.id if query.student else None,
            "name": query.student.full_name if query.student else "Unknown",
            "email": query.student.email if query.student else None
        },
        "responses": responses,
        "response_count": len(responses),
        "sentiment": sentiment,
        "tags": query.tags or [],
        "created_at": query.created_at.isoformat() if query.created_at else None,
        "updated_at": query.updated_at.isoformat() if query.updated_at else None
    }
