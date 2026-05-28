from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass

from ..config import settings


class Base(DeclarativeBase, MappedAsDataclass):
    pass


DATABASE_URI = settings.POSTGRES_URI 
DATABASE_PREFIX = settings.POSTGRES_ASYNC_PREFIX
DATABASE_URL = f"{DATABASE_PREFIX}{DATABASE_URI}"


async_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,             # Increased: support more concurrent connections
    max_overflow=20,          # Increased: handle burst traffic
    pool_recycle=1800,        # Recycle connections every 30 min (prevent stale)
    pool_pre_ping=True,       # Verify connection is alive before using
    pool_timeout=30,          # Increased: avoid timeout under load
    pool_use_lifo=True,       # Use LIFO for better connection reuse
)

local_session = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)


async def async_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with local_session() as db:
        yield db


from contextlib import asynccontextmanager

@asynccontextmanager
async def async_get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for getting a database session.
    Use this when outside of FastAPI route handlers.
    
    Example:
        async with async_get_db_session() as db:
            result = await some_crud_operation(db, ...)
    """
    async with local_session() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
