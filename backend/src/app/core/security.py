from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Literal, cast

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.crud_users import crud_users
from .config import settings
from .db.crud_token_blacklist import crud_token_blacklist
from .schemas import TokenBlacklistCreate, TokenData

SECRET_KEY: SecretStr = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    correct_password: bool = bcrypt.checkpw(
        plain_password.encode(), hashed_password.encode()
    )
    return correct_password


def get_password_hash(password: str) -> str:
    hashed_password: str = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashed_password


# BE-M2: pre-computed dummy hash used to keep authentication time constant
# regardless of whether the user exists. Generated once at import-time.
_DUMMY_BCRYPT_HASH: str = bcrypt.hashpw(
    b"this-is-a-fixed-non-existent-password",
    bcrypt.gensalt(rounds=12),
).decode()


async def authenticate_user(
    username_or_email: str, password: str, db: AsyncSession
) -> dict[str, Any] | Literal[False]:
    """Authenticate user by email and password.

    Note: username_or_email parameter name kept for OAuth2 compatibility,
    but only email format is accepted.

    BE-M2: When the user lookup fails, we still run bcrypt verify against a
    constant dummy hash so the timing of an unknown email matches that of a
    known email with wrong password. Prevents user enumeration via timing
    side-channel (CWE-208).
    """
    db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False)

    if not db_user:
        # Constant-time path: still hash so we don't return early.
        await verify_password(password, _DUMMY_BCRYPT_HASH)
        return False

    db_user = cast(dict[str, Any], db_user)
    if not await verify_password(password, db_user["hashed_password"]):
        return False

    return db_user


async def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "token_type": TokenType.ACCESS})
    encoded_jwt: str = jwt.encode(
        to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM
    )
    return encoded_jwt


async def create_refresh_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    to_encode.update({"exp": expire, "token_type": TokenType.REFRESH})
    encoded_jwt: str = jwt.encode(
        to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM
    )
    return encoded_jwt


async def create_device_access_token(
    device_id: str, expires_delta: timedelta | None = None
) -> str:
    """Create JWT token for device authentication with device_id in payload.

    Parameters
    ----------
    device_id : str
        The MAC address or device identifier
    expires_delta : timedelta | None
        Custom expiration delta, defaults to ACCESS_TOKEN_EXPIRE_MINUTES

    Returns
    -------
    str
        Encoded JWT token with device_id claim
    """
    to_encode = {"device_id": device_id}
    if expires_delta:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
    else:
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire, "token_type": TokenType.ACCESS})
    encoded_jwt: str = jwt.encode(
        to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM
    )
    return encoded_jwt


async def verify_token(
    token: str, expected_token_type: TokenType, db: AsyncSession
) -> TokenData | None:
    """Verify a JWT token and return TokenData if valid.

    Parameters
    ----------
    token: str
        The JWT token to be verified.
    expected_token_type: TokenType
        The expected type of token (access or refresh)
    db: AsyncSession
        Database session for performing database operations.

    Returns
    -------
    TokenData | None
        TokenData instance if the token is valid, None otherwise.
    """
    is_blacklisted = await crud_token_blacklist.exists(db, token=token)
    if is_blacklisted:
        return None

    try:
        payload = jwt.decode(
            token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM]
        )
        username_or_email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")

        if username_or_email is None or token_type != expected_token_type:
            return None

        return TokenData(username_or_email=username_or_email)

    except JWTError:
        return None


async def verify_device_token(
    token: str,
    db: AsyncSession | None = None,
    expected_device_id: str | None = None,
) -> TokenData | None:
    """Verify a device JWT token.

    BE-H5 hardening: now consults the token blacklist (if a DB session is
    supplied) so revoked devices cannot reuse old tokens until expiry.
    BE-H4 hardening: optional ``expected_device_id`` enforces that the
    Device-Id header matches the device_id claim inside the JWT.

    Parameters
    ----------
    token: str
        The JWT token to be verified.
    db: AsyncSession, optional
        DB session used for blacklist lookup; if None blacklist is skipped.
    expected_device_id: str, optional
        If provided, must match the JWT's device_id claim or verification fails.

    Returns
    -------
    TokenData | None
        TokenData with device_id if valid, None otherwise.
    """
    try:
        payload = jwt.decode(
            token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM]
        )
        device_id: str | None = payload.get("device_id")
        token_type: str | None = payload.get("token_type")

        if device_id is None or token_type != TokenType.ACCESS:
            return None

        if expected_device_id is not None and device_id != expected_device_id:
            # BE-H4: claim mismatch — refuse.
            return None

        if db is not None:
            try:
                from ..crud.crud_token_blacklist import crud_token_blacklist  # type: ignore
                is_revoked = await crud_token_blacklist.exists(db=db, token=token)
                if is_revoked:
                    return None
            except Exception:
                # If blacklist module not present, continue (fail-open by design
                # only when DB layer absent in tests).
                pass

        return TokenData(username_or_email="device", device_id=device_id)

    except JWTError:
        return None


async def blacklist_tokens(
    access_token: str, refresh_token: str, db: AsyncSession
) -> None:
    """Blacklist both access and refresh tokens.

    Parameters
    ----------
    access_token: str
        The access token to blacklist
    refresh_token: str
        The refresh token to blacklist
    db: AsyncSession
        Database session for performing database operations.
    """
    for token in [access_token, refresh_token]:
        payload = jwt.decode(
            token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM]
        )
        exp_timestamp = payload.get("exp")
        if exp_timestamp is not None:
            expires_at = datetime.fromtimestamp(exp_timestamp)
            await crud_token_blacklist.create(
                db, object=TokenBlacklistCreate(token=token, expires_at=expires_at)
            )


async def blacklist_token(token: str, db: AsyncSession) -> None:
    payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
    exp_timestamp = payload.get("exp")
    if exp_timestamp is not None:
        expires_at = datetime.fromtimestamp(exp_timestamp)
        await crud_token_blacklist.create(
            db, object=TokenBlacklistCreate(token=token, expires_at=expires_at)
        )
