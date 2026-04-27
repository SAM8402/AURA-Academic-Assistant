"""
Pytest configuration and shared fixtures for AURA API tests.

This module provides:
- Database session management for tests
- Test client with authenticated requests
- User creation helpers
- Mock data factories
"""

import os
import sys
import pytest
from typing import Generator, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("GOOGLE_API_KEY", "test-api-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from config.db import Base, get_db

# Import ALL models to register them with Base before create_all
from app.models.user import User
from app.models.profile import Profile
from app.models.course import Course
from app.models.knowledge import KnowledgeSource, KnowledgeChunk
from app.models.task import Task
from app.models.query import Query, QueryResponse
from app.models.chat_session import ChatSession
from app.models.call import Call
from app.models.doubts import DoubtUpload, DoubtMessage
from app.models.quiz import Quiz
from app.models.slide_deck import SlideDeck
from app.models.resource import Resource
from app.models.tag import Tag
from app.models.announcement import Announcement

from config.security import create_tokens


# ============================================================================
# Test Database Configuration
# ============================================================================

# Use SQLite database for tests
TEST_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./test.db")

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# Create test session factory
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.

    This fixture:
    1. Creates all database tables
    2. Yields a database session
    3. Cleans up after test completes
    """
    # Create all tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database session override.

    This fixture provides a TestClient that uses the test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ============================================================================
# User Creation Fixtures
# ============================================================================

@pytest.fixture
def test_user_data() -> Dict:
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User",
        "role": "student"
    }


@pytest.fixture
def test_ta_data() -> Dict:
    """Sample TA user data for testing."""
    return {
        "email": "ta@example.com",
        "password": "TAPassword123!",
        "full_name": "TA User",
        "role": "ta"
    }


@pytest.fixture
def test_instructor_data() -> Dict:
    """Sample instructor user data for testing."""
    return {
        "email": "instructor@example.com",
        "password": "InstructorPass123!",
        "full_name": "Instructor User",
        "role": "instructor"
    }


@pytest.fixture
def test_admin_data() -> Dict:
    """Sample admin user data for testing."""
    return {
        "email": "admin@example.com",
        "password": "AdminPassword123!",
        "full_name": "Admin User",
        "role": "admin"
    }


@pytest.fixture
def create_test_user(db_session: Session):
    """
    Factory fixture to create test users.

    Usage:
        user = create_test_user(email="test@example.com", password="pass123")
    """
    def _create_user(
        email: str = "test@example.com",
        password: str = "TestPassword123!",
        full_name: str = "Test User",
        role: str = "student",
        is_active: bool = True
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            role=role,
            is_active=is_active
        )
        user.set_password(password)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create profile
        profile = Profile(
            user_id=user.id,
            full_name=full_name
        )
        db_session.add(profile)
        db_session.commit()

        return user

    return _create_user


@pytest.fixture
def authenticated_user(create_test_user, test_user_data) -> User:
    """Create an authenticated test user."""
    return create_test_user(**test_user_data)


@pytest.fixture
def authenticated_ta(create_test_user, test_ta_data) -> User:
    """Create an authenticated TA user."""
    return create_test_user(**test_ta_data)


@pytest.fixture
def authenticated_instructor(create_test_user, test_instructor_data) -> User:
    """Create an authenticated instructor user."""
    return create_test_user(**test_instructor_data)


@pytest.fixture
def authenticated_admin(create_test_user, test_admin_data) -> User:
    """Create an authenticated admin user."""
    return create_test_user(**test_admin_data)


# ============================================================================
# Authentication Token Fixtures
# ============================================================================

@pytest.fixture
def user_token(authenticated_user: User) -> str:
    """Generate JWT access token for test user."""
    tokens = create_tokens(
        user_id=authenticated_user.id,
        email=authenticated_user.email,
        role=authenticated_user.role
    )
    return tokens["access_token"]


@pytest.fixture
def ta_token(authenticated_ta: User) -> str:
    """Generate JWT access token for TA user."""
    tokens = create_tokens(
        user_id=authenticated_ta.id,
        email=authenticated_ta.email,
        role=authenticated_ta.role
    )
    return tokens["access_token"]


@pytest.fixture
def instructor_token(authenticated_instructor: User) -> str:
    """Generate JWT access token for instructor user."""
    tokens = create_tokens(
        user_id=authenticated_instructor.id,
        email=authenticated_instructor.email,
        role=authenticated_instructor.role
    )
    return tokens["access_token"]


@pytest.fixture
def admin_token(authenticated_admin: User) -> str:
    """Generate JWT access token for admin user."""
    tokens = create_tokens(
        user_id=authenticated_admin.id,
        email=authenticated_admin.email,
        role=authenticated_admin.role
    )
    return tokens["access_token"]


@pytest.fixture
def auth_headers(user_token: str) -> Dict:
    """Create authorization headers with user token."""
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def ta_auth_headers(ta_token: str) -> Dict:
    """Create authorization headers with TA token."""
    return {"Authorization": f"Bearer {ta_token}"}


@pytest.fixture
def instructor_auth_headers(instructor_token: str) -> Dict:
    """Create authorization headers with instructor token."""
    return {"Authorization": f"Bearer {instructor_token}"}


@pytest.fixture
def admin_auth_headers(admin_token: str) -> Dict:
    """Create authorization headers with admin token."""
    return {"Authorization": f"Bearer {admin_token}"}


# ============================================================================
# Mock Data Fixtures
# ============================================================================

@pytest.fixture
def sample_chat_request() -> Dict:
    """Sample chatbot request data."""
    return {
        "message": "Explain binary search algorithm",
        "mode": "academic",
        "conversation_id": None
    }


@pytest.fixture
def sample_chat_stream_request() -> Dict:
    """Sample chatbot streaming request data."""
    return {
        "message": "What is recursion?",
        "mode": "academic",
        "conversation_id": None
    }


@pytest.fixture
def test_course(db_session: Session, authenticated_admin: User) -> Course:
    """
    Creates a sample course in the database for testing purposes.
    """
    course = Course(
        name="Test Course for API",
        description="A sample course created by a fixture.",
        created_by_id=authenticated_admin.id
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)
    return course


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def invalid_token() -> str:
    """Generate an invalid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.token"


@pytest.fixture
def expired_token() -> str:
    """Generate an expired JWT token for testing."""
    # This is a token that expired in the past
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZW1haWwiOiJ0ZXN0QGV4YW1wbGUuY29tIiwicm9sZSI6InN0dWRlbnQiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjAwMDAwMDAwfQ.expired"
