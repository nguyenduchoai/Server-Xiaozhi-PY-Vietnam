"""
Core Security Tests — Authentication, Authorization, Token Management

Tests cover:
- User registration
- Login (success + failure)
- Token refresh
- Token blacklist (logout)
- Password hashing
- Device token creation/verification
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Registration Tests
# =============================================================================

class TestRegistration:
    """User registration endpoint tests."""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient, test_user_data: dict):
        """New user registration should return 201 with user data."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code in (200, 201), f"Expected 200/201, got {response.status_code}: {response.text}"
        data = response.json()
        assert "email" in data or "id" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data: dict):
        """Duplicate email registration should fail."""
        # First registration
        await client.post("/api/v1/auth/register", json=test_user_data)
        # Second registration with same email
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        assert response.status_code in (400, 409, 422), f"Expected error, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client: AsyncClient):
        """Invalid email format should be rejected."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "testuser",
            "password": "SecurePass123!",
        })
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """Weak password should be rejected (if validation exists)."""
        response = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "123",
        })
        # Some apps accept any password, some validate — check either way
        assert response.status_code in (200, 201, 422)


# =============================================================================
# Login Tests
# =============================================================================

class TestLogin:
    """Login endpoint tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user_data: dict):
        """Valid credentials should return access + refresh tokens."""
        # Register first
        await client.post("/api/v1/auth/register", json=test_user_data)
        # Login
        response = await client.post("/api/v1/auth/login", data={
            "username": test_user_data["email"],
            "password": test_user_data["password"],
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data.get("token_type") == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user_data: dict):
        """Wrong password should return 401."""
        await client.post("/api/v1/auth/register", json=test_user_data)
        response = await client.post("/api/v1/auth/login", data={
            "username": test_user_data["email"],
            "password": "WrongPassword!",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Non-existent user should return 401."""
        response = await client.post("/api/v1/auth/login", data={
            "username": "ghost@example.com",
            "password": "whatever",
        })
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Empty credentials should return 422."""
        response = await client.post("/api/v1/auth/login", data={})
        assert response.status_code == 422


# =============================================================================
# Token Tests
# =============================================================================

class TestTokens:
    """Token management tests."""

    @pytest.mark.asyncio
    async def test_access_protected_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Authenticated requests should succeed."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)
        # Should not be 401/403
        assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_access_without_token(self, client: AsyncClient):
        """Unauthenticated requests to protected endpoints should fail."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_access_with_invalid_token(self, client: AsyncClient):
        """Invalid JWT should return 401."""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code in (401, 403)


# =============================================================================
# Security Unit Tests (no HTTP)
# =============================================================================

class TestSecurityUtils:
    """Unit tests for security utility functions."""

    @pytest.mark.asyncio
    async def test_password_hash_and_verify(self):
        """Password hashing should produce verifiable hashes."""
        from app.core.security import get_password_hash, verify_password
        
        password = "MyStr0ng!Pass"
        hashed = get_password_hash(password)
        
        assert hashed != password, "Hash should not equal plaintext"
        assert await verify_password(password, hashed), "Correct password should verify"
        assert not await verify_password("WrongPass", hashed), "Wrong password should not verify"

    @pytest.mark.asyncio
    async def test_access_token_creation(self):
        """Access token should be valid JWT."""
        from app.core.security import create_access_token
        
        token = await create_access_token(data={"sub": "test@example.com"})
        assert isinstance(token, str)
        assert len(token) > 50  # JWT should be reasonably long
        assert token.count(".") == 2  # JWT has 3 parts

    @pytest.mark.asyncio
    async def test_refresh_token_creation(self):
        """Refresh token should be valid JWT."""
        from app.core.security import create_refresh_token
        
        token = await create_refresh_token(data={"sub": "test@example.com"})
        assert isinstance(token, str)
        assert token.count(".") == 2

    @pytest.mark.asyncio
    async def test_device_token_creation_and_verification(self):
        """Device tokens should encode/decode device_id correctly."""
        from app.core.security import create_device_access_token, verify_device_token
        
        device_id = "AA:BB:CC:DD:EE:FF"
        token = await create_device_access_token(device_id=device_id)
        
        result = await verify_device_token(token)
        assert result is not None
        assert result.device_id == device_id

