"""
Sentry Error Tracking Integration

Provides production error tracking, performance monitoring,
and exception reporting via Sentry.

Usage:
    1. Set SENTRY_DSN environment variable
    2. Call init_sentry() in app startup
"""

import os
from typing import Optional

from app.core.logger import get_logger

logger = get_logger(__name__)


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
) -> bool:
    """
    Initialize Sentry SDK for error tracking.
    
    Args:
        dsn: Sentry DSN (from SENTRY_DSN env var if not provided)
        environment: Environment name (production, staging, development)
        release: Release version
    
    Returns:
        bool: True if Sentry was initialized, False otherwise
    """
    # Get DSN from env if not provided
    sentry_dsn = dsn or os.environ.get("SENTRY_DSN", "")
    
    if not sentry_dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        # Determine environment
        env = environment or os.environ.get("ENVIRONMENT", "production")
        
        # Get release version
        version = release or os.environ.get("APP_VERSION", "1.0.0")
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=env,
            release=f"xiaozhi-ai@{version}",
            
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(
                    level=None,  # Capture all log levels
                    event_level="ERROR",  # Only send errors and above
                ),
            ],
            
            # Performance monitoring
            traces_sample_rate=0.1,  # 10% of transactions
            profiles_sample_rate=0.1,  # 10% of transactions
            
            # Error filtering
            before_send=_before_send,
            
            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personal identifiable info
            max_breadcrumbs=50,
            
            # Ignore certain errors
            ignore_errors=[
                "asyncio.CancelledError",
                "websockets.exceptions.ConnectionClosed",
            ],
        )
        
        logger.info(f"Sentry initialized: env={env}, release=xiaozhi-ai@{version}")
        return True
        
    except ImportError:
        logger.warning("sentry-sdk not installed, error tracking disabled")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def _before_send(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter or modify events before sending to Sentry.
    
    Returns:
        Modified event or None to drop
    """
    # Get exception info
    if "exc_info" in hint:
        exc_type, exc_value, _ = hint["exc_info"]
        
        # Ignore specific exceptions
        ignored_exceptions = [
            "ConnectionResetError",
            "BrokenPipeError",
            "asyncio.TimeoutError",
        ]
        
        if exc_type.__name__ in ignored_exceptions:
            return None
        
        # Ignore 404 errors
        if hasattr(exc_value, "status_code") and exc_value.status_code == 404:
            return None
    
    # Filter out sensitive data from request
    if "request" in event and "data" in event["request"]:
        data = event["request"]["data"]
        if isinstance(data, dict):
            # Redact sensitive fields
            sensitive_fields = ["password", "token", "api_key", "secret", "credit_card"]
            for field in sensitive_fields:
                if field in data:
                    data[field] = "[REDACTED]"
    
    return event


def capture_exception(exc: Exception, **extra) -> Optional[str]:
    """
    Manually capture and report an exception to Sentry.
    
    Args:
        exc: Exception to report
        **extra: Additional context to attach
    
    Returns:
        Event ID if sent, None otherwise
    """
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            
            event_id = sentry_sdk.capture_exception(exc)
            return event_id
            
    except ImportError:
        logger.error(f"Exception (sentry not available): {exc}")
        return None
    except Exception as e:
        logger.error(f"Failed to capture exception: {e}")
        return None


def capture_message(message: str, level: str = "info", **extra) -> Optional[str]:
    """
    Send a message to Sentry.
    
    Args:
        message: Message to send
        level: Log level (info, warning, error)
        **extra: Additional context
    
    Returns:
        Event ID if sent, None otherwise
    """
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            
            event_id = sentry_sdk.capture_message(message, level=level)
            return event_id
            
    except ImportError:
        logger.info(f"Message (sentry not available): {message}")
        return None
    except Exception as e:
        logger.error(f"Failed to capture message: {e}")
        return None


def set_user(user_id: str, email: Optional[str] = None, username: Optional[str] = None):
    """
    Set user context for Sentry events.
    
    Args:
        user_id: User ID
        email: Optional email
        username: Optional username
    """
    try:
        import sentry_sdk
        
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            "username": username,
        })
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Failed to set Sentry user: {e}")


def add_breadcrumb(message: str, category: str = "custom", level: str = "info", **data):
    """
    Add a breadcrumb for debugging.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., "http", "db", "custom")
        level: Level (debug, info, warning, error)
        **data: Additional data
    """
    try:
        import sentry_sdk
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data,
        )
    except ImportError:
        pass
    except Exception:
        pass
