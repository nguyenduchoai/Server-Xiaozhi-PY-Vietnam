"""
CRUD operations for UserConnection (Integrations).
"""

from typing import Optional, Sequence
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user_connection import UserConnection


async def get_connections(
    db: AsyncSession,
    user_id: str,
    connection_type: Optional[str] = None,
) -> Sequence[UserConnection]:
    """Get all connections for a user, optionally filtered by type."""
    stmt = select(UserConnection).where(UserConnection.user_id == user_id)
    if connection_type:
        stmt = stmt.where(UserConnection.type == connection_type)
    stmt = stmt.order_by(UserConnection.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_connection(
    db: AsyncSession,
    connection_id: str,
    user_id: str,
) -> Optional[UserConnection]:
    """Get a specific connection by ID, ensuring ownership."""
    stmt = select(UserConnection).where(
        and_(
            UserConnection.id == connection_id,
            UserConnection.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_connection(
    db: AsyncSession,
    user_id: str,
    type: str,
    name: str,
    config: dict,
    enabled: bool = True,
) -> UserConnection:
    """Create a new connection."""
    conn = UserConnection(
        user_id=user_id,
        type=type,
        name=name,
        config=config,
        enabled=enabled,
        status="disconnected",
    )
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return conn


async def update_connection(
    db: AsyncSession,
    connection: UserConnection,
    **kwargs,
) -> UserConnection:
    """Update connection fields."""
    for key, value in kwargs.items():
        if hasattr(connection, key) and value is not None:
            setattr(connection, key, value)
    await db.commit()
    await db.refresh(connection)
    return connection


async def delete_connection(
    db: AsyncSession,
    connection: UserConnection,
) -> bool:
    """Delete a connection."""
    await db.delete(connection)
    await db.commit()
    return True


async def get_connections_by_ids(
    db: AsyncSession,
    connection_ids: list[str],
    user_id: str,
) -> Sequence[UserConnection]:
    """Get multiple connections by IDs (for agent reference lookups)."""
    if not connection_ids:
        return []
    stmt = select(UserConnection).where(
        and_(
            UserConnection.id.in_(connection_ids),
            UserConnection.user_id == user_id,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()
