"""
Query/Doubt database models.

This module defines models for student queries, doubts, and their responses.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, func, JSON
from sqlalchemy.orm import relationship
from config.db import Base
from app.schemas.query_schema import QueryStatus, QueryPriority, QueryCategory


class Query(Base):
    """
    Query model representing student doubts/questions.

    Attributes:
        id: Primary key
        title: Query title/summary
        description: Detailed description
        status: Current status (open, in_progress, resolved, etc.)
        priority: Priority level (low, medium, high, urgent)
        category: Query category
        student_id: ID of student who created the query
        assigned_to_id: ID of TA/instructor assigned to handle
        course_id: Associated course (optional)
        tags: List of tags for searchability
        resolution_notes: Notes added when resolving
        view_count: Number of views
        created_at: Creation timestamp
        updated_at: Last update timestamp
        resolved_at: Resolution timestamp

    Relationships:
        student: Many-to-one with User (as student)
        assigned_to: Many-to-one with User (as TA/instructor)
        responses: One-to-many with QueryResponse

    Example:
        >>> query = Query(
        ...     title="How to implement binary search?",
        ...     description="I'm having trouble...",
        ...     student_id=1,
        ...     category=QueryCategory.TECHNICAL
        ... )
    """
    __tablename__ = "queries"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Query Content
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=False)

    # Status and Priority
    status = Column(
        SQLEnum(QueryStatus),
        nullable=False,
        default=QueryStatus.OPEN,
        index=True
    )
    priority = Column(
        SQLEnum(QueryPriority),
        nullable=False,
        default=QueryPriority.MEDIUM,
        index=True
    )
    category = Column(
        SQLEnum(QueryCategory),
        nullable=False,
        default=QueryCategory.GENERAL,
        index=True
    )

    # Foreign Keys
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    course_id = Column(Integer, nullable=True, index=True)  # For future course model

    # Metadata
    tags = Column(JSON, default=list)  # Store as JSON array
    resolution_notes = Column(Text, nullable=True)
    view_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    student = relationship("User", foreign_keys=[student_id], back_populates="queries")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], back_populates="assigned_queries")
    responses = relationship("QueryResponse", back_populates="query", cascade="all, delete-orphan", order_by="QueryResponse.created_at")

    def __repr__(self) -> str:
        """String representation of Query."""
        return f"<Query(id={self.id}, title='{self.title[:30]}...', status='{self.status.value}')>"


class QueryResponse(Base):
    """
    QueryResponse model representing responses to queries.

    Attributes:
        id: Primary key
        query_id: Associated query ID
        user_id: User who responded (TA/instructor/student)
        content: Response content
        is_solution: Whether this is the accepted solution
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        query: Many-to-one with Query
        user: Many-to-one with User

    Example:
        >>> response = QueryResponse(
        ...     query_id=1,
        ...     user_id=2,
        ...     content="Here's how you implement...",
        ...     is_solution=True
        ... )
    """
    __tablename__ = "query_responses"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Keys
    query_id = Column(Integer, ForeignKey("queries.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Content
    content = Column(Text, nullable=False)
    is_solution = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    query = relationship("Query", back_populates="responses")
    user = relationship("User", back_populates="query_responses")

    def __repr__(self) -> str:
        """String representation of QueryResponse."""
        return f"<QueryResponse(id={self.id}, query_id={self.query_id}, is_solution={self.is_solution})>"
