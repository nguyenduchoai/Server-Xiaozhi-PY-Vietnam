"""CRUD operations for Board Type and Screen Type."""

from fastcrud import FastCRUD

from ..models.board_type import BoardType, ScreenType
from ..schemas.board_type import (
    BoardTypeCreate,
    BoardTypeUpdate,
    ScreenTypeCreate,
    ScreenTypeUpdate,
)

crud_board_type = FastCRUD[BoardType, BoardTypeCreate, BoardTypeUpdate, BoardTypeUpdate, None, None](
    BoardType
)

crud_screen_type = FastCRUD[ScreenType, ScreenTypeCreate, ScreenTypeUpdate, ScreenTypeUpdate, None, None](
    ScreenType
)
