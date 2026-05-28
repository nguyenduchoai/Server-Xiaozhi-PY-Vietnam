"""
CRUD operations for UserTool model.
"""

from fastcrud import FastCRUD

from ..models.user_tool import UserTool
from ..schemas.user_tool import (
    UserToolCreateInternal,
    UserToolUpdate,
    UserToolRead,
)


class UserToolDelete:
    """Schema for soft delete."""
    is_deleted: bool = True


CRUDUserTool = FastCRUD[
    UserTool,
    UserToolCreateInternal,
    UserToolUpdate,
    UserToolUpdate,  # UpdateInternal same as Update
    UserToolDelete,
    UserToolRead,
]
crud_user_tool = CRUDUserTool(UserTool)
