"""
Tests for Analytics API endpoints.

This module tests:
- GET /api/analytics/overview - Overall metrics
- GET /api/analytics/faqs - Frequently asked questions
- GET /api/analytics/performance - Response time and resolution rate
- GET /api/analytics/sentiment - Aggregate feedback sentiment
- GET /api/analytics/usage - Active users, API calls, session stats
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.models.user import User, UserRole
from app.models.query import Query, QueryResponse
from app.models.knowledge import KnowledgeSource
from app.models.chat_session import ChatSession
from app.schemas.query_schema import QueryStatus, QueryCategory, QueryPriority
from config.security import hash_password


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsOverview:
    """Tests for analytics overview endpoint."""

    def test_overview_requires_authentication(self, client: TestClient):
        """Test that overview endpoint requires authentication."""
        response = client.get("/api/analytics/overview")
        # 403 Forbidden when no auth is provided
        assert response.status_code in [401, 403]

    def test_overview_requires_admin_role(self, client: TestClient, db_session: Session):
        """Test that overview endpoint requires admin role."""
        # Create non-admin user with properly hashed password
        student = User(
            full_name="Student User",
            email="student_analytics@test.com",
            password=hash_password("student123"),
            role=UserRole.STUDENT
        )
        db_session.add(student)
        db_session.commit()

        # Login as student
        login_response = client.post("/api/auth/login", json={
            "email": "student_analytics@test.com",
            "password": "student123"
        })

        # Try to access analytics
        token = login_response.json().get("access_token")
        if token:
            response = client.get(
                "/api/analytics/overview",
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should be forbidden (403) or unauthorized
            assert response.status_code in [401, 403]

    def test_overview_success_with_admin(self, client: TestClient, db_session: Session, admin_token):
        """Test that admin can access overview endpoint."""
        response = client.get(
            "/api/analytics/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = [
            "total_users", "total_queries", "total_responses",
            "total_knowledge_sources", "total_chat_sessions",
            "active_users_today", "active_users_week",
            "queries_today", "queries_week",
            "open_queries", "resolved_queries"
        ]

        for field in required_fields:
            assert field in data, f"Missing field: {field}"
            assert isinstance(data[field], int), f"Field {field} should be integer"

    def test_overview_with_sample_data(self, client: TestClient, db_session: Session, admin_token):
        """Test overview with populated database."""
        # Create sample users
        for i in range(5):
            user = User(
                full_name=f"Test User {i}",
                email=f"overview_user{i}@test.com",
                password=hash_password("test123"),
                role=UserRole.STUDENT
            )
            db_session.add(user)
        db_session.commit()

        # Create sample queries
        user = db_session.query(User).filter(User.email == "overview_user0@test.com").first()
        for i in range(3):
            query = Query(
                title=f"Test Query {i}",
                description="Test description",
                category=QueryCategory.TECHNICAL,
                status=QueryStatus.OPEN if i == 0 else QueryStatus.RESOLVED,
                student_id=user.id,
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            db_session.add(query)
        db_session.commit()

        response = client.get(
            "/api/analytics/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify counts (at least our sample data)
        assert data["total_users"] >= 5
        assert data["total_queries"] >= 3
        assert data["open_queries"] >= 1
        assert data["resolved_queries"] >= 2


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsFAQs:
    """Tests for FAQs endpoint."""

    def test_faqs_requires_admin(self, client: TestClient):
        """Test that FAQs endpoint requires admin authentication."""
        response = client.get("/api/analytics/faqs")
        assert response.status_code in [401, 403]

    def test_faqs_success(self, client: TestClient, admin_token):
        """Test successful FAQs retrieval."""
        response = client.get(
            "/api/analytics/faqs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "total_unique_questions" in data
        assert "faqs" in data
        assert "time_period" in data
        assert isinstance(data["faqs"], list)

    def test_faqs_with_limit_parameter(self, client: TestClient, admin_token):
        """Test FAQs with custom limit."""
        response = client.get(
            "/api/analytics/faqs?limit=5",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should return at most 5 items
        assert len(data["faqs"]) <= 5

    def test_faqs_with_days_parameter(self, client: TestClient, admin_token):
        """Test FAQs with custom time period."""
        response = client.get(
            "/api/analytics/faqs?days=7",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["time_period"] == "last_7_days"

    def test_faqs_structure(self, client: TestClient, db_session: Session, admin_token):
        """Test FAQ item structure."""
        # Create duplicate queries to generate FAQs
        user = User(
            full_name="FAQ Test User",
            email="faqtest@test.com",
            password="hashed",
            role=UserRole.STUDENT
        )
        db_session.add(user)
        db_session.commit()

        for i in range(3):
            query = Query(
                title="How do I submit assignment?",  # Same title
                description=f"Description {i}",
                category=QueryCategory.ASSIGNMENT,
                status=QueryStatus.RESOLVED,
                student_id=user.id
            )
            db_session.add(query)
        db_session.commit()

        response = client.get(
            "/api/analytics/faqs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        if len(data["faqs"]) > 0:
            faq = data["faqs"][0]
            assert "question" in faq
            assert "count" in faq
            assert "category" in faq
            assert "status" in faq


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsPerformance:
    """Tests for performance metrics endpoint."""

    def test_performance_requires_admin(self, client: TestClient):
        """Test that performance endpoint requires admin."""
        response = client.get("/api/analytics/performance")
        assert response.status_code in [401, 403]

    def test_performance_success(self, client: TestClient, admin_token):
        """Test successful performance metrics retrieval."""
        response = client.get(
            "/api/analytics/performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        required_fields = [
            "resolution_rate_percentage",
            "open_query_count",
            "in_progress_count",
            "resolved_count",
            "closed_count",
            "queries_with_responses",
            "queries_without_responses",
            "average_responses_per_query"
        ]

        for field in required_fields:
            assert field in data

    def test_performance_calculations(self, client: TestClient, db_session: Session, admin_token):
        """Test performance metric calculations."""
        # Create test data
        user = User(
            full_name="Perf Test User",
            email="perftest@test.com",
            password="hashed",
            role=UserRole.STUDENT
        )
        db_session.add(user)
        db_session.commit()

        # Create resolved query
        query = Query(
            title="Test Query",
            description="Test",
            category=QueryCategory.TECHNICAL,
            status=QueryStatus.RESOLVED,
            student_id=user.id,
            created_at=datetime.utcnow() - timedelta(hours=5),
            updated_at=datetime.utcnow()
        )
        db_session.add(query)
        db_session.commit()

        # Add response
        ta = User(
            full_name="TA User",
            email="ta_perf@test.com",
            password="hashed",
            role=UserRole.TA
        )
        db_session.add(ta)
        db_session.commit()

        response_obj = QueryResponse(
            query_id=query.id,
            user_id=ta.id,
            content="Answer to query",
            is_solution=True
        )
        db_session.add(response_obj)
        db_session.commit()

        response = client.get(
            "/api/analytics/performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least 1 resolved query
        assert data["resolved_count"] >= 1
        assert data["queries_with_responses"] >= 1
        assert data["resolution_rate_percentage"] > 0


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsSentiment:
    """Tests for sentiment analysis endpoint."""

    def test_sentiment_requires_admin(self, client: TestClient):
        """Test that sentiment endpoint requires admin."""
        response = client.get("/api/analytics/sentiment")
        assert response.status_code in [401, 403]

    def test_sentiment_success(self, client: TestClient, admin_token):
        """Test successful sentiment retrieval."""
        response = client.get(
            "/api/analytics/sentiment",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "positive_count", "neutral_count", "negative_count",
            "total_feedback", "positive_percentage",
            "neutral_percentage", "negative_percentage"
        ]

        for field in required_fields:
            assert field in data

    def test_sentiment_percentages_sum_to_100(self, client: TestClient, db_session: Session, admin_token):
        """Test that sentiment percentages sum to approximately 100%."""
        # Create sample queries with different statuses
        user = User(
            full_name="Sentiment Test",
            email="sentiment@test.com",
            password="hashed",
            role=UserRole.STUDENT
        )
        db_session.add(user)
        db_session.commit()

        for status in [QueryStatus.RESOLVED, QueryStatus.IN_PROGRESS, QueryStatus.OPEN]:
            query = Query(
                title=f"Query {status}",
                description="Test",
                category=QueryCategory.TECHNICAL,
                status=status,
                student_id=user.id
            )
            db_session.add(query)
        db_session.commit()

        response = client.get(
            "/api/analytics/sentiment",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        if data["total_feedback"] > 0:
            total_percentage = (
                data["positive_percentage"] +
                data["neutral_percentage"] +
                data["negative_percentage"]
            )
            # Allow small rounding error
            assert 99.9 <= total_percentage <= 100.1


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsUsage:
    """Tests for usage statistics endpoint."""

    def test_usage_requires_admin(self, client: TestClient):
        """Test that usage endpoint requires admin."""
        response = client.get("/api/analytics/usage")
        assert response.status_code in [401, 403]

    def test_usage_success(self, client: TestClient, admin_token):
        """Test successful usage statistics retrieval."""
        response = client.get(
            "/api/analytics/usage",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "usage_stats" in data
        assert "users_by_role" in data
        assert "queries_by_category" in data
        assert "time_period" in data

        # Check usage_stats structure
        usage_stats = data["usage_stats"]
        required_stats = [
            "active_users_today", "active_users_week", "active_users_month",
            "total_chat_sessions", "chat_sessions_today", "chat_sessions_week",
            "api_calls_today", "api_calls_week"
        ]

        for stat in required_stats:
            assert stat in usage_stats

    def test_usage_users_by_role(self, client: TestClient, db_session: Session, admin_token):
        """Test users by role breakdown."""
        # Create users with different roles
        roles_to_create = [
            (UserRole.STUDENT, "student_usage@test.com"),
            (UserRole.TA, "ta_usage@test.com"),
            (UserRole.INSTRUCTOR, "instructor_usage@test.com")
        ]

        for role, email in roles_to_create:
            user = User(
                full_name=f"User {role.value}",
                email=email,
                password=hash_password("test123"),
                role=role
            )
            db_session.add(user)
        db_session.commit()

        response = client.get(
            "/api/analytics/usage",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have role breakdown
        assert len(data["users_by_role"]) > 0

        # Each role should have count and active_count
        for role_data in data["users_by_role"]:
            assert "role" in role_data
            assert "count" in role_data
            assert "active_count" in role_data

    def test_usage_queries_by_category(self, client: TestClient, db_session: Session, admin_token):
        """Test queries by category breakdown."""
        # Create queries in different categories
        user = User(
            full_name="Category Test",
            email="category@test.com",
            password=hash_password("test123"),
            role=UserRole.STUDENT
        )
        db_session.add(user)
        db_session.commit()

        categories = [QueryCategory.TECHNICAL, QueryCategory.ASSIGNMENT, QueryCategory.GENERAL]
        for category in categories:
            query = Query(
                title=f"Query in {category.value}",
                description="Test",
                category=category,
                status=QueryStatus.OPEN,
                student_id=user.id
            )
            db_session.add(query)
        db_session.commit()

        response = client.get(
            "/api/analytics/usage",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Should have category breakdown
        assert len(data["queries_by_category"]) > 0

        # Each category should have count and percentage
        for cat_data in data["queries_by_category"]:
            assert "category" in cat_data
            assert "count" in cat_data
            assert "percentage" in cat_data


@pytest.mark.api
@pytest.mark.integration
class TestAnalyticsIntegration:
    """Integration tests for analytics endpoints."""

    def test_all_endpoints_accessible_by_admin(self, client: TestClient, admin_token):
        """Test that all analytics endpoints are accessible by admin."""
        endpoints = [
            "/api/analytics/overview",
            "/api/analytics/faqs",
            "/api/analytics/performance",
            "/api/analytics/sentiment",
            "/api/analytics/usage"
        ]

        for endpoint in endpoints:
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed to access {endpoint}"

    def test_analytics_data_consistency(self, client: TestClient, db_session: Session, admin_token):
        """Test data consistency across different endpoints."""
        # Get overview
        overview_response = client.get(
            "/api/analytics/overview",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        overview = overview_response.json()

        # Get performance
        performance_response = client.get(
            "/api/analytics/performance",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        performance = performance_response.json()

        # Query counts should match
        total_queries_overview = overview["total_queries"]
        total_queries_performance = (
            performance["open_query_count"] +
            performance["in_progress_count"] +
            performance["resolved_count"] +
            performance["closed_count"]
        )

        assert total_queries_overview == total_queries_performance

    def test_analytics_performance_under_load(self, client: TestClient, db_session: Session, admin_token):
        """Test analytics performance with larger dataset."""
        # Create more test data
        user = User(
            full_name="Load Test User",
            email="loadtest@test.com",
            password=hash_password("test123"),
            role=UserRole.STUDENT
        )
        db_session.add(user)
        db_session.commit()

        # Create 50 queries
        for i in range(50):
            query = Query(
                title=f"Load Test Query {i}",
                description="Performance test",
                category=QueryCategory.TECHNICAL,
                status=QueryStatus.OPEN,
                student_id=user.id
            )
            db_session.add(query)

        db_session.commit()

        # All endpoints should still respond quickly
        import time

        endpoints = [
            "/api/analytics/overview",
            "/api/analytics/faqs",
            "/api/analytics/performance",
            "/api/analytics/sentiment",
            "/api/analytics/usage"
        ]

        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(
                endpoint,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            end_time = time.time()

            assert response.status_code == 200
            # Should respond within 2 seconds
            assert (end_time - start_time) < 2.0, f"{endpoint} took too long"
