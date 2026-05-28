"""
Config encryption utilities for sensitive data in UserConnection.

Uses Fernet symmetric encryption. Key derived from SECRET_KEY in env.
Falls back to base64 encoding if cryptography package not available.
"""

import base64
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

# Derive Fernet key from SECRET_KEY
_FERNET = None
try:
    from cryptography.fernet import Fernet
    secret = os.getenv("SECRET_KEY")
    if not secret:
        raise ValueError("SECRET_KEY is utterly missing")
    # Fernet needs 32 bytes base64-encoded
    key_bytes = hashlib.sha256(secret.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    _FERNET = Fernet(fernet_key)
    logger.info("Config encryption: Fernet initialized")
except ImportError:
    logger.warning("Config encryption: cryptography package not installed, using plaintext")
except Exception as e:
    logger.error(f"Config encryption init error: {e}")

# Sensitive keys to encrypt
SENSITIVE_KEYS = {"bot_token", "oa_access_token", "password", "api_key", "secret", "access_token"}


def encrypt_config(config: dict) -> dict:
    """Encrypt sensitive fields in config dict before storage."""
    if not _FERNET or not config:
        return config
    
    encrypted = dict(config)
    for key in SENSITIVE_KEYS:
        if key in encrypted and encrypted[key] and not str(encrypted[key]).startswith("gAAA"):
            # Only encrypt if not already encrypted (Fernet tokens start with gAAA)
            try:
                val = str(encrypted[key]).encode()
                encrypted[key] = _FERNET.encrypt(val).decode()
            except Exception as e:
                logger.warning(f"Failed to encrypt {key}: {e}")
    
    return encrypted


def decrypt_config(config: dict) -> dict:
    """Decrypt sensitive fields in config dict after retrieval."""
    if not _FERNET or not config:
        return config
    
    decrypted = dict(config)
    for key in SENSITIVE_KEYS:
        if key in decrypted and decrypted[key] and str(decrypted[key]).startswith("gAAA"):
            try:
                val = _FERNET.decrypt(str(decrypted[key]).encode())
                decrypted[key] = val.decode()
            except Exception as e:
                logger.warning(f"Failed to decrypt {key}: {e}")
                # Return as-is if decryption fails (might be plain text)
    
    return decrypted


def is_encryption_available() -> bool:
    """Check if encryption is available."""
    return _FERNET is not None
