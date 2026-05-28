"""
Admin API Endpoints

Handles admin operations for subscription management.
Requires superuser permissions.
"""

from typing import Annotated, Any
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update

from app.core.db.database import async_get_db
from app.api.dependencies import get_current_user
from app.crud import crud_users, crud_subscription_payment
from app.models.user import User, UserRole
from app.models.subscription_payment import PaymentStatus
from app.models.user_subscription import UserSubscription, SubscriptionStatus, SubscriptionBillingCycle
from app.schemas.user import UserRead, UserUpdate, UserCreateAdmin
from app.schemas.subscription_payment import SubscriptionPaymentRead, SubscriptionPaymentApprove
from app.schemas.base import PaginatedResponse, SuccessResponse
from app.core.logger import get_logger
from app.core.security import get_password_hash

router = APIRouter(prefix="/admin", tags=["admin"])
logger = get_logger(__name__)


def require_superuser(current_user: dict) -> dict:
    """Dependency to check if user is superuser or admin"""
    is_superuser = current_user.get("is_superuser")
    role = current_user.get("role")
    
    # Allow if is_superuser OR role is admin/super_admin
    if is_superuser:
        return current_user
        
    if role in [UserRole.ADMIN, UserRole.SUPER_ADMIN, "admin", "super_admin"]:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )
    return current_user


@router.get("/users", response_model=PaginatedResponse[UserRead])
async def list_users(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by name or email"),
    is_superuser: bool | None = Query(default=None, description="Filter by superuser status"),
    include_deleted: bool = Query(default=True, description="Include soft-deleted users"),
) -> dict[str, Any]:
    """
    List all users (admin only).
    
    Supports pagination and search.
    By default includes deleted users (for admin management).
    """
    require_superuser(current_user)
    
    try:
        filters = {}
        if is_superuser is not None:
            filters["is_superuser"] = is_superuser
        
        # Build base conditions
        conditions = []
        if not include_deleted:
            conditions.append(User.is_deleted == False)
        
        # If search provided, use raw query
        if search:
            search_condition = or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
            )
            conditions.append(search_condition)
            
            # Build query with all conditions
            if conditions:
                stmt = select(User).where(*conditions).offset((page - 1) * page_size).limit(page_size)
                count_stmt = select(func.count(User.id)).where(*conditions)
            else:
                stmt = select(User).offset((page - 1) * page_size).limit(page_size)
                count_stmt = select(func.count(User.id))
            
            result = await db.execute(stmt)
            users = result.scalars().all()
            
            count_result = await db.execute(count_stmt)
            total = count_result.scalar_one()
            
            users_data = {"data": users, "total_count": total}
        else:
            users_data = await crud_users.get_multi(
                db=db,
                offset=(page - 1) * page_size,
                limit=page_size,
                schema_to_select=UserRead,
                **filters,
            )
        
        total = users_data.get("total_count", 0)
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            success=True,
            message="Success",
            data=users_data["data"],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/users", response_model=SuccessResponse[UserRead], status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateAdmin,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[UserRead]:
    """
    Create a new user (admin only).
    
    Creates user with hashed password. User will have FREE plan by default.
    """
    require_superuser(current_user)
    
    try:
        # Normalize email to lowercase
        normalized_email = user_data.email.lower().strip()
        
        # Check if email already exists (case-insensitive)
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create user (id is auto-generated by SQLAlchemy via uuid7)
        new_user = User(
            name=user_data.name,
            email=normalized_email,  # Store as lowercase
            hashed_password=get_password_hash(user_data.password),
            role=user_data.role,
            is_superuser=(user_data.role.value == "super_admin"),  # Auto-set based on role
            is_deleted=False,
            created_at=datetime.now(timezone.utc),
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"Admin {current_user.get('id')} created user {new_user.id} ({new_user.email})")
        
        return SuccessResponse(
            success=True,
            message="User created successfully",
            data=UserRead.model_validate(new_user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/payments", response_model=PaginatedResponse[SubscriptionPaymentRead])
async def list_payments(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
) -> dict[str, Any]:
    """
    List all payment requests (admin only).
    
    Use status=PENDING to see requests awaiting approval.
    """
    require_superuser(current_user)
    
    try:
        filters = {}
        if status_filter:
            filters["status"] = status_filter
        
        payments_data = await crud_subscription_payment.get_multi(
            db=db,
            offset=(page - 1) * page_size,
            limit=page_size,
            schema_to_select=SubscriptionPaymentRead,
            **filters,
        )
        
        total = payments_data.get("total_count", 0)
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            success=True,
            message="Success",
            data=payments_data["data"],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
    except Exception as e:
        logger.error(f"Error listing payments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/payments/{payment_id}/approve", response_model=SuccessResponse[dict])
async def approve_payment(
    payment_id: str,
    approval_data: SubscriptionPaymentApprove,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """
    Approve or reject a payment request (admin only).
    
    If approved, creates/extends user subscription.
    """
    require_superuser(current_user)
    
    try:
        admin_id = current_user.get("sub") or current_user.get("id")
        
        # Get payment
        payment = await crud_subscription_payment.get(db=db, id=payment_id)
        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment request not found"
            )
        
        if payment.status != PaymentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment already {payment.status.value}"
            )
        
        # Update payment status
        payment.status = approval_data.status
        payment.reviewed_by_admin_id = admin_id
        payment.reviewed_at = datetime.now(timezone.utc)
        payment.admin_note = approval_data.admin_note
        
        # Captured for the post-commit notification email so we can tell the
        # user when their access expires. Only meaningful when approved.
        new_expires_at: datetime | None = None

        # If approved, create/update subscription
        if approval_data.status == PaymentStatus.APPROVED:
            # Check if user has existing subscription
            stmt = (
                select(UserSubscription)
                .where(UserSubscription.user_id == payment.user_id)
                .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
                .order_by(UserSubscription.created_at.desc())
            )
            result = await db.execute(stmt)
            existing_sub = result.scalar_one_or_none()

            # Determine subscription duration
            if payment.billing_cycle == "yearly":
                duration_days = 365
            else:  # monthly
                duration_days = 30

            now = datetime.now(timezone.utc)

            if existing_sub:
                # Guardrail: refuse to approve a payment for a plan that
                # differs from the user's currently-active plan. Silently
                # overwriting plan_id while extending expires_at corrupts
                # billing state (user pays for plan A, ends up on plan B
                # with extra days, or vice versa). Force admin to handle
                # upgrade/downgrade explicitly (e.g. cancel current sub
                # via support flow, or build proration logic later).
                if existing_sub.plan_id != payment.plan_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"User đang có gói khác đang active "
                            f"(plan_id={existing_sub.plan_id}). "
                            f"Không thể tự động duyệt thanh toán cho "
                            f"plan_id={payment.plan_id}. "
                            f"Hãy huỷ/kết thúc gói hiện tại trước, "
                            f"hoặc liên hệ kỹ thuật để xử lý nâng/hạ cấp."
                        ),
                    )

                # Same plan: extend existing subscription
                if existing_sub.expires_at and existing_sub.expires_at > now:
                    # Extend from current expiry
                    new_expiry = existing_sub.expires_at + timedelta(days=duration_days)
                else:
                    # Start from now
                    new_expiry = now + timedelta(days=duration_days)

                existing_sub.expires_at = new_expiry
                existing_sub.billing_cycle = SubscriptionBillingCycle.YEARLY if payment.billing_cycle == "yearly" else SubscriptionBillingCycle.MONTHLY
                existing_sub.updated_at = now
                new_expires_at = new_expiry

                logger.info(f"Extended subscription {existing_sub.id} for user {payment.user_id} until {new_expiry}")
            else:
                # Create new subscription
                sub_expires = now + timedelta(days=duration_days)
                new_sub = UserSubscription(
                    id=str(uuid4()),
                    user_id=payment.user_id,
                    plan_id=payment.plan_id,
                    status=SubscriptionStatus.ACTIVE,
                    billing_cycle=SubscriptionBillingCycle.YEARLY if payment.billing_cycle == "yearly" else SubscriptionBillingCycle.MONTHLY,
                    started_at=now,
                    expires_at=sub_expires,
                    current_period_start=now,
                    current_period_end=sub_expires,
                )
                db.add(new_sub)
                new_expires_at = sub_expires

                logger.info(f"Created new subscription for user {payment.user_id}, plan {payment.plan_id}")

        await db.commit()
        await db.refresh(payment)

        # Best-effort notification email. Failures here MUST NOT bubble out:
        # the admin already approved/rejected the payment, the DB is committed,
        # and the response should still report success — even if SMTP is down.
        try:
            from app.services.email_service import get_email_service
            from app.crud import crud_subscription_plan as _crud_plan

            email_svc = get_email_service()
            if email_svc.enabled:
                user_row = await db.get(User, payment.user_id)
                # Skip shadow users — their email is a synthetic
                # MAC@device.xiaozhi.vn address that doesn't actually deliver.
                if user_row and user_row.email and not user_row.is_shadow:
                    plan_row = await _crud_plan.get(db=db, id=payment.plan_id)
                    plan_name = (
                        plan_row.get("display_name") if isinstance(plan_row, dict)
                        else getattr(plan_row, "display_name", None)
                    ) or f"Plan #{payment.plan_id}"
                    user_name = user_row.name or user_row.email

                    if approval_data.status == PaymentStatus.APPROVED:
                        email_svc.send_payment_approved_email(
                            to_email=user_row.email,
                            user_name=user_name,
                            plan_name=plan_name,
                            amount=payment.amount,
                            billing_cycle=payment.billing_cycle,
                            expires_at=new_expires_at,
                        )
                    elif approval_data.status == PaymentStatus.REJECTED:
                        email_svc.send_payment_rejected_email(
                            to_email=user_row.email,
                            user_name=user_name,
                            plan_name=plan_name,
                            amount=payment.amount,
                            reason=approval_data.admin_note,
                        )
        except Exception as email_err:  # noqa: BLE001
            logger.warning(
                f"Failed to send payment {approval_data.status.value} email "
                f"for payment {payment.id}: {email_err}"
            )

        return SuccessResponse(
            success=True,
            message=f"Payment {approval_data.status.value} successfully",
            data={
                "payment_id": payment.id,
                "status": payment.status.value,
                "reviewed_at": payment.reviewed_at.isoformat() if payment.reviewed_at else None,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving payment: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/users/{user_id}/subscription", response_model=SuccessResponse[dict])
async def assign_subscription_to_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    plan_id: int = Query(..., description="Plan ID to assign"),
    billing_cycle: str = Query(default="monthly", pattern="^(monthly|yearly|lifetime)$"),
    duration_days: int = Query(default=30, ge=1, le=3650),
) -> SuccessResponse[dict]:
    """
    Manually assign a subscription plan to a user (admin only).
    
    Use this for special cases, promotions, or manual upgrades.
    """
    require_superuser(current_user)
    
    try:
        # Validate user exists
        user = await crud_users.get(db=db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Validate plan exists
        from app.crud import crud_subscription_plan
        plan = await crud_subscription_plan.get(db=db, id=plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription plan not found"
            )
        
        # Cancel existing active subscriptions
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
        )
        result = await db.execute(stmt)
        existing_subs = result.scalars().all()
        
        for sub in existing_subs:
            sub.status = SubscriptionStatus.CANCELLED
            sub.cancelled_at = datetime.now(timezone.utc)
        
        # Create new subscription
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=duration_days) if billing_cycle != "lifetime" else None
        
        new_sub = UserSubscription(
            id=str(uuid4()),
            user_id=user_id,
            plan_id=plan_id,
            status=SubscriptionStatus.ACTIVE,
            billing_cycle=SubscriptionBillingCycle[billing_cycle.upper()],
            started_at=now,
            expires_at=expires_at,
            current_period_start=now,
            current_period_end=expires_at,
            created_at=now,
        )
        
        db.add(new_sub)
        await db.commit()
        await db.refresh(new_sub)
        
        plan_name = plan.get("name") if isinstance(plan, dict) else plan.name
        logger.info(f"Admin {current_user.get('id')} assigned {plan_name} plan to user {user_id}")
        
        return SuccessResponse(
            success=True,
            message=f"Successfully assigned {plan_name} plan to user",
            data={
                "subscription_id": new_sub.id,
                "plan_name": plan_name,
                "expires_at": new_sub.expires_at.isoformat() if new_sub.expires_at else None,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning subscription: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/users/{user_id}", response_model=SuccessResponse[UserRead])
async def get_user_detail(
    user_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[UserRead]:
    """
    Get user details by ID (admin only).
    """
    require_superuser(current_user)
    
    try:
        user = await crud_users.get(db=db, id=user_id, schema_to_select=UserRead)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return SuccessResponse(
            success=True,
            message="Success",
            data=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/users/{user_id}", response_model=SuccessResponse[UserRead])
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[UserRead]:
    """
    Update user information (admin only).
    """
    require_superuser(current_user)
    
    try:
        # Check if user exists
        user = await crud_users.get(db=db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user - use correct signature
        # Sync is_superuser with role if role is being updated
        update_data = user_update.model_dump(exclude_unset=True)
        if "role" in update_data:
            if update_data["role"] == UserRole.SUPER_ADMIN:
                update_data["is_superuser"] = True
            else:
                update_data["is_superuser"] = False
            
            # Create a new update object or dict to pass to update
            # Since crud.update expects a Pydantic model or dict
            # We can pass the dict directly if the crud supports it
            
            # Alternatively, since user_update is a model, we can't easily modify it if it's frozen
            # But we can pass the dict to crud.update if implementation allow
        
        await crud_users.update(
            db=db,
            object=update_data,
            id=user_id
        )
        
        # Fetch updated user
        updated_user = await crud_users.get(
            db=db, 
            id=user_id, 
            schema_to_select=UserRead
        )
        
        logger.info(f"Admin {current_user.get('id')} updated user {user_id}")
        
        return SuccessResponse(
            success=True,
            message="User updated successfully",
            data=updated_user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/users/{user_id}", response_model=SuccessResponse[dict])
async def delete_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    permanent: bool = Query(default=False, description="Permanently delete user"),
) -> SuccessResponse[dict]:
    """
    Delete user (admin only).
    
    By default, performs soft delete (is_deleted=True).
    Use permanent=true to permanently delete user and all related data.
    """
    require_superuser(current_user)
    
    try:
        # Check if user exists
        user = await crud_users.get(db=db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prevent deleting yourself
        admin_id = current_user.get("sub") or current_user.get("id")
        # Handle case where IDs might be UUID objects or strings
        if str(user["id"] if isinstance(user, dict) else user.id) == str(admin_id):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        # Permission Check:
        # Admin cannot delete Super Admin or other Admin
        current_role = current_user.get("role")
        target_role = user["role"] if isinstance(user, dict) else user.role
        
        if current_role != UserRole.SUPER_ADMIN:
            if target_role == UserRole.SUPER_ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to delete Super Admin"
                )
            if target_role == UserRole.ADMIN:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admins cannot delete other Admins"
                )
        
        if permanent:
            # Permanently delete user
            await crud_users.delete(db=db, id=user_id)
            message = "User permanently deleted"
        else:
            # Soft delete
            logger.info(f"Attempting soft delete for user {user_id}")
            try:
                deleted_at = datetime.now(timezone.utc)
                stmt = update(User).where(User.id == user_id).values(
                    is_deleted=True,
                    deleted_at=deleted_at,
                    updated_at=deleted_at
                )
                result = await db.execute(stmt)
                await db.commit()
                logger.info(f"Soft delete executed. Rowcount: {result.rowcount}")
                message = "User soft deleted"
            except Exception as e:
                logger.error(f"Error soft deleting user: {e}")
                raise HTTPException(status_code=500, detail=f"Soft delete failed: {str(e)}")
        
        logger.info(f"Admin {admin_id} deleted user {user_id} (permanent={permanent})")
        
        return SuccessResponse(
            success=True,
            message=message,
            data={"user_id": user_id, "permanent": permanent}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/users/{user_id}/restore", response_model=SuccessResponse[UserRead])
async def restore_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[UserRead]:
    """
    Restore a soft-deleted user (admin only).
    """
    require_superuser(current_user)
    
    try:
        # Get user (even if deleted)
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not user.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not deleted"
            )
        
        # Restore user
        user.is_deleted = False
        user.deleted_at = None
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Admin {current_user.get('id')} restored user {user_id}")
        
        return SuccessResponse(
            success=True,
            message="User restored successfully",
            data=UserRead.model_validate(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring user: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/users/{user_id}/password")
async def admin_reset_user_password(
    user_id: str,
    new_password: str = Query(..., min_length=8, description="New password (min 8 characters)"),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(async_get_db),
) -> dict:
    """
    Admin/SuperAdmin reset user password.
    
    Allows admins to set a new password for any user.
    The admin can then share this password with the user.
    
    Parameters
    ----------
    user_id : str
        User ID to reset password for
    new_password : str
        New password (minimum 8 characters)
    current_user : dict
        Current authenticated admin user
    db : AsyncSession
        Database session
        
    Returns
    -------
    dict
        Success message with masked password hint
        
    Raises
    ------
    HTTPException 403
        If user is not admin or trying to change superadmin password without being superadmin
    HTTPException 404
        If user not found
    """
    try:
        # Verify admin permissions
        require_superuser(current_user)
        admin_id = current_user.get("id")
        admin_role = current_user.get("role", "")
        is_superuser = current_user.get("is_superuser", False)
        
        # Check target user exists
        user = await crud_users.get(db=db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        target_role = user.get("role", "user")
        target_is_superuser = user.get("is_superuser", False)
        
        # Permission checks:
        # - Regular Admin cannot change SuperAdmin password
        # - Only SuperAdmin can change other SuperAdmin's password
        if target_is_superuser or target_role in ["super_admin", UserRole.SUPER_ADMIN]:
            if not is_superuser and admin_role not in ["super_admin", UserRole.SUPER_ADMIN]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only SuperAdmin can change another SuperAdmin's password"
                )
        
        # Hash and update password
        hashed_password = get_password_hash(new_password)
        
        stmt = update(User).where(User.id == user_id).values(
            hashed_password=hashed_password,
            updated_at=datetime.now(timezone.utc)
        )
        await db.execute(stmt)
        await db.commit()
        
        # Log action
        logger.info(f"Admin {admin_id} reset password for user {user_id} ({user.get('email')})")
        
        # Return success with masked password hint
        password_hint = new_password[:2] + "*" * (len(new_password) - 4) + new_password[-2:] if len(new_password) > 4 else "****"
        
        return {
            "message": f"Đã đặt lại mật khẩu cho {user.get('name')} ({user.get('email')})",
            "password_hint": password_hint,
            "note": "Vui lòng gửi mật khẩu mới cho người dùng qua email hoặc tin nhắn."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting user password: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# ============= SMTP Settings =============
from pydantic import BaseModel
import os

class SMTPSettingsSchema(BaseModel):
    """Schema for SMTP settings"""
    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""  # Will be masked when reading
    from_email: str = ""
    from_name: str = "Xiaozhi AI"
    use_tls: bool = True
    enabled: bool = False


@router.get("/smtp-settings")
async def get_smtp_settings(
    current_user: Annotated[dict, Depends(get_current_user)] = None,
) -> dict:
    """
    Get current SMTP settings.
    Password is masked for security.
    """
    require_superuser(current_user)
    
    # Read from environment variables
    password = os.getenv("SMTP_PASSWORD", "")
    masked_password = "*" * min(len(password), 8) if password else ""
    
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": masked_password,  # Masked
        "from_email": os.getenv("SMTP_FROM_EMAIL", ""),
        "from_name": os.getenv("SMTP_FROM_NAME", "Xiaozhi AI"),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        "enabled": os.getenv("SMTP_ENABLED", "false").lower() == "true",
    }


@router.post("/smtp-settings")
async def update_smtp_settings(
    settings: SMTPSettingsSchema,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
) -> dict:
    """
    Update SMTP settings.
    Settings are saved to .env file.
    
    Note: Requires backend restart to take effect.
    """
    require_superuser(current_user)
    
    try:
        # Path to .env file
        env_path = "/app/.env"
        if not os.path.exists(env_path):
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
        
        # Read current .env content
        env_content = ""
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                env_content = f.read()
        
        # Update or add SMTP settings
        smtp_vars = {
            "SMTP_HOST": settings.host,
            "SMTP_PORT": str(settings.port),
            "SMTP_USERNAME": settings.username,
            "SMTP_FROM_EMAIL": settings.from_email,
            "SMTP_FROM_NAME": settings.from_name,
            "SMTP_USE_TLS": "true" if settings.use_tls else "false",
            "SMTP_ENABLED": "true" if settings.enabled else "false",
        }
        
        # Only update password if not masked
        if settings.password and not settings.password.startswith("*"):
            smtp_vars["SMTP_PASSWORD"] = settings.password
        
        # Process each line
        lines = env_content.split("\n")
        updated_vars = set()
        new_lines = []
        
        for line in lines:
            # Skip empty lines at the end
            stripped = line.strip()
            if not stripped:
                new_lines.append(line)
                continue
                
            # Check if this line defines an SMTP variable
            var_updated = False
            for var_name, var_value in smtp_vars.items():
                if stripped.startswith(f"{var_name}="):
                    new_lines.append(f'{var_name}="{var_value}"')
                    updated_vars.add(var_name)
                    var_updated = True
                    break
            
            if not var_updated:
                new_lines.append(line)
        
        # Add any missing SMTP variables
        for var_name, var_value in smtp_vars.items():
            if var_name not in updated_vars:
                new_lines.append(f'{var_name}="{var_value}"')
        
        # Write back to .env
        with open(env_path, "w") as f:
            f.write("\n".join(new_lines))
        
        # Update runtime environment (for immediate effect without restart)
        for var_name, var_value in smtp_vars.items():
            os.environ[var_name] = var_value
        
        # Re-initialize email service
        from app.services.email_service import init_email_service
        init_email_service(
            host=settings.host,
            port=settings.port,
            username=settings.username,
            password=settings.password if not settings.password.startswith("*") else os.getenv("SMTP_PASSWORD", ""),
            from_email=settings.from_email,
            from_name=settings.from_name,
            use_tls=settings.use_tls,
            enabled=settings.enabled,
        )
        
        logger.info(f"SMTP settings updated by admin {current_user.get('id')}")
        
        return {
            "message": "Đã cập nhật cấu hình SMTP thành công!",
            "note": "Cấu hình đã được áp dụng ngay lập tức.",
        }
        
    except Exception as e:
        logger.error(f"Error updating SMTP settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Không thể cập nhật cấu hình SMTP: {str(e)}"
        )


@router.post("/smtp-settings/test")
async def test_smtp_settings(
    test_email: str = Query(..., description="Email address to send test email to"),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
) -> dict:
    """
    Send a test email to verify SMTP settings.
    """
    require_superuser(current_user)
    
    try:
        from app.services.email_service import get_email_service
        
        email_service = get_email_service()
        
        if not email_service.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email service is disabled. Enable it first."
            )
        
        # Send test email
        success = email_service.send_email(
            to_email=test_email,
            subject="[Test] Kiểm tra cấu hình SMTP",
            html_content="""
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h1 style="color: #667eea;">✅ SMTP Hoạt Động!</h1>
                <p>Cấu hình SMTP của bạn đã hoạt động đúng.</p>
                <p>Email này được gửi từ hệ thống để kiểm tra.</p>
                <hr>
                <p style="color: #888; font-size: 12px;">Xiaozhi AI Platform</p>
            </div>
            """,
            text_content="SMTP đã hoạt động! Cấu hình của bạn đúng."
        )
        
        if success:
            return {"message": f"Email test đã được gửi đến {test_email}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Không thể gửi email. Kiểm tra lại cấu hình SMTP."
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SMTP test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test SMTP thất bại: {str(e)}"
        )


# ============= Admin Device Management =============

from app.models.device import Device
from pydantic import BaseModel as PydanticBaseModel


class AdminDeviceRead(PydanticBaseModel):
    """Schema for admin device list item"""
    id: str
    mac_address: str
    device_name: str | None
    board: str | None
    firmware_version: str | None
    status: str | None
    user_id: str
    user_email: str | None = None
    user_name: str | None = None
    last_connected_at: datetime | None
    created_at: datetime


class TransferDeviceRequest(PydanticBaseModel):
    """Request to transfer device to another user"""
    target_user_id: str


@router.get("/devices", response_model=PaginatedResponse[AdminDeviceRead])
async def list_all_devices(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, description="Search by MAC, name, or user email"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status"),
) -> dict[str, Any]:
    """
    List all devices in the system (SuperAdmin only).
    
    Includes user information for each device.
    """
    require_superuser(current_user)
    
    try:
        # Build query with user join
        
        stmt = (
            select(
                Device,
                User.email.label("user_email"),
                User.name.label("user_name")
            )
            .join(User, Device.user_id == User.id, isouter=True)
        )
        
        # Apply filters
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Device.mac_address.ilike(search_pattern),
                    Device.device_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.name.ilike(search_pattern),
                )
            )
        
        if status_filter:
            stmt = stmt.where(Device.status == status_filter)
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()
        
        # Apply pagination
        stmt = stmt.order_by(Device.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(stmt)
        rows = result.all()
        
        # Build response
        devices = []
        for row in rows:
            device = row[0]  # Device object
            devices.append(AdminDeviceRead(
                id=device.id,
                mac_address=device.mac_address,
                device_name=device.device_name,
                board=device.board,
                firmware_version=device.firmware_version,
                status=device.status,
                user_id=device.user_id,
                user_email=row.user_email,
                user_name=row.user_name,
                last_connected_at=device.last_connected_at,
                created_at=device.created_at,
            ))
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResponse(
            success=True,
            message="Success",
            data=devices,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing all devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/devices/{device_id}", response_model=SuccessResponse[dict])
async def delete_device(
    device_id: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """
    Delete a device (SuperAdmin only).
    
    Permanently removes device from the system.
    """
    require_superuser(current_user)
    
    try:
        # Get device
        stmt = select(Device).where(Device.id == device_id)
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thiết bị không tồn tại"
            )
        
        mac_address = device.mac_address
        await db.delete(device)
        await db.commit()
        
        admin_id = current_user.get("sub") or current_user.get("id")
        logger.info(f"Admin {admin_id} deleted device {device_id} (MAC: {mac_address})")
        
        return SuccessResponse(
            success=True,
            message=f"Đã xóa thiết bị {mac_address}",
            data={"device_id": device_id, "mac_address": mac_address}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/devices/{device_id}/transfer", response_model=SuccessResponse[dict])
async def transfer_device(
    device_id: str,
    transfer_data: TransferDeviceRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
) -> SuccessResponse[dict]:
    """
    Transfer device to another user (SuperAdmin only).
    
    Changes the owner of a device.
    """
    require_superuser(current_user)
    
    try:
        # Get device
        stmt = select(Device).where(Device.id == device_id)
        result = await db.execute(stmt)
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thiết bị không tồn tại"
            )
        
        # Validate target user
        target_user = await crud_users.get(db=db, id=transfer_data.target_user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Người dùng đích không tồn tại"
            )
        
        # Check if target user already has this MAC address (unique constraint)
        existing_stmt = select(Device).where(
            Device.user_id == transfer_data.target_user_id,
            Device.mac_address == device.mac_address,
            Device.id != device_id
        )
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Người dùng đích đã có thiết bị với MAC address này"
            )
        
        old_user_id = device.user_id
        device.user_id = transfer_data.target_user_id
        device.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(device)

        target_name = target_user.get("name") if isinstance(target_user, dict) else target_user.name
        target_email = target_user.get("email") if isinstance(target_user, dict) else target_user.email
        target_is_shadow = (
            target_user.get("is_shadow") if isinstance(target_user, dict)
            else getattr(target_user, "is_shadow", False)
        )

        admin_id = current_user.get("sub") or current_user.get("id")
        logger.info(f"Admin {admin_id} transferred device {device_id} from {old_user_id} to {transfer_data.target_user_id}")

        # Best-effort: notify the new owner. Skip shadow users (synthetic
        # MAC@device.xiaozhi.vn email never delivers). Failures only log.
        try:
            from app.services.email_service import get_email_service
            email_svc = get_email_service()
            if email_svc.enabled and target_email and not target_is_shadow:
                # Look up old owner's email for the "from" line — purely
                # informational; if missing we omit it.
                from_email: str | None = None
                try:
                    old_owner = await crud_users.get(db=db, id=old_user_id)
                    if old_owner:
                        from_email = (
                            old_owner.get("email") if isinstance(old_owner, dict)
                            else getattr(old_owner, "email", None)
                        )
                except Exception:
                    from_email = None

                email_svc.send_device_transferred_email(
                    to_email=target_email,
                    user_name=target_name or target_email,
                    device_name=device.device_name or device.mac_address,
                    mac_address=device.mac_address,
                    from_user_email=from_email,
                )
        except Exception as email_err:  # noqa: BLE001
            logger.warning(
                f"Failed to send device-transferred email for {device_id}: {email_err}"
            )
        
        return SuccessResponse(
            success=True,
            message=f"Đã chuyển thiết bị {device.mac_address} cho {target_name} ({target_email})",
            data={
                "device_id": device_id,
                "mac_address": device.mac_address,
                "new_user_id": transfer_data.target_user_id,
                "new_user_name": target_name,
                "new_user_email": target_email,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error transferring device: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
