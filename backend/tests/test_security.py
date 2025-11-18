import pytest
from datetime import datetime, timedelta
from jose import jwt

from app.core.security import (
    create_access_token,
    verify_password,
    get_password_hash,
    generate_api_key,
    hash_api_key,
    verify_api_key,
    verify_token,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.core.config import settings


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_same_password_different_hashes(self):
        """Test that hashing same password produces different hashes (salt)."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token functions."""

    def test_create_access_token(self):
        """Test creating access token."""
        data = {"sub": "test_user", "user_id": 123}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test_user"
        assert payload["user_id"] == 123
        assert "exp" in payload

    def test_create_access_token_with_expiry(self):
        """Test creating access token with custom expiry."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data, expires_delta=expires_delta)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()

        # Should expire in about 15 minutes
        time_diff = (exp_time - now).total_seconds()
        assert 14 * 60 < time_diff < 16 * 60

    def test_create_access_token_default_expiry(self):
        """Test creating access token with default expiry."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()

        # Should expire in about 30 minutes (default)
        time_diff = (exp_time - now).total_seconds()
        assert 29 * 60 < time_diff < 31 * 60

    def test_verify_token_valid(self):
        """Test verifying valid token."""
        data = {"sub": "test_user", "user_id": 123}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload is not None
        assert payload["sub"] == "test_user"
        assert payload["user_id"] == 123

    def test_verify_token_invalid(self):
        """Test verifying invalid token."""
        invalid_token = "invalid.token.here"
        payload = verify_token(invalid_token)

        assert payload is None

    def test_verify_token_expired(self):
        """Test verifying expired token."""
        data = {"sub": "test_user"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = create_access_token(data, expires_delta=expires_delta)

        payload = verify_token(token)

        assert payload is None

    def test_token_contains_expiry(self):
        """Test that token contains expiry claim."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        assert "exp" in payload
        assert isinstance(payload["exp"], int)
        assert payload["exp"] > datetime.utcnow().timestamp()


class TestAPIKeys:
    """Test API key functions."""

    def test_generate_api_key(self):
        """Test generating API key."""
        api_key = generate_api_key()

        assert isinstance(api_key, str)
        assert len(api_key) > 0
        # URL-safe base64 typically has - and _ characters
        assert all(c.isalnum() or c in '-_' for c in api_key)

    def test_generate_unique_api_keys(self):
        """Test that generated API keys are unique."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        assert key1 != key2

    def test_hash_api_key(self):
        """Test hashing API key."""
        api_key = "test_api_key_123"
        hashed = hash_api_key(api_key)

        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 hex digest length
        assert hashed != api_key
        assert hashed.isalnum()  # Hex string

    def test_hash_api_key_consistent(self):
        """Test that hashing same API key produces same hash."""
        api_key = "test_api_key_123"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        assert hash1 == hash2

    def test_verify_api_key_correct(self):
        """Test verifying correct API key."""
        api_key = "test_api_key_123"
        hashed = hash_api_key(api_key)

        assert verify_api_key(api_key, hashed) is True

    def test_verify_api_key_incorrect(self):
        """Test verifying incorrect API key."""
        api_key = "test_api_key_123"
        wrong_key = "wrong_api_key"
        hashed = hash_api_key(api_key)

        assert verify_api_key(wrong_key, hashed) is False

    def test_api_key_length(self):
        """Test API key has sufficient length."""
        api_key = generate_api_key()

        # URL-safe base64 with 32 bytes produces ~43 characters
        assert len(api_key) >= 40


class TestSecurityConstants:
    """Test security constants and configuration."""

    def test_algorithm_is_hs256(self):
        """Test JWT algorithm is HS256."""
        assert ALGORITHM == "HS256"

    def test_access_token_expiry_configured(self):
        """Test access token expiry is configured."""
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert isinstance(ACCESS_TOKEN_EXPIRE_MINUTES, int)

    def test_secret_key_configured(self):
        """Test secret key is configured."""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0
        # Should not be the old default
        assert "default-secret-key" not in settings.SECRET_KEY.lower()


class TestSecurityHeaders:
    """Test security headers configuration."""

    def test_security_headers_imported(self):
        """Test security headers can be imported."""
        from app.core.security import SECURITY_HEADERS

        assert SECURITY_HEADERS is not None
        assert isinstance(SECURITY_HEADERS, dict)

    def test_security_headers_content(self):
        """Test security headers contain expected values."""
        from app.core.security import SECURITY_HEADERS

        assert "X-Content-Type-Options" in SECURITY_HEADERS
        assert "X-Frame-Options" in SECURITY_HEADERS
        assert "X-XSS-Protection" in SECURITY_HEADERS
        assert "Strict-Transport-Security" in SECURITY_HEADERS
        assert "Content-Security-Policy" in SECURITY_HEADERS
        assert "Referrer-Policy" in SECURITY_HEADERS

        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"


class TestPasswordStrength:
    """Test password hashing with different password types."""

    def test_hash_short_password(self):
        """Test hashing short password."""
        password = "abc"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_long_password(self):
        """Test hashing long password."""
        password = "a" * 100
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_special_characters(self):
        """Test hashing password with special characters."""
        password = "p@ssw0rd!#$%^&*()"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_hash_unicode_password(self):
        """Test hashing password with unicode characters."""
        password = "пароль_密码_🔐"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True


class TestTokenSecurity:
    """Test token security features."""

    def test_token_cannot_be_modified(self):
        """Test that modifying token makes it invalid."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        # Modify token
        modified_token = token[:-5] + "XXXXX"

        payload = verify_token(modified_token)
        assert payload is None

    def test_token_with_different_secret(self):
        """Test that token cannot be verified with different secret."""
        data = {"sub": "test_user"}
        token = create_access_token(data)

        # Try to decode with wrong secret
        with pytest.raises(Exception):
            jwt.decode(token, "wrong_secret_key", algorithms=[ALGORITHM])

    def test_token_payload_integrity(self):
        """Test token payload integrity."""
        original_data = {
            "sub": "test_user",
            "user_id": 123,
            "role": "admin"
        }
        token = create_access_token(original_data.copy())

        payload = verify_token(token)

        assert payload["sub"] == original_data["sub"]
        assert payload["user_id"] == original_data["user_id"]
        assert payload["role"] == original_data["role"]
