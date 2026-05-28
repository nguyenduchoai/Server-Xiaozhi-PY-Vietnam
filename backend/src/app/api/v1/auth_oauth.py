"""OAuth Authentication — Google & Zalo.

Provides social login via Google OAuth 2.0 and Zalo OAuth.
Settings are stored in system_setting table (SuperAdmin configurable).

Security:
- OAuth state stored in Redis (not memory) to prevent replay attacks
- State expires after 10 minutes
- PKCE for Zalo OAuth
- Rate limiting on auth endpoints

Flow:
1. Frontend redirects user to /auth/google (or /auth/zalo)
2. Backend redirects to provider's consent page
3. Provider redirects back with authorization code
4. Backend exchanges code for user info
5. Create or find user → return JWT tokens
"""

import json
import secrets
from typing import Annotated, Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_redis_client
from ...core.config import settings
from ...core.db.database import async_get_db
from ...core.logger import get_logger
from ...core.rate_limit import rate_limit_auth
from ...core.security import (
    create_refresh_token,
    get_password_hash,
)
from ...crud.crud_system_setting import crud_system_setting
from ...models.user import User, UserRole

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth-oauth"])

# OAuth state TTL: 10 minutes
OAUTH_STATE_TTL = 600

# Redis key prefix for OAuth states
OAUTH_STATE_PREFIX = "oauth:state:"


# ============ Redis State Store ============


async def _save_oauth_state(redis: Redis, state: str, data: dict) -> None:
    """Save OAuth state to Redis with TTL."""
    key = f"{OAUTH_STATE_PREFIX}{state}"
    await redis.set(key, json.dumps(data), ex=OAUTH_STATE_TTL)


async def _pop_oauth_state(redis: Redis, state: str) -> dict | None:
    """Get and delete OAuth state from Redis (one-time use)."""
    key = f"{OAUTH_STATE_PREFIX}{state}"
    data = await redis.get(key)
    if data:
        await redis.delete(key)
        return json.loads(data)
    return None


# ============ Helpers ============


async def _get_oauth_setting(db: AsyncSession, key: str) -> Any:
    """Get an OAuth setting from system_setting table."""
    return await crud_system_setting.get(db, key)


async def _find_or_create_user(
    db: AsyncSession,
    email: str,
    name: str,
    provider: str,
) -> User:
    """Find existing user by email or create new one."""
    normalized_email = email.lower().strip()

    # Find existing user
    result = await db.execute(select(User).where(func.lower(User.email) == normalized_email))
    user = result.scalar_one_or_none()

    if user:
        # If shadow user, upgrade to real user
        if user.is_shadow:
            user.is_shadow = False
            user.name = name or user.name
            await db.flush()
            logger.info(f"Upgraded shadow user to real: {user.id} via {provider}")
        return user

    # Create new user
    user = User(
        name=name or f"User {normalized_email.split('@')[0]}",
        email=normalized_email,
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        timezone="Asia/Ho_Chi_Minh",
        role=UserRole.USER,
    )
    db.add(user)
    await db.flush()

    # Auto-assign FREE plan
    try:
        from datetime import datetime, timezone
        from uuid import uuid4

        from sqlalchemy import text

        result = await db.execute(text("SELECT id FROM subscription_plan WHERE name = 'FREE' LIMIT 1"))
        free_plan = result.fetchone()
        if free_plan:
            now = datetime.now(timezone.utc)
            await db.execute(
                text("""
                    INSERT INTO user_subscription (id, user_id, plan_id, status, billing_cycle, started_at, current_period_start, created_at)
                    VALUES (:id, :user_id, :plan_id, 'active', 'lifetime', :now, :now, :now)
                """),
                {"id": str(uuid4()), "user_id": user.id, "plan_id": free_plan[0], "now": now},
            )
    except Exception as e:
        logger.warning(f"Failed to assign FREE plan for OAuth user: {e}")

    await db.commit()
    logger.info(f"Created new user via {provider}: {user.id} ({normalized_email})")
    return user


async def _create_tokens_and_redirect(
    user: User,
    frontend_url: str,
) -> RedirectResponse:
    """Create refresh token cookie and redirect to frontend."""
    refresh_token = await create_refresh_token(data={"sub": user.email})

    redirect_url = f"{frontend_url}/oauth-callback?oauth=success"

    resp = RedirectResponse(url=redirect_url, status_code=302)

    # Also set refresh token cookie
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    resp.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
    )

    return resp


def _get_frontend_url(request: Request) -> str:
    """Get frontend URL from request headers."""
    scheme = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host", "localhost")
    return f"{scheme}://{host}"


def _get_callback_url(request: Request, route_name: str, path: str) -> str:
    """Build callback URL, handling reverse proxy correctly."""
    callback_url = str(request.url_for(route_name))
    if "localhost" in callback_url and "localhost" not in request.headers.get("host", ""):
        scheme = request.headers.get("x-forwarded-proto", "https")
        host = request.headers.get("host", "localhost")
        callback_url = f"{scheme}://{host}{path}"
    return callback_url


# ============ Google OAuth ============


@router.get("/google", dependencies=[Depends(rate_limit_auth)])
async def google_login(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    """Redirect to Google OAuth consent page."""
    enabled = await _get_oauth_setting(db, "oauth.google.enabled")
    if not enabled:
        raise HTTPException(400, "Google login chưa được bật")

    client_id = await _get_oauth_setting(db, "oauth.google.client_id")
    if not client_id:
        raise HTTPException(500, "Google Client ID chưa cấu hình")

    # Generate state for CSRF → stored in Redis
    state = secrets.token_urlsafe(32)
    await _save_oauth_state(
        redis,
        state,
        {
            "provider": "google",
            "frontend_url": _get_frontend_url(request),
        },
    )

    callback_url = _get_callback_url(request, "google_callback", "/api/v1/auth/google/callback")

    params = {
        "client_id": client_id,
        "redirect_uri": callback_url,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }

    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return RedirectResponse(url=google_auth_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    db: AsyncSession = Depends(async_get_db),
    redis: Redis = Depends(get_redis_client),
):
    """Handle Google OAuth callback."""
    if error:
        raise HTTPException(400, f"Google login bị từ chối: {error}")

    if not code or not state:
        raise HTTPException(400, "Thiếu authorization code")

    # Verify state from Redis (CSRF protection)
    state_data = await _pop_oauth_state(redis, state)
    if not state_data:
        raise HTTPException(400, "Invalid or expired state — thử lại")

    frontend_url = state_data["frontend_url"]

    # Get settings
    client_id = await _get_oauth_setting(db, "oauth.google.client_id")
    client_secret = await _get_oauth_setting(db, "oauth.google.client_secret")

    callback_url = _get_callback_url(request, "google_callback", "/api/v1/auth/google/callback")

    # Exchange code for tokens
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
        )

        if token_resp.status_code != 200:
            logger.error(f"Google token exchange failed: {token_resp.text}")
            raise HTTPException(400, "Google đăng nhập thất bại")

        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        # Get user info
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if userinfo_resp.status_code != 200:
            raise HTTPException(400, "Không lấy được thông tin Google")

        userinfo = userinfo_resp.json()

    email = userinfo.get("email")
    name = userinfo.get("name", "")

    if not email:
        raise HTTPException(400, "Google không trả về email")

    logger.info(f"Google login: {email} ({name})")

    # Find or create user
    user = await _find_or_create_user(db, email, name, "google")

    # Create tokens and redirect
    return await _create_tokens_and_redirect(user, frontend_url)


# ============ Zalo OAuth ============


@router.get("/zalo", dependencies=[Depends(rate_limit_auth)])
async def zalo_login(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    redis: Annotated[Redis, Depends(get_redis_client)],
):
    """Redirect to Zalo OAuth consent page."""
    enabled = await _get_oauth_setting(db, "oauth.zalo.enabled")
    if not enabled:
        raise HTTPException(400, "Zalo login chưa được bật")

    app_id = await _get_oauth_setting(db, "oauth.zalo.app_id")
    if not app_id:
        raise HTTPException(500, "Zalo App ID chưa cấu hình")

    # Generate state for CSRF
    state = secrets.token_urlsafe(32)

    # Zalo OAuth needs code_verifier (PKCE)
    code_verifier = secrets.token_urlsafe(64)
    import base64
    import hashlib

    code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")

    # Store state + code_verifier in Redis
    await _save_oauth_state(
        redis,
        state,
        {
            "provider": "zalo",
            "frontend_url": _get_frontend_url(request),
            "code_verifier": code_verifier,
        },
    )

    callback_url = _get_callback_url(request, "zalo_callback", "/api/v1/auth/zalo/callback")

    params = {
        "app_id": app_id,
        "redirect_uri": callback_url,
        "state": state,
        "code_challenge": code_challenge,
    }

    zalo_auth_url = f"https://oauth.zaloapp.com/v4/permission?{urlencode(params)}"
    return RedirectResponse(url=zalo_auth_url)


@router.get("/zalo/callback")
async def zalo_callback(
    request: Request,
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    db: AsyncSession = Depends(async_get_db),
    redis: Redis = Depends(get_redis_client),
):
    """Handle Zalo OAuth callback."""
    if error:
        raise HTTPException(400, f"Zalo login bị từ chối: {error_description or error}")

    if not code or not state:
        raise HTTPException(400, "Thiếu authorization code")

    # Verify state from Redis
    state_data = await _pop_oauth_state(redis, state)
    if not state_data:
        raise HTTPException(400, "Invalid or expired state — thử lại")

    frontend_url = state_data["frontend_url"]
    code_verifier = state_data.get("code_verifier", "")

    # Get settings
    app_id = await _get_oauth_setting(db, "oauth.zalo.app_id")
    app_secret = await _get_oauth_setting(db, "oauth.zalo.app_secret")

    _get_callback_url(request, "zalo_callback", "/api/v1/auth/zalo/callback")

    # Exchange code for access token
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            "https://oauth.zaloapp.com/v4/access_token",
            headers={"secret_key": app_secret},
            data={
                "code": code,
                "app_id": app_id,
                "grant_type": "authorization_code",
                "code_verifier": code_verifier,
            },
        )

        if token_resp.status_code != 200:
            logger.error(f"Zalo token exchange failed: {token_resp.text}")
            raise HTTPException(400, "Zalo đăng nhập thất bại")

        tokens = token_resp.json()

        if "error" in tokens:
            logger.error(f"Zalo token error: {tokens}")
            raise HTTPException(400, f"Zalo lỗi: {tokens.get('error_description', tokens.get('error'))}")

        zalo_access_token = tokens.get("access_token")

        # Get user info from Zalo
        userinfo_resp = await client.get(
            "https://graph.zalo.me/v2.0/me",
            params={"fields": "id,name,picture"},
            headers={"access_token": zalo_access_token},
        )

        if userinfo_resp.status_code != 200:
            raise HTTPException(400, "Không lấy được thông tin Zalo")

        userinfo = userinfo_resp.json()

    zalo_id = userinfo.get("id")
    name = userinfo.get("name", "")

    if not zalo_id:
        raise HTTPException(400, "Zalo không trả về user ID")

    # Zalo doesn't return email — use zalo_{id}@zalo.xiaozhi.vn as identifier
    email = f"zalo_{zalo_id}@zalo.xiaozhi.vn"

    logger.info(f"Zalo login: {zalo_id} ({name})")

    # Find or create user
    user = await _find_or_create_user(db, email, name, "zalo")

    # Create tokens and redirect
    return await _create_tokens_and_redirect(user, frontend_url)
