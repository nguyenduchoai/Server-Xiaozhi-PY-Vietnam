"""
Config encryption utilities for sensitive data in UserConnection and Providers.

Uses Fernet symmetric encryption. 
For enhanced security (BYOK), it uses HKDF to derive a unique master key 
per user using the SECRET_KEY and user_id. Falls back to a global key if user_id is missing.
"""

import base64
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

# Derive global Fernet key from SECRET_KEY (fallback)
_FERNET = None
_SECRET_KEY = os.getenv("SECRET_KEY")

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    
    if not _SECRET_KEY:
        raise ValueError("SECRET_KEY is utterly missing")
    
    # Global Fernet needs 32 bytes base64-encoded
    key_bytes = hashlib.sha256(_SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    _FERNET = Fernet(fernet_key)
    logger.info("Config encryption: Global Fernet initialized")
except ImportError:
    logger.warning("Config encryption: cryptography package not installed, using plaintext")
except Exception as e:
    logger.error(f"Config encryption init error: {e}")

# Sensitive keys to encrypt
SENSITIVE_KEYS = {"bot_token", "oa_access_token", "password", "api_key", "secret", "access_token"}


def _get_fernet_for_user(user_id: str):
    """Derive a unique Fernet instance for a specific user using HKDF."""
    if not _SECRET_KEY:
        return None
    try:
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=user_id.encode(),
            info=b"xiaozhi-ce-key-encryption",
        )
        key = hkdf.derive(_SECRET_KEY.encode())
        return Fernet(base64.urlsafe_b64encode(key))
    except Exception as e:
        logger.error(f"Failed to derive user Fernet: {e}")
        return None


def encrypt_config(config: dict, user_id: str = None) -> dict:
    """Encrypt sensitive fields in config dict before storage."""
    if not config:
        return config
        
    fernet = _get_fernet_for_user(user_id) if user_id else _FERNET
    if not fernet:
        return config
    
    encrypted = dict(config)
    for key in SENSITIVE_KEYS:
        if key in encrypted and encrypted[key] and not str(encrypted[key]).startswith("gAAA"):
            # Only encrypt if not already encrypted (Fernet tokens start with gAAA)
            try:
                val = str(encrypted[key]).encode()
                encrypted[key] = fernet.encrypt(val).decode()
            except Exception as e:
                logger.warning(f"Failed to encrypt {key}: {e}")
    
    return encrypted


def decrypt_config(config: dict, user_id: str = None) -> dict:
    """Decrypt sensitive fields in config dict after retrieval."""
    if not config:
        return config
        
    fernet = _get_fernet_for_user(user_id) if user_id else _FERNET
    if not fernet and not _FERNET:
        return config
    
    decrypted = dict(config)
    for key in SENSITIVE_KEYS:
        if key in decrypted and decrypted[key] and str(decrypted[key]).startswith("gAAA"):
            try:
                success = False
                # Try user-specific fernet first
                if fernet:
                    try:
                        val = fernet.decrypt(str(decrypted[key]).encode())
                        decrypted[key] = val.decode()
                        success = True
                    except Exception:
                        pass # Fallback to global
                
                # Fallback to global fernet
                if not success and _FERNET:
                    val = _FERNET.decrypt(str(decrypted[key]).encode())
                    decrypted[key] = val.decode()
            except Exception as e:
                logger.warning(f"Failed to decrypt {key}: {e}")
                # Return as-is if decryption fails (might be plain text)
    
    return decrypted


def is_encryption_available() -> bool:
    """Check if encryption is available."""
    return _FERNET is not None

