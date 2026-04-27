"""
Tests for Queries API endpoints.

This module tests:
- GET /api/queries/ - List queries with filtering
- GET /api/queries/{id} - Get query details
- POST /api/queries/ - Create new query
- POST /api/queries/{id}/response - Add response to query
- PUT /api/queries/{id}/status - Update query status
- GET /api/queries/statistics/summary - Get query statistics
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.user import User
from app.models.query import Query, QueryResponse
from app.schemas.query_schema import QueryStatus, QueryPriority, QueryCategory
from app.schemas.user_schema import UserRole
from config.security import hash_password


@pytest.mark.api
@pytest.mark.queries
class TestListQueries:
    """Tests for listing queries endpoint."""

    def test_list_queries_student_sees_own(self, client: TestClient, db_session: Session):
        """Test that students see only their own queries."""
        # Create two students
        student1 = User(
            email="student1@test.com",
            full_name="Student One",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        student2 = User(
            email="student2@test.com",
            full_name="Student Two",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student1, student2])
        db_session.flush()

        # Create queries for both students
        query1 = Query(
            title="Student 1 Query",
            description="This is student 1's query",
            student_id=student1.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        query2 = Query(
            title="Student 2 Query",
            description="This is student 2's query",
            student_id=student2.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add_all([query1, query2])
        db_session.commit()

        # Login as student1
        login_response = client.post("/api/auth/login", json={
            "email": "student1@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List queries
        response = client.get("/api/queries/", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["queries"]) == 1
        assert data["queries"][0]["title"] == "Student 1 Query"

    def test_list_queries_ta_sees_all(self, client: TestClient, db_session: Session):
        """Test that TAs see all queries."""
        # Create student and TA
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student, ta])
        db_session.flush()

        # Create multiple queries
        query1 = Query(
            title="Query 1",
            description="First query",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        query2 = Query(
            title="Query 2",
            description="Second query",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.ASSIGNMENT,
            priority=QueryPriority.HIGH
        )
        db_session.add_all([query1, query2])
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # List queries
        response = client.get("/api/queries/", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert len(data["queries"]) == 2

    def test_list_queries_filter_by_status(self, client: TestClient, db_session: Session):
        """Test filtering queries by status."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create queries with different statuses
        query1 = Query(
            title="Open Query",
            description="This is open",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        query2 = Query(
            title="Resolved Query",
            description="This is resolved",
            student_id=student.id,
            status=QueryStatus.RESOLVED,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add_all([query1, query2])
        db_session.commit()

        # Login as student
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Filter by OPEN status
        response = client.get("/api/queries/?status=OPEN", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["queries"][0]["status"] == "open"

    def test_list_queries_filter_by_category(self, client: TestClient, db_session: Session):
        """Test filtering queries by category."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create queries with different categories
        query1 = Query(
            title="Technical Query",
            description="Technical question",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        query2 = Query(
            title="Assignment Query",
            description="Assignment question",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.ASSIGNMENT,
            priority=QueryPriority.MEDIUM
        )
        db_session.add_all([query1, query2])
        db_session.commit()

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Filter by TECHNICAL category
        response = client.get("/api/queries/?category=TECHNICAL", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert data["queries"][0]["category"] == "technical"

    def test_list_queries_invalid_status(self, client: TestClient, auth_headers: dict):
        """Test filtering with invalid status."""
        response = client.get("/api/queries/?status=INVALID", headers=auth_headers)

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_list_queries_pagination(self, client: TestClient, db_session: Session):
        """Test query pagination."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create 15 queries
        for i in range(15):
            query = Query(
                title=f"Query {i+1}",
                description=f"Description {i+1}",
                student_id=student.id,
                status=QueryStatus.OPEN,
                category=QueryCategory.TECHNICAL,
                priority=QueryPriority.MEDIUM
            )
            db_session.add(query)
        db_session.commit()

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get first page (10 items)
        response = client.get("/api/queries/?limit=10&offset=0", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 15
        assert len(data["queries"]) == 10
        assert data["limit"] == 10
        assert data["offset"] == 0


@pytest.mark.api
@pytest.mark.queries
class TestGetQuery:
    """Tests for getting specific query endpoint."""

    def test_get_query_success(self, client: TestClient, db_session: Session):
        """Test getting a query successfully."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Test description",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get query
        response = client.get(f"/api/queries/{query.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == query.id
        assert data["title"] == "Test Query"
        assert data["description"] == "Test description"
        assert data["view_count"] == 1  # Incremented after view

    def test_get_query_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting non-existent query."""
        response = client.get("/api/queries/99999", headers=auth_headers)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_get_query_forbidden_for_other_student(self, client: TestClient, db_session: Session):
        """Test that student cannot view another student's query."""
        # Create two students
        student1 = User(
            email="student1@test.com",
            full_name="Student One",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        student2 = User(
            email="student2@test.com",
            full_name="Student Two",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student1, student2])
        db_session.flush()

        # Create query for student2
        query = Query(
            title="Student 2 Query",
            description="Private query",
            student_id=student2.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as student1
        login_response = client.post("/api/auth/login", json={
            "email": "student1@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to get student2's query
        response = client.get(f"/api/queries/{query.id}", headers=headers)

        assert response.status_code == 403
        assert "permission" in response.json()["detail"]

    def test_get_query_includes_responses(self, client: TestClient, db_session: Session):
        """Test that get query includes responses."""
        # Create student and TA
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student, ta])
        db_session.flush()

        # Create query
        query = Query(
            title="Query with responses",
            description="Test",
            student_id=student.id,
            status=QueryStatus.IN_PROGRESS,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.flush()

        # Add response
        response_obj = QueryResponse(
            query_id=query.id,
            user_id=ta.id,
            content="This is the answer",
            is_solution=True
        )
        db_session.add(response_obj)
        db_session.commit()

        # Login as student
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get query
        response = client.get(f"/api/queries/{query.id}", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert "responses" in data
        assert len(data["responses"]) == 1
        assert data["responses"][0]["content"] == "This is the answer"
        assert data["responses"][0]["is_solution"] == True


@pytest.mark.api
@pytest.mark.queries
class TestCreateQuery:
    """Tests for creating queries endpoint."""

    def test_create_query_success(self, client: TestClient, db_session: Session):
        """Test creating a query successfully."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.commit()

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create query
        query_data = {
            "title": "Need help with algorithm",
            "description": "I'm stuck on implementing quicksort algorithm",
            "category": "TECHNICAL",
            "priority": "MEDIUM",
            "tags": ["algorithms", "sorting"]
        }

        response = client.post("/api/queries/", json=query_data, headers=headers)

        assert response.status_code == 201
        data = response.json()

        assert data["message"] == "Query created successfully"
        assert data["query"]["title"] == query_data["title"]
        assert data["query"]["status"] == "open"
        assert data["query"]["tags"] == ["algorithms", "sorting"]

    def test_create_query_forbidden_for_ta(self, client: TestClient, db_session: Session):
        """Test that TAs cannot create queries."""
        # Create TA
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(ta)
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to create query
        query_data = {
            "title": "Test Query",
            "description": "This should fail",
            "category": "TECHNICAL",
            "priority": "MEDIUM"
        }

        response = client.post("/api/queries/", json=query_data, headers=headers)

        assert response.status_code == 403
        assert "Only students" in response.json()["detail"]

    def test_create_query_validation_title_too_short(self, client: TestClient, auth_headers: dict):
        """Test validation for short title."""
        query_data = {
            "title": "Hi",  # Too short
            "description": "This is a valid description",
            "category": "TECHNICAL"
        }

        response = client.post("/api/queries/", json=query_data, headers=auth_headers)

        assert response.status_code == 422

    def test_create_query_validation_description_too_short(self, client: TestClient, auth_headers: dict):
        """Test validation for short description."""
        query_data = {
            "title": "Valid Title Here",
            "description": "Short",  # Too short
            "category": "TECHNICAL"
        }

        response = client.post("/api/queries/", json=query_data, headers=auth_headers)

        assert response.status_code == 422


@pytest.mark.api
@pytest.mark.queries
class TestAddQueryResponse:
    """Tests for adding responses to queries."""

    def test_add_response_success(self, client: TestClient, db_session: Session):
        """Test adding a response to a query."""
        # Create student and TA
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student, ta])
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add response
        response_data = {
            "content": "Here is the solution to your problem",
            "is_solution": False
        }

        response = client.post(
            f"/api/queries/{query.id}/response",
            json=response_data,
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["message"] == "Response added successfully"
        assert data["response"]["content"] == response_data["content"]

    def test_add_solution_by_ta(self, client: TestClient, db_session: Session):
        """Test that TA can mark response as solution."""
        # Create student and TA
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student, ta])
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add solution response
        response_data = {
            "content": "This is the correct solution",
            "is_solution": True
        }

        response = client.post(
            f"/api/queries/{query.id}/response",
            json=response_data,
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()

        assert data["response"]["is_solution"] == True

        # Verify query is now resolved
        db_session.refresh(query)
        assert query.status == QueryStatus.RESOLVED

    def test_add_response_student_cannot_mark_solution(self, client: TestClient, db_session: Session):
        """Test that students cannot mark their response as solution."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as student
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to mark response as solution
        response_data = {
            "content": "I think this is the answer",
            "is_solution": True
        }

        response = client.post(
            f"/api/queries/{query.id}/response",
            json=response_data,
            headers=headers
        )

        assert response.status_code == 201
        # Solution flag should be ignored for students
        assert response.json()["response"]["is_solution"] == False

    def test_add_response_updates_status_to_in_progress(self, client: TestClient, db_session: Session):
        """Test that adding first response changes status to IN_PROGRESS."""
        # Create student and TA
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student, ta])
        db_session.flush()

        # Create OPEN query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Add first response
        response_data = {
            "content": "Let me help you",
            "is_solution": False
        }

        client.post(
            f"/api/queries/{query.id}/response",
            json=response_data,
            headers=headers
        )

        # Verify status changed to IN_PROGRESS
        db_session.refresh(query)
        assert query.status == QueryStatus.IN_PROGRESS

    def test_add_response_to_nonexistent_query(self, client: TestClient, auth_headers: dict):
        """Test adding response to non-existent query."""
        response_data = {
            "content": "This should fail",
            "is_solution": False
        }

        response = client.post(
            "/api/queries/99999/response",
            json=response_data,
            headers=auth_headers
        )

        assert response.status_code == 404


@pytest.mark.api
@pytest.mark.queries
class TestUpdateQueryStatus:
    """Tests for updating query status."""

    def test_update_status_by_ta(self, client: TestClient, db_session: Session):
        """Test that TA can update query status."""
        # Create student and TA
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add_all([student, ta])
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update status
        status_data = {
            "status": "IN_PROGRESS",
            "resolution_notes": "Working on it"
        }

        response = client.put(
            f"/api/queries/{query.id}/status",
            json=status_data,
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Query status updated successfully"
        assert data["query"]["status"] == "in_progress"

    def test_update_status_student_forbidden(self, client: TestClient, db_session: Session):
        """Test that students cannot update query status."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as student
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to update status
        status_data = {
            "status": "RESOLVED"
        }

        response = client.put(
            f"/api/queries/{query.id}/status",
            json=status_data,
            headers=headers
        )

        assert response.status_code == 403

    def test_update_status_to_resolved_sets_timestamp(self, client: TestClient, db_session: Session):
        """Test that resolving query sets resolved_at timestamp."""
        # Create TA
        ta = User(
            email="ta@test.com",
            full_name="Test TA",
            role=UserRole.TA,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(ta)
        db_session.flush()

        # Create query
        query = Query(
            title="Test Query",
            description="Need help",
            student_id=ta.id,  # Use TA as student for simplicity
            status=QueryStatus.IN_PROGRESS,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.MEDIUM
        )
        db_session.add(query)
        db_session.commit()

        # Login as TA
        login_response = client.post("/api/auth/login", json={
            "email": "ta@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Update to resolved
        status_data = {
            "status": "RESOLVED",
            "resolution_notes": "Issue fixed"
        }

        client.put(
            f"/api/queries/{query.id}/status",
            json=status_data,
            headers=headers
        )

        # Verify resolved_at is set
        db_session.refresh(query)
        assert query.resolved_at is not None
        assert query.resolution_notes == "Issue fixed"


@pytest.mark.api
@pytest.mark.queries
class TestQueryStatistics:
    """Tests for query statistics endpoint."""

    def test_get_statistics_student(self, client: TestClient, db_session: Session):
        """Test getting statistics as a student."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.flush()

        # Create queries with different statuses
        query1 = Query(
            title="Open Query",
            description="Test",
            student_id=student.id,
            status=QueryStatus.OPEN,
            category=QueryCategory.TECHNICAL,
            priority=QueryPriority.HIGH
        )
        query2 = Query(
            title="Resolved Query",
            description="Test",
            student_id=student.id,
            status=QueryStatus.RESOLVED,
            category=QueryCategory.ASSIGNMENT,
            priority=QueryPriority.MEDIUM
        )
        db_session.add_all([query1, query2])
        db_session.commit()

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get statistics
        response = client.get("/api/queries/statistics/summary", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total_queries"] == 2
        assert data["by_status"]["open"] == 1
        assert data["by_status"]["resolved"] == 1
        assert data["by_priority"]["high"] == 1

    def test_get_statistics_empty(self, client: TestClient, db_session: Session):
        """Test getting statistics with no queries."""
        # Create student
        student = User(
            email="student@test.com",
            full_name="Test Student",
            role=UserRole.STUDENT,
            password=hash_password("test123"),
            is_active=True
        )
        db_session.add(student)
        db_session.commit()

        # Login
        login_response = client.post("/api/auth/login", json={
            "email": "student@test.com",
            "password": "test123"
        })
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get statistics
        response = client.get("/api/queries/statistics/summary", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total_queries"] == 0
        assert data["by_status"]["open"] == 0
