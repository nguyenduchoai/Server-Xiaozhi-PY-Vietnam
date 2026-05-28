"""
Pytest Configuration & Fixtures

Provides common fixtures for API testing including:
- Async client for FastAPI
- Database session
- Test user authentication
"""

import asyncio
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.db.database import Base, async_get_db


# Test database URL (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing FastAPI app."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[async_get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create authenticated user and return auth headers."""
    from app.crud.crud_users import crud_users
    from app.schemas.user import UserCreateInternal
    from app.core.security import create_access_token
    
    # Create test user
    test_user = UserCreateInternal(
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.rLe.s0lFYC5.eO",  # "password123"
        is_verified=True,
        is_superuser=False,
    )
    
    user = await crud_users.create(db=db_session, object=test_user)
    
    # Generate token
    access_token = await create_access_token(
        data={"sub": user.id},
    )
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture(scope="function")
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Create admin user and return auth headers."""
    from app.crud.crud_users import crud_users
    from app.schemas.user import UserCreateInternal
    from app.core.security import create_access_token
    from app.models.user import UserRole
    
    # Create admin user
    admin_user = UserCreateInternal(
        email="admin@example.com",
        username="adminuser",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.rLe.s0lFYC5.eO",
        is_verified=True,
        is_superuser=True,
        role=UserRole.SUPER_ADMIN,
    )
    
    user = await crud_users.create(db=db_session, object=admin_user)
    
    access_token = await create_access_token(
        data={"sub": user.id},
    )
    
    return {"Authorization": f"Bearer {access_token}"}


# Test data fixtures
@pytest.fixture
def test_user_data() -> dict:
    """Sample user registration data."""
    return {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "SecurePass123!",
    }


@pytest.fixture
def test_agent_data() -> dict:
    """Sample agent creation data."""
    return {
        "name": "Test Agent",
        "description": "A test AI agent",
        "system_prompt": "You are a helpful assistant.",
    }
