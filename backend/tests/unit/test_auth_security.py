"""
Tests for Authentication and Security Utilities

Tests JWT token handling, password hashing, and security utilities.
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
from unittest.mock import patch

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_password_hash,
    verify_password,
    TokenPayload,
)
from app.core.auth import AuthManager


class TestPasswordHashing:
    """Tests for password hashing utilities."""
    
    def test_password_hash_creates_hash(self):
        """Test that get_password_hash creates a hash."""
        password = "secure_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")
    
    def test_password_hash_different_for_same_input(self):
        """Test that same password creates different hashes (salting)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
    
    def test_verify_password_correct(self):
        """Test verify_password with correct password."""
        password = "correct_password"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test verify_password with incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_verify_password_empty_password(self):
        """Test verify_password with empty password."""
        hashed = get_password_hash("password")
        
        assert verify_password("", hashed) is False


class TestJWTTokenCreation:
    """Tests for JWT token creation."""
    
    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2
    
    def test_create_access_token_with_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "user123"}
        expires_delta = timedelta(hours=2)
        token = create_access_token(data, expires_delta=expires_delta)
        
        assert isinstance(token, str)
        
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        assert "exp" in decoded
    
    def test_create_refresh_token(self):
        """Test creating refresh token."""
        data = {"sub": "user123"}
        token = create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_access_token_has_required_claims(self):
        """Test that access token has required claims."""
        data = {"sub": "user123", "email": "user@example.com"}
        token = create_access_token(data)
        
        decoded = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        assert "sub" in decoded
        assert "email" in decoded
        assert "exp" in decoded
        assert "iat" in decoded
        assert "type" in decoded
        assert decoded["type"] == "access"


class TestTokenVerification:
    """Tests for token verification."""
    
    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        from app.core.config import settings
        
        data = {"sub": "user123"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload.sub == "user123"
    
    def test_verify_expired_token(self):
        """Test verifying an expired token."""
        from app.core.config import settings
        
        data = {"sub": "user123"}
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expires_delta)
        
        payload = verify_token(token)
        
        assert payload is None
    
    def test_verify_invalid_token(self):
        """Test verifying an invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = verify_token(invalid_token)
        
        assert payload is None
    
    def test_verify_malformed_token(self):
        """Test verifying a malformed token."""
        malformed_token = "not-a-jwt"
        
        payload = verify_token(malformed_token)
        
        assert payload is None


class TestTokenPayload:
    """Tests for TokenPayload dataclass."""
    
    def test_token_payload_creation(self):
        """Test creating TokenPayload."""
        payload = TokenPayload(
            sub="user123",
            exp=datetime.utcnow() + timedelta(hours=1),
        )
        
        assert payload.sub == "user123"
        assert payload.exp is not None
    
    def test_token_payload_optional_fields(self):
        """Test TokenPayload with optional fields."""
        payload = TokenPayload(
            sub="user123",
            email="user@example.com",
            username="testuser",
        )
        
        assert payload.email == "user@example.com"
        assert payload.username == "testuser"


class TestAuthManager:
    """Tests for AuthManager class."""
    
    def test_auth_manager_initialization(self):
        """Test AuthManager initialization."""
        manager = AuthManager()
        
        assert manager is not None
    
    def test_auth_manager_generate_device_token(self):
        """Test generating device token."""
        manager = AuthManager()
        
        token = manager.generate_device_token("device123")
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_auth_manager_verify_device_token(self):
        """Test verifying device token."""
        manager = AuthManager()
        
        device_id = "device123"
        token = manager.generate_device_token(device_id)
        
        verified_device_id = manager.verify_device_token(token)
        
        assert verified_device_id == device_id
    
    def test_auth_manager_verify_invalid_device_token(self):
        """Test verifying invalid device token."""
        manager = AuthManager()
        
        result = manager.verify_device_token("invalid_token")
        
        assert result is None


class TestSecurityEdgeCases:
    """Tests for security edge cases."""
    
    def test_password_hash_special_characters(self):
        """Test hashing passwords with special characters."""
        password = "P@$$w0rd!#$%^&*()"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_hash_unicode(self):
        """Test hashing passwords with unicode characters."""
        password = "密码测试123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_password_hash_long_password(self):
        """Test hashing long passwords."""
        password = "a" * 1000
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_token_with_unicode_data(self):
        """Test creating token with unicode data."""
        data = {"sub": "user123", "name": "用户你好"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
    
    def test_multiple_tokens_same_data(self):
        """Test that multiple tokens for same data are different."""
        data = {"sub": "user123"}
        token1 = create_access_token(data)
        token2 = create_access_token(data)
        
        assert token1 != token2


class TestSecurityConstants:
    """Tests for security constants and configuration."""
    
    def test_algorithm_is_hs256(self):
        """Test that JWT algorithm is HS256."""
        from app.core.config import settings
        
        assert settings.JWT_ALGORITHM == "HS256"
    
    def test_access_token_expire_minutes(self):
        """Test access token expiry configuration."""
        from app.core.config import settings
        
        assert settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES > 0
    
    def test_refresh_token_expire_minutes(self):
        """Test refresh token expiry configuration."""
        from app.core.config import settings
        
        assert settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES > settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
