"""
Database configuration and session management.

This module handles SQLAlchemy engine creation, session management,
and provides database dependencies for FastAPI routes.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings


# ============================================================================
# Database Engine Configuration
# ============================================================================

# Create database engine with configuration from settings
# For SQLite: uses check_same_thread=False for FastAPI compatibility
# For PostgreSQL/MySQL: connect_args can be removed or customized
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DB_ECHO,  # Log SQL queries if enabled in settings
    pool_pre_ping=True,  # Verify connections before using them
)


# ============================================================================
# Session Factory
# ============================================================================

# Create session factory
# autocommit=False: Manual transaction control
# autoflush=False: Manual flush control for better performance
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ============================================================================
# Base Class for ORM Models
# ============================================================================

# Base class for all SQLAlchemy ORM models
# All models should inherit from this base
Base = declarative_base()


# ============================================================================
# Database Dependencies for FastAPI
# ============================================================================


def get_db():
    """
    Provide a SQLAlchemy database session as a FastAPI dependency.

    This function creates a new database session for each request
    and ensures proper cleanup after the request is complete.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ============================================================================
# Database Initialization Helper
# ============================================================================


def init_db():
    """
    Initialize database by creating all tables.

    This function creates all tables defined by SQLAlchemy models
    that inherit from Base.

    Note:
        In production, use Alembic migrations instead of create_all()
        for better version control and schema management.

    Example:
        from app.core.db import init_db
        init_db()  # Creates all tables
    """
    # Import all models here to ensure they are registered with Base
    from app.models import (
        User, Query, QueryResponse, Resource, Announcement, Profile,
        # New models from merge
        KnowledgeSource, KnowledgeChunk, Call, ChatSession, Task,
        # Additional models
        Course, UserCourse, Quiz, QuizAttempt, SlideDeck, Tag,
        DoubtUpload, DoubtMessage
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)


def drop_db():
    """
    Drop all database tables.

    WARNING: This will delete all data in the database!
    Use only for development/testing purposes.

    Example:
        from app.core.db import drop_db
        drop_db()  # Drops all tables
    """
    Base.metadata.drop_all(bind=engine)
