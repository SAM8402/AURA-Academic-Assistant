"""
Resource database model.

This module defines the Resource model for educational materials.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum, func, JSON
from sqlalchemy.orm import relationship
from config.db import Base
from app.schemas.resource_schema import ResourceType, ResourceVisibility


class Resource(Base):
    """
    Resource model representing educational materials.

    Attributes:
        id: Primary key
        title: Resource title
        description: Detailed description
        resource_type: Type of resource (video, pdf, link, etc.)
        url: External resource URL (if applicable)
        file_path: Internal file path (if uploaded)
        visibility: Access level (public, course, role_specific, private)
        course_id: Associated course (optional)
        tags: List of tags for searchability
        created_by_id: ID of creator
        download_count: Number of downloads
        view_count: Number of views
        is_active: Whether resource is active
        created_at: Creation timestamp
        updated_at: Last update timestamp

    Relationships:
        created_by: Many-to-one with User

    Example:
        >>> resource = Resource(
        ...     title="Python Tutorial",
        ...     resource_type=ResourceType.VIDEO,
        ...     url="https://example.com/video",
        ...     created_by_id=1
        ... )
    """
    __tablename__ = "resources"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Resource Content
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Resource Type and Location
    resource_type = Column(
        SQLEnum(ResourceType),
        nullable=False,
        index=True
    )
    url = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)

    # Access Control
    visibility = Column(
        SQLEnum(ResourceVisibility),
        nullable=False,
        default=ResourceVisibility.PUBLIC,
        index=True
    )

    # Foreign Keys
    course_id = Column(Integer, nullable=True, index=True)  # For future course model
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Metadata
    tags = Column(JSON, default=list)  # Store as JSON array
    download_count = Column(Integer, default=0, nullable=False)
    view_count = Column(Integer, default=0, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    created_by = relationship("User", back_populates="resources")

    def __repr__(self) -> str:
        """String representation of Resource."""
        return f"<Resource(id={self.id}, title='{self.title[:30]}...', type='{self.resource_type.value}')>"
