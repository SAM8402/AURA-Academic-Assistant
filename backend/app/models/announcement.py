"""
Announcement database model.

This module defines the Announcement model for system-wide and course-specific announcements.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from config.db import Base
from app.schemas.announcement_schema import AnnouncementType, AnnouncementTarget


class Announcement(Base):
    """
    Announcement model representing system and course announcements.

    Attributes:
        id: Primary key
        title: Announcement title
        content: Announcement content
        announcement_type: Type (general, urgent, deadline, etc.)
        target_audience: Who should see this (all, students, tas, etc.)
        course_id: Course ID for course-specific announcements
        created_by_id: ID of creator (admin/instructor)
        is_pinned: Pin to top of announcements
        is_active: Whether announcement is active
        view_count: Number of views
        expires_at: Expiration date (optional)
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        created_by: Many-to-one with User

    Example:
        >>> announcement = Announcement(
        ...     title="Midterm Exam Schedule",
        ...     content="The exam will be held...",
        ...     announcement_type=AnnouncementType.DEADLINE,
        ...     target_audience=AnnouncementTarget.STUDENTS,
        ...     created_by_id=1
        ... )
    """
    __tablename__ = "announcements"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Content
    title = Column(String(200), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Type and Targeting
    announcement_type = Column(
        SQLEnum(AnnouncementType),
        nullable=False,
        default=AnnouncementType.GENERAL,
        index=True
    )
    target_audience = Column(
        SQLEnum(AnnouncementTarget),
        nullable=False,
        default=AnnouncementTarget.ALL,
        index=True
    )

    # Foreign Keys
    course_id = Column(Integer, nullable=True, index=True)  # For future course model
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Status and Metadata
    is_pinned = Column(Boolean, default=False, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    created_by = relationship("User", back_populates="announcements")

    def __repr__(self) -> str:
        """String representation of Announcement."""
        return f"<Announcement(id={self.id}, title='{self.title[:30]}...', type='{self.announcement_type.value}')>"
