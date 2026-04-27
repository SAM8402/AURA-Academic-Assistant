"""
User database model.

This module defines the User SQLAlchemy model for database operations.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from config.db import Base
from config.security import hash_password, verify_password
from app.schemas.user_schema import UserRole
import enum


class User(Base):
    """
    User model representing all users in the system.

    Supports role-based access control with four roles:
    - student: Regular students
    - ta: Teaching assistants
    - instructor: Course instructors
    - admin: System administrators

    Attributes:
        id: Primary key
        email: Unique email address (indexed for fast lookups)
        password: Hashed password using Argon2
        role: User role (student, ta, instructor, admin)
        full_name: User's full name
        is_active: Account activation status
        is_verified: Email verification status
        created_at: Account creation timestamp
        updated_at: Last update timestamp

    Relationships:
        profile: One-to-one relationship with Profile
        queries: One-to-many relationship with Query (as student)
        assigned_queries: One-to-many relationship with Query (as TA/instructor)
        resources: One-to-many relationship with Resource (as creator)
        announcements: One-to-many relationship with Announcement (as creator)
        query_responses: One-to-many relationship with QueryResponse

    Example:
        >>> user = User(
        ...     email="student@example.com",
        ...     role=UserRole.STUDENT,
        ...     full_name="John Doe"
        ... )
        >>> user.set_password("SecurePass123")
        >>> db.add(user)
        >>> db.commit()
    """
    __tablename__ = "users"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True)

    # Authentication
    email = Column(String(120), unique=True, index=True, nullable=False)
    password = Column(String(192), nullable=False)

    # Role and Permissions
    role = Column(
        SQLEnum(UserRole),
        nullable=False,
        default=UserRole.STUDENT,
        index=True  # Index for role-based queries
    )

    # User Information
    full_name = Column(String(100), nullable=True)

    # Account Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    queries = relationship("Query", foreign_keys="Query.student_id", back_populates="student", cascade="all, delete-orphan")
    assigned_queries = relationship("Query", foreign_keys="Query.assigned_to_id", back_populates="assigned_to")
    resources = relationship("Resource", back_populates="created_by", cascade="all, delete-orphan")
    announcements = relationship("Announcement", back_populates="created_by", cascade="all, delete-orphan")
    query_responses = relationship("QueryResponse", back_populates="user", cascade="all, delete-orphan")
    quizzes_created = relationship("Quiz", back_populates="creator", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    slide_decks_created = relationship("SlideDeck", back_populates="creator", cascade="all, delete-orphan")
    assigned_courses = relationship("UserCourse", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        """
        Hash and set the user's password using Argon2.

        Args:
            password: Plain text password

        Example:
            >>> user = User(email="test@example.com")
            >>> user.set_password("SecurePass123")
        """
        self.password = hash_password(password)

    def verify_password(self, password: str) -> bool:
        """
        Verify a plain text password against the stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            bool: True if password matches, False otherwise

        Example:
            >>> user.set_password("SecurePass123")
            >>> user.verify_password("SecurePass123")
            True
            >>> user.verify_password("WrongPassword")
            False
        """
        return verify_password(password, self.password)

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"
