from datetime import timedelta
from typing import Annotated, Optional, cast

from fastapi import APIRouter, Body, Cookie, Depends, Request, Response, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from ...core.config import settings
from ...core.db.database import async_get_db
from ...api.dependencies import get_current_user
from ...core.exceptions.http_exceptions import (
    DuplicateValueException,
    NotFoundException,
    UnauthorizedException,
)
from ...core.logger import get_logger
from ...core.schemas import Token
from ...core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenType,
    authenticate_user,
    blacklist_tokens,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    oauth2_scheme,
    verify_token,
)
from ...crud.crud_users import crud_users
from ...schemas.user import UserCreate, UserCreateInternal, UserRead
from ...schemas.base import SuccessResponse
from ...services.email_service import get_email_service
from ...core.rate_limit import rate_limit_auth, rate_limit_strict
from ...models.user import User
from ...models.user import User as UserModel
from datetime import datetime, timezone
from sqlalchemy import select, func, update

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


# Schemas for password reset
class ForgotPasswordRequest(BaseModel):
    """Request body for forgot password"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request body for reset password"""
    token: str
    new_password: str


@router.post("/register", response_model=UserRead, status_code=201, dependencies=[Depends(rate_limit_auth)])
async def register(
    request: Request,
    user: UserCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> UserRead:
    """Register a new user.

    Parameters
    ----------
    request : Request
        The HTTP request object
    user : UserCreate
        The user registration data (name, email, password, optional invitation_token)
    db : AsyncSession
        Database session for performing database operations

    Returns
    -------
    UserRead
        The created user with HTTP 201 status

    Raises
    ------
    DuplicateValueException
        If email already exists
    NotFoundException
        If created user cannot be retrieved
    """
    # Normalize email to lowercase
    normalized_email = user.email.lower().strip()
    
    # Check email case-insensitively using direct query
    stmt = select(User).where(func.lower(User.email) == normalized_email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise DuplicateValueException("Email is already registered")

    user_internal_dict = user.model_dump()
    user_internal_dict["email"] = normalized_email  # Store lowercase
    user_internal_dict["hashed_password"] = get_password_hash(
        password=user_internal_dict["password"]
    )
    del user_internal_dict["password"]
    
    # Remove invitation_token from internal dict (not stored in User model)
    invitation_token = user_internal_dict.pop("invitation_token", None)

    user_internal = UserCreateInternal(**user_internal_dict)
    created_user = await crud_users.create(
        db=db, object=user_internal, schema_to_select=UserRead, return_as_model=True
    )

    user_read = await crud_users.get(
        db=db, id=created_user.id, schema_to_select=UserRead, return_as_model=True
    )
    if user_read is None:
        raise NotFoundException("Created user not found")

    # Auto-assign FREE plan to new user
    try:
        from sqlalchemy import select
        from ...models.subscription_plan import SubscriptionPlan
        from ...models.user_subscription import UserSubscription, SubscriptionStatus, SubscriptionBillingCycle
        from datetime import datetime, timezone
        from uuid import uuid4
        
        # Get FREE plan (name='FREE')
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.name == "FREE")
        result = await db.execute(stmt)
        free_plan = result.scalar_one_or_none()
        
        if free_plan:
            # Create subscription for new user
            now = datetime.now(timezone.utc)
            new_subscription = UserSubscription(
                id=str(uuid4()),
                user_id=created_user.id,
                plan_id=free_plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=SubscriptionBillingCycle.LIFETIME,
                started_at=now,
                expires_at=None,  # FREE never expires
                current_period_start=now,
                current_period_end=None,
                created_at=now,
            )
            db.add(new_subscription)
            await db.commit()
    except Exception as e:
        # Log error but don't fail registration
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to auto-assign FREE plan to user {created_user.id}: {e}")

    # Process invitation token if provided
    if invitation_token:
        try:
            from sqlalchemy import text
            from datetime import datetime, timezone
            from uuid import uuid4
            from ...models.friend import Friend, FriendStatus
            
            # Validate invitation token
            result = await db.execute(
                text("""
                    SELECT id, sender_id, email, status, expires_at
                    FROM friend_invitations
                    WHERE token = :token
                """),
                {"token": invitation_token}
            )
            invitation = result.fetchone()
            
            if invitation:
                inv_id, sender_id, inv_email, status, expires_at = invitation
                
                # Check if valid
                if status == "pending" and expires_at > datetime.now(timezone.utc):
                    # Update invitation status
                    await db.execute(
                        text("""
                            UPDATE friend_invitations 
                            SET status = 'accepted', 
                                accepted_at = NOW(),
                                recipient_id = :recipient_id 
                            WHERE id = :id
                        """),
                        {"id": inv_id, "recipient_id": created_user.id}
                    )
                    
                    # Auto-create friend relationship (both directions)
                    # Sender -> New user (ACCEPTED)
                    friend1 = Friend(
                        id=str(uuid4()),
                        user_id=sender_id,
                        friend_id=created_user.id,
                        status=FriendStatus.ACCEPTED.value,
                    )
                    db.add(friend1)
                    
                    # New user -> Sender (ACCEPTED)
                    friend2 = Friend(
                        id=str(uuid4()),
                        user_id=created_user.id,
                        friend_id=sender_id,
                        status=FriendStatus.ACCEPTED.value,
                    )
                    db.add(friend2)
                    
                    await db.commit()
                    logger.info(f"Auto-accepted friend invitation: {sender_id} <-> {created_user.id}")
        except Exception as e:
            logger.error(f"Failed to process invitation token: {e}")
            # Don't fail registration, just log

    # Best-effort welcome email. SMTP being down or misconfigured must NOT
    # break registration — the user is already created and committed.
    # We deliberately don't reference free_plan here: it lives inside the
    # earlier try-block and may be unbound if the auto-assign step failed
    # before its lookup ran. Hard-coding "FREE" matches what the
    # registration flow grants by default.
    try:
        email_service = get_email_service()
        if email_service.enabled:
            email_service.send_welcome_email(
                to_email=user_read.email,
                user_name=user_read.name or user_read.email,
                plan_name="FREE",
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Failed to send welcome email to {user_read.email}: {e}"
        )

    return cast(UserRead, user_read)


@router.post("/login", response_model=Token, dependencies=[Depends(rate_limit_auth)])
async def login(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    """Authenticate user and return JWT tokens.

    Parameters
    ----------
    response : Response
        The HTTP response object for setting cookies
    form_data : OAuth2PasswordRequestForm
        Email (in username field) and password credentials
    db : AsyncSession
        Database session for performing database operations

    Returns
    -------
    dict
        Dictionary with access_token and token_type="bearer"

    Raises
    ------
    UnauthorizedException
        If credentials are invalid
    """
    user = await authenticate_user(
        username_or_email=form_data.username, password=form_data.password, db=db
    )
    if not user:
        raise UnauthorizedException("Wrong email or password.")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )

    refresh_token = await create_refresh_token(data={"sub": user["email"]})
    max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=max_age,
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/refresh")
async def refresh(
    request: Request,
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """Refresh access token using refresh token from cookie.

    Parameters
    ----------
    request : Request
        The HTTP request object containing refresh_token cookie
    db : AsyncSession
        Database session for performing database operations

    Returns
    -------
    dict
        Dictionary with new access_token and token_type="bearer"

    Raises
    ------
    UnauthorizedException
        If refresh token is missing, invalid, or expired
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise UnauthorizedException("Refresh token missing.")

    user_data = await verify_token(refresh_token, TokenType.REFRESH, db)
    if not user_data:
        raise UnauthorizedException("Invalid refresh token.")

    new_access_token = await create_access_token(
        data={"sub": user_data.username_or_email}
    )
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    access_token: str = Depends(oauth2_scheme),
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """Logout user by blacklisting tokens and clearing cookies.

    Parameters
    ----------
    response : Response
        The HTTP response object for clearing cookies
    access_token : str
        The current access token from Bearer scheme
    refresh_token : Optional[str]
        The refresh token from cookie
    db : AsyncSession
        Database session for performing database operations

    Returns
    -------
    dict
        Dictionary with success message

    Raises
    ------
    UnauthorizedException
        If refresh token is not found or tokens are invalid
    """
    if not refresh_token:
        raise UnauthorizedException("Refresh token not found")

    await blacklist_tokens(
        access_token=access_token, refresh_token=refresh_token, db=db
    )
    response.delete_cookie(key="refresh_token")

    return {"message": "Logged out successfully"}


@router.post("/delete-account", response_model=SuccessResponse[dict])
async def delete_my_account(
    request: Request,
    password: str = Body(..., embed=True, description="Current password for verification"),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
) -> SuccessResponse[dict]:
    """
    Delete the current user's account (soft delete).

    **Apple App Store Requirement** (since June 2022):
    All apps that support account creation MUST provide account deletion.

    **GDPR Article 17** - Right to Erasure:
    Users have the right to request their data be deleted.

    The account is soft-deleted with a 30-day recovery window.
    After 30 days, data is permanently purged.

    Requires password confirmation for security.
    """

    user_id = current_user["id"] if isinstance(current_user, dict) else current_user.id
    email = current_user["email"] if isinstance(current_user, dict) else current_user.email

    # Verify password using the same auth function as login
    user_data = await authenticate_user(
        username_or_email=email, password=password, db=db
    )
    if not user_data:
        raise HTTPException(status_code=400, detail="Incorrect password")

    # Soft delete

    stmt = (
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(
            is_deleted=True,
            deleted_at=datetime.now(timezone.utc),
        )
    )
    await db.execute(stmt)
    await db.commit()

    logger.info(f"User {email} requested account deletion (soft delete)")

    return SuccessResponse(
        data={
            "message": "Tài khoản đã được xóa. Bạn có 30 ngày để khôi phục.",
            "recovery_days": 30,
        },
        message="Account deleted successfully. You have 30 days to restore it.",
    )


@router.post("/restore", response_model=SuccessResponse[dict])
async def restore_deleted_account(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> SuccessResponse[dict]:
    """
    Restore soft-deleted user account.

    User can restore their account within 30 days of deletion
    by providing email and password. After successful restore,
    new tokens are issued.

    Parameters
    ----------
    response : Response
        HTTP response for setting cookies
    form_data : OAuth2PasswordRequestForm
        Email (in username field) and password
    db : AsyncSession
        Database session

    Returns
    -------
    SuccessResponse
        Success message with new access token

    Raises
    ------
    UnauthorizedException
        If credentials invalid or account not found
    HTTPException 400
        If account is not deleted
    HTTPException 410
        If grace period expired (>30 days)

    Examples
    --------
    POST /auth/restore
    username=user@example.com&password=Password123!
    """
    try:
        from datetime import datetime, timezone, timedelta

        # Get deleted user (include deleted in query)
        user = await crud_users.get(
            db=db, email=form_data.username, is_deleted=True  # Only get deleted users
        )

        if not user:
            raise UnauthorizedException("Invalid email or password")

        # Verify password
        from ...core.security import verify_password

        if not await verify_password(form_data.password, user["hashed_password"]):
            raise UnauthorizedException("Invalid email or password")

        # Check if not actually deleted
        if not user.get("is_deleted"):
            raise HTTPException(status_code=400, detail="Account is not deleted")

        # Check grace period (30 days)
        deleted_at = user.get("deleted_at")
        if deleted_at:
            grace_period = timedelta(days=30)
            if datetime.now(timezone.utc) - deleted_at > grace_period:
                raise HTTPException(
                    status_code=410,
                    detail="Restore period expired. Account permanently deleted.",
                )

        # Restore account
        await crud_users.update(
            db=db,
            object={
                "is_deleted": False,
                "deleted_at": None,
                "updated_at": datetime.now(timezone.utc),
            },
            id=user["id"],
        )

        # Create new tokens
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = await create_access_token(
            data={"sub": user["email"]}, expires_delta=access_token_expires
        )

        refresh_token = await create_refresh_token(data={"sub": user["email"]})
        max_age = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=max_age,
        )

        logger.info(f"User {user['id']} restored account")

        return SuccessResponse(
            data={
                "message": "Account restored successfully",
                "access_token": access_token,
                "token_type": "bearer",
            }
        )

    except (UnauthorizedException, HTTPException):
        raise
    except Exception as e:
        logger.error(f"Error restoring account: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to restore account")


@router.post("/forgot-password", dependencies=[Depends(rate_limit_strict)])
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict:
    """
    Request password reset email.
    
    Sends an email with a password reset link if the email exists.
    For security reasons, always returns success even if email doesn't exist.
    
    Parameters
    ----------
    request : Request
        The HTTP request object (used to get base URL)
    data : ForgotPasswordRequest
        Contains email address
    db : AsyncSession
        Database session
        
    Returns
    -------
    dict
        Success message
    """
    try:
        # Check if user exists
        user = await crud_users.get(db=db, email=data.email, is_deleted=False)
        
        if user:
            # Get email service
            email_service = get_email_service()
            
            if email_service.enabled:
                # Generate reset token
                token = email_service.generate_password_reset_token(
                    user_id=user["id"],
                    email=user["email"],
                    expire_minutes=30
                )
                
                # Build reset URL
                # Try to get frontend URL from environment or use request host
                import os
                frontend_url = os.getenv("FRONTEND_URL", "")
                if not frontend_url:
                    # Fallback: construct from request
                    scheme = request.headers.get("x-forwarded-proto", "https")
                    host = request.headers.get("host", "localhost")
                    frontend_url = f"{scheme}://{host}"
                
                reset_link = f"{frontend_url}/reset-password?token={token}"
                
                # Send email
                app_name = os.getenv("APP_NAME", "Xiaozhi AI")
                email_service.send_password_reset_email(
                    to_email=user["email"],
                    user_name=user["name"],
                    reset_link=reset_link,
                    app_name=app_name,
                )
                logger.info(f"Password reset email sent to {data.email}")
            else:
                logger.warning(f"Email service disabled. Reset requested for {data.email}")
        else:
            # User not found - still return success for security
            logger.info(f"Password reset requested for non-existent email: {data.email}")
        
        # Always return success (security best practice - don't reveal if email exists)
        return {"message": "Nếu email tồn tại, chúng tôi đã gửi link đặt lại mật khẩu."}
        
    except Exception as e:
        logger.error(f"Forgot password error: {str(e)}")
        # Still return success to avoid leaking information
        return {"message": "Nếu email tồn tại, chúng tôi đã gửi link đặt lại mật khẩu."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict:
    """
    Reset password using token from email.
    
    Parameters
    ----------
    data : ResetPasswordRequest
        Contains reset token and new password
    db : AsyncSession
        Database session
        
    Returns
    -------
    dict
        Success message
        
    Raises
    ------
    HTTPException 400
        If token is invalid or expired
    """
    try:
        # Verify token
        email_service = get_email_service()
        payload = email_service.verify_password_reset_token(data.token)
        
        if not payload:
            raise HTTPException(status_code=400, detail="Token không hợp lệ hoặc đã hết hạn")
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id or not email:
            raise HTTPException(status_code=400, detail="Token không hợp lệ")
        
        # Verify user still exists and matches
        user = await crud_users.get(db=db, id=user_id, is_deleted=False)
        if not user or user["email"] != email:
            raise HTTPException(status_code=400, detail="Token không hợp lệ")
        
        # Validate password (min 8 characters)
        if len(data.new_password) < 8:
            raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 8 ký tự")
        
        # Update password
        from datetime import datetime, timezone
        hashed_password = get_password_hash(data.new_password)
        
        await crud_users.update(
            db=db,
            object={
                "hashed_password": hashed_password,
                "updated_at": datetime.now(timezone.utc),
            },
            id=user_id,
        )
        
        logger.info(f"Password reset successful for user {user_id}")
        
        return {"message": "Đặt lại mật khẩu thành công! Vui lòng đăng nhập với mật khẩu mới."}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        raise HTTPException(status_code=500, detail="Đặt lại mật khẩu thất bại")

