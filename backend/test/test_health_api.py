"""
Tests for Health Check and Info API endpoints.

This module tests:
- GET / - Root endpoint (redirects to docs)
- GET /health - Health check endpoint
- GET /api - API information endpoint
"""

import pytest
from fastapi.testclient import TestClient


# ============================================================================
# Root Endpoint Tests
# ============================================================================

@pytest.mark.api
class TestRootEndpoint:
    """Tests for GET / endpoint."""

    def test_root_redirects_to_docs(self, client: TestClient):
        """Test that root endpoint redirects to documentation."""
        response = client.get("/", follow_redirects=False)

        # Should redirect (307 or 302)
        assert response.status_code in [307, 302]
        assert "/docs" in response.headers.get("location", "")

    def test_root_redirect_works(self, client: TestClient):
        """Test that following the redirect works."""
        response = client.get("/", follow_redirects=True)

        # Should successfully load docs page
        assert response.status_code == 200


# ============================================================================
# Health Check Tests
# ============================================================================

@pytest.mark.api
class TestHealthCheck:
    """Tests for GET /health endpoint."""

    def test_health_check_success(self, client: TestClient):
        """Test successful health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "status" in data
        assert "app_name" in data
        assert "version" in data

    def test_health_check_status_healthy(self, client: TestClient):
        """Test that health check returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_check_app_name(self, client: TestClient):
        """Test that health check returns correct app name."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["app_name"] == "AURA"

    def test_health_check_version(self, client: TestClient):
        """Test that health check returns version."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_check_environment(self, client: TestClient):
        """Test that health check does NOT expose environment for security."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "environment" not in data

    def test_health_check_database(self, client: TestClient):
        """Test that health check does NOT expose database info for security."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "database" not in data

    def test_health_check_no_auth_required(self, client: TestClient):
        """Test that health check doesn't require authentication."""
        # No auth headers provided
        response = client.get("/health")

        # Should still succeed
        assert response.status_code == 200


# ============================================================================
# API Info Tests
# ============================================================================

@pytest.mark.api
class TestAPIInfo:
    """Tests for GET /api endpoint."""

    def test_api_info_success(self, client: TestClient):
        """Test successful API info retrieval."""
        response = client.get("/api")

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "app_name" in data
        assert "version" in data
        assert "description" in data
        assert "docs_url" in data
        assert "redoc_url" in data
        assert "openapi_url" in data
        assert "endpoints" in data

    def test_api_info_app_name(self, client: TestClient):
        """Test API info returns correct app name."""
        response = client.get("/api")

        assert response.status_code == 200
        assert response.json()["app_name"] == "AURA"

    def test_api_info_description(self, client: TestClient):
        """Test API info returns description."""
        response = client.get("/api")

        assert response.status_code == 200
        data = response.json()

        assert "description" in data
        assert "Academic" in data["description"] or "AURA" in data["description"]

    def test_api_info_documentation_urls(self, client: TestClient):
        """Test API info returns documentation URLs."""
        response = client.get("/api")

        assert response.status_code == 200
        data = response.json()

        assert data["docs_url"] == "/docs"
        assert data["redoc_url"] == "/redoc"
        assert data["openapi_url"] == "/openapi.json"

    def test_api_info_endpoints(self, client: TestClient):
        """Test API info returns endpoint information."""
        response = client.get("/api")

        assert response.status_code == 200
        data = response.json()

        endpoints = data["endpoints"]
        assert "authentication" in endpoints
        assert "health" in endpoints
        assert "documentation" in endpoints

        # Check endpoint paths
        assert "/api/auth" in endpoints["authentication"]
        assert "/health" in endpoints["health"]
        assert "/docs" in endpoints["documentation"]

    def test_api_info_no_auth_required(self, client: TestClient):
        """Test that API info doesn't require authentication."""
        # No auth headers provided
        response = client.get("/api")

        # Should still succeed
        assert response.status_code == 200


# ============================================================================
# Documentation Endpoints Tests
# ============================================================================

@pytest.mark.api
class TestDocumentationEndpoints:
    """Tests for documentation endpoints."""

    def test_swagger_docs_accessible(self, client: TestClient):
        """Test that Swagger documentation is accessible."""
        response = client.get("/docs")

        assert response.status_code == 200

    def test_redoc_accessible(self, client: TestClient):
        """Test that ReDoc documentation is accessible."""
        response = client.get("/redoc")

        assert response.status_code == 200

    def test_openapi_json_accessible(self, client: TestClient):
        """Test that OpenAPI JSON is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        # Check OpenAPI structure
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_openapi_json_structure(self, client: TestClient):
        """Test OpenAPI JSON has correct structure."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()

        # Check info section
        info = data["info"]
        assert "title" in info
        assert "version" in info
        assert info["title"] == "AURA"

        # Check paths section
        paths = data["paths"]
        assert "/health" in paths
        assert "/api/auth/login" in paths
        assert "/api/auth/signup" in paths
        assert "/api/chatbot/chat" in paths


# ============================================================================
# CORS Tests
# ============================================================================

@pytest.mark.api
class TestCORS:
    """Tests for CORS middleware."""

    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are present in response."""
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )

        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_preflight_request(self, client: TestClient):
        """Test CORS preflight request."""
        response = client.options(
            "/api/chatbot/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type"
            }
        )

        # Preflight should succeed
        assert response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.api
class TestErrorHandling:
    """Tests for general error handling."""

    def test_404_on_invalid_endpoint(self, client: TestClient):
        """Test 404 response for non-existent endpoint."""
        response = client.get("/nonexistent/endpoint")

        assert response.status_code == 404

    def test_405_on_wrong_method(self, client: TestClient):
        """Test 405 response for wrong HTTP method."""
        # GET instead of POST for login
        response = client.get("/api/auth/login")

        assert response.status_code == 405

    def test_error_response_format(self, client: TestClient):
        """Test that error responses have consistent format."""
        response = client.get("/nonexistent/endpoint")

        assert response.status_code == 404
        data = response.json()

        # FastAPI error format
        assert "detail" in data
