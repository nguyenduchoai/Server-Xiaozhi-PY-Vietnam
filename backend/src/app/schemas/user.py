from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..core.schemas import PersistentDeletion, TimestampSchema
from ..models.user import UserRole


def _validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(char.islower() for char in value):
        raise ValueError("Password must include a lowercase letter")
    if not any(char.isupper() for char in value):
        raise ValueError("Password must include an uppercase letter")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must include a number")
    if not any(not char.isalnum() for char in value):
        raise ValueError("Password must include a special character")
    return value


class UserBase(BaseModel):
    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]


class User(TimestampSchema, UserBase, PersistentDeletion):
    id: str
    profile_image_base64: Annotated[str | None, Field(default=None)]
    hashed_password: str
    is_superuser: bool = False


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str

    name: Annotated[str, Field(min_length=2, max_length=30, examples=["User Userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    profile_image_base64: str | None = None
    is_superuser: bool = False
    role: UserRole = UserRole.USER
    timezone: str | None = None
    created_at: datetime | None = None
    is_deleted: bool = False


class UserCreate(UserBase):
    """Public-registration schema.

    DOES NOT include `role`. Even though UserCreateInternal currently
    drops unknown fields (Pydantic v2 default `extra="ignore"`), keeping
    `role` out of the public registration schema enforces "users can
    only self-register as USER" at the API contract level — robust
    against future refactors that might inadvertently propagate fields.
    For admin-driven creation use UserCreateAdmin instead.
    """

    model_config = ConfigDict(extra="forbid")

    password: Annotated[
        str,
        Field(
            min_length=8,
            examples=["Str1ngst!"],
            description="Must include uppercase, lowercase, number, and special character",
        ),
    ]
    invitation_token: str | None = Field(None, description="Friend invitation token if registering via invite link")

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)


class UserCreateAdmin(UserCreate):
    """Admin-only creation schema — adds `role` so admins can create
    users with elevated privileges. Used by POST /admin/users."""

    role: UserRole = UserRole.USER


class UserCreateInternal(UserBase):
    hashed_password: str


class UserSelfUpdate(BaseModel):
    """Fields a user is allowed to change about themselves (PATCH /user/me).

    DOES NOT include `role` — only an admin can change another user's role
    via the admin endpoint. If `role` were present here, any authenticated
    user could PATCH /user/me with {"role": "super_admin"} and escalate
    privileges.
    """

    model_config = ConfigDict(extra="forbid")

    name: Annotated[
        str | None,
        Field(min_length=2, max_length=30, examples=["User Userberg"], default=None),
    ]
    email: Annotated[EmailStr | None, Field(examples=["user.userberg@example.com"], default=None)]
    profile_image_base64: Annotated[
        str | None,
        Field(
            description="Base64 encoded image data (e.g., 'data:image/png;base64,iVBOR...')",
            default=None,
        ),
    ]
    timezone: Annotated[
        str | None,
        Field(
            min_length=1,
            max_length=50,
            examples=["Asia/Ho_Chi_Minh", "UTC", "America/New_York"],
            default=None,
        ),
    ]


class UserUpdate(UserSelfUpdate):
    """Admin-only update schema — adds `role` so admins can change roles."""

    role: UserRole | None = None


class UserUpdateInternal(UserUpdate):
    updated_at: datetime


class UserDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime


class UserRestoreDeleted(BaseModel):
    is_deleted: bool


class PasswordChange(BaseModel):
    """Schema for changing user password."""

    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, Field(min_length=1, examples=["OldPassword123!"])]
    new_password: Annotated[
        str,
        Field(
            min_length=8,
            examples=["NewPassword123!"],
            description="Must be at least 8 characters with uppercase, lowercase, number, and special character",
        ),
    ]

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        return _validate_password_strength(value)
