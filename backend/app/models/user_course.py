"""
User-Course Association model for many-to-many relationship.
Tracks which courses each TA/Instructor is assigned to.
"""

from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.db import Base


class UserCourse(Base):
    """
    Many-to-many relationship between Users and Courses.
    Tracks course assignments for TAs and Instructors.

    Attributes:
        id: Primary key
        user_id: Foreign key to users table (TA or Instructor)
        course_id: Foreign key to courses table
        assigned_at: Timestamp when assignment was made
        
    Constraints:
        - Unique constraint on (user_id, course_id) to prevent duplicates
        - Only TAs and Instructors should have course assignments
    """
    __tablename__ = "user_courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="assigned_courses")
    course = relationship("Course", back_populates="assigned_users")

    # Constraint to prevent duplicate assignments
    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='uq_user_course'),
    )

    def __repr__(self):
        return f"<UserCourse(user_id={self.user_id}, course_id={self.course_id})>"
