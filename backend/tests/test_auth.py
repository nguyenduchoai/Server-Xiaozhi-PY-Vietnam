"""
Authentication API Tests

Tests for:
- User registration
- User login
- Token refresh
- Password validation
"""

import pytest
from httpx import AsyncClient


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """Test health endpoint is accessible."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_register_user_success(self, client: AsyncClient, test_user_data: dict):
        """Test successful user registration."""
        response = await client.post(
            "/api/v1/auth/register",
            json=test_user_data
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data.get("email") == test_user_data["email"]
        assert "password" not in data  # Password should not be returned

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, client: AsyncClient, test_user_data: dict):
        """Test registration with duplicate email fails."""
        # First registration
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Second registration with same email
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code in [400, 409]

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "username": "testuser",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_weak_password(self, client: AsyncClient):
        """Test registration with weak password fails."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "username": "testuser",
                "password": "123"  # Too weak
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user_data: dict):
        """Test successful login."""
        # Register first
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Login
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["password"]
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user_data: dict):
        """Test login with wrong password fails."""
        # Register first
        await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Login with wrong password
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["email"],
                "password": "WrongPassword123!"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code in [400, 401]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user fails."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code in [400, 401, 404]

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """Test getting current user profile."""
        response = await client.get(
            "/api/v1/user/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data

    @pytest.mark.asyncio
    async def test_protected_route_no_token(self, client: AsyncClient):
        """Test accessing protected route without token fails."""
        response = await client.get("/api/v1/user/me")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_protected_route_invalid_token(self, client: AsyncClient):
        """Test accessing protected route with invalid token fails."""
        response = await client.get(
            "/api/v1/user/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code in [401, 403]
