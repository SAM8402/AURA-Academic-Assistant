"""
Profile database model.

This module defines the Profile model for extended user information.
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from config.db import Base


class Profile(Base):
    """
    Profile model representing extended user information.

    Attributes:
        id: Primary key
        user_id: Associated user ID (one-to-one)
        full_name: User's full name
        bio: Short biography
        avatar_url: Profile picture URL
        phone: Contact phone number
        date_of_birth: Date of birth
        department: Department/field of study
        year_of_study: Current year (for students)
        interests: List of interests/topics
        social_links: Social media links (JSON)
        query_count: Number of queries posted
        resolved_count: Number of queries resolved
        resource_count: Number of resources contributed
        reputation_score: User reputation score
        created_at: Profile creation timestamp
        updated_at: Last update timestamp

    Relationships:
        user: One-to-one with User

    Example:
        >>> profile = Profile(
        ...     user_id=1,
        ...     full_name="John Doe",
        ...     bio="CS student interested in AI",
        ...     department="Computer Science"
        ... )
    """
    __tablename__ = "profiles"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign Key (One-to-One with User)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)

    # Basic Information
    full_name = Column(String(100), nullable=False)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)

    # Academic Information
    department = Column(String(100), nullable=True)
    year_of_study = Column(Integer, nullable=True)

    # Interests and Social
    interests = Column(JSON, default=list)  # Store as JSON array
    social_links = Column(JSON, default=dict)  # Store as JSON object

    # Statistics
    query_count = Column(Integer, default=0, nullable=False)
    resolved_count = Column(Integer, default=0, nullable=False)
    resource_count = Column(Integer, default=0, nullable=False)
    reputation_score = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profile")

    def __repr__(self) -> str:
        """String representation of Profile."""
        return f"<Profile(id={self.id}, user_id={self.user_id}, name='{self.full_name}')>"
