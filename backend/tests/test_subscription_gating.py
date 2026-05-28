"""
Integration Tests for Subscription Gating

Tests that:
1. FREE users are blocked from PRO features (agent limit, device limit, etc.)
2. PRO users can access PRO features within their limits
3. SuperAdmins bypass all gating
4. Token quota enforcement works correctly
5. Device feature toggles respect plan settings
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.quota_service import QuotaService
from app.models.user import User, UserRole
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription, SubscriptionStatus
from app.models.agent import Agent
from app.models.device import Device


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def free_plan(db_session: AsyncSession) -> SubscriptionPlan:
    """Create a FREE subscription plan."""
    plan = SubscriptionPlan(
        name="free",
        display_name="Free",
        price=0,
        billing_period="monthly",
        max_agents=2,
        max_devices=1,
        max_mcps=1,
        max_templates=3,
        max_tools=5,
        max_monthly_tokens=50_000,
        max_tts_minutes_monthly=10,
        max_knowledge_base_size_mb=50,
        enable_api_access=False,
        enable_webhook=False,
        enable_custom_branding=False,
        enable_priority_support=False,
        allow_custom_providers=False,
        allowed_provider_types=["edge_tts", "valtec"],
        allowed_provider_categories=["TTS"],
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def pro_plan(db_session: AsyncSession) -> SubscriptionPlan:
    """Create a PRO subscription plan."""
    plan = SubscriptionPlan(
        name="pro",
        display_name="Pro",
        price=199_000,
        billing_period="monthly",
        max_agents=10,
        max_devices=5,
        max_mcps=10,
        max_templates=20,
        max_tools=50,
        max_monthly_tokens=1_000_000,
        max_tts_minutes_monthly=120,
        max_knowledge_base_size_mb=500,
        enable_api_access=True,
        enable_webhook=True,
        enable_custom_branding=False,
        enable_priority_support=False,
        allow_custom_providers=True,
        is_active=True,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return plan


@pytest_asyncio.fixture
async def free_user(db_session: AsyncSession, free_plan: SubscriptionPlan) -> User:
    """Create a user with FREE subscription."""
    from app.crud.crud_users import crud_users
    from app.schemas.user import UserCreateInternal

    user_data = UserCreateInternal(
        email="free@example.com",
        username="freeuser",
        hashed_password="$2b$12$dummy",
        is_verified=True,
        is_superuser=False,
    )
    user = await crud_users.create(db=db_session, object=user_data)

    sub = UserSubscription(
        user_id=user.id,
        plan_id=free_plan.id,
        status=SubscriptionStatus.ACTIVE,
        monthly_tokens_used=0,
        monthly_tts_minutes_used=0.0,
    )
    db_session.add(sub)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def pro_user(db_session: AsyncSession, pro_plan: SubscriptionPlan) -> User:
    """Create a user with PRO subscription."""
    from app.crud.crud_users import crud_users
    from app.schemas.user import UserCreateInternal

    user_data = UserCreateInternal(
        email="pro@example.com",
        username="prouser",
        hashed_password="$2b$12$dummy",
        is_verified=True,
        is_superuser=False,
    )
    user = await crud_users.create(db=db_session, object=user_data)

    sub = UserSubscription(
        user_id=user.id,
        plan_id=pro_plan.id,
        status=SubscriptionStatus.ACTIVE,
        monthly_tokens_used=0,
        monthly_tts_minutes_used=0.0,
    )
    db_session.add(sub)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def superadmin_user(db_session: AsyncSession, free_plan: SubscriptionPlan) -> User:
    """Create a superadmin — should bypass all gating even with free plan."""
    from app.crud.crud_users import crud_users
    from app.schemas.user import UserCreateInternal

    user_data = UserCreateInternal(
        email="admin@example.com",
        username="superadmin",
        hashed_password="$2b$12$dummy",
        is_verified=True,
        is_superuser=True,
        role=UserRole.SUPER_ADMIN,
    )
    user = await crud_users.create(db=db_session, object=user_data)

    # Give free plan — superadmin should bypass anyway
    sub = UserSubscription(
        user_id=user.id,
        plan_id=free_plan.id,
        status=SubscriptionStatus.ACTIVE,
        monthly_tokens_used=0,
        monthly_tts_minutes_used=0.0,
    )
    db_session.add(sub)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def quota_service(db_session: AsyncSession) -> QuotaService:
    """Create QuotaService instance."""
    return QuotaService(db_session)


# ==================== Helper ====================


async def _create_agents(db: AsyncSession, user: User, count: int):
    """Helper to create N agents for a user."""
    for i in range(count):
        agent = Agent(
            user_id=user.id,
            name=f"Agent-{i}",
            is_deleted=False,
        )
        db.add(agent)
    await db.commit()


async def _create_devices(db: AsyncSession, user: User, count: int):
    """Helper to create N devices for a user."""
    for i in range(count):
        device = Device(
            user_id=user.id,
            mac_address=f"AA:BB:CC:DD:EE:{i:02X}",
        )
        db.add(device)
    await db.commit()


# ==================== Tests ====================


class TestAgentQuota:
    """Tests for agent creation gating."""

    @pytest.mark.asyncio
    async def test_free_user_can_create_agent_within_limit(
        self, quota_service: QuotaService, free_user: User
    ):
        can, msg = await quota_service.can_create_agent(free_user.id)
        assert can is True
        assert msg == "OK"

    @pytest.mark.asyncio
    async def test_free_user_blocked_at_agent_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, free_user: User
    ):
        # FREE plan allows 2 agents
        await _create_agents(db_session, free_user, 2)

        can, msg = await quota_service.can_create_agent(free_user.id)
        assert can is False
        assert "Vượt quá giới hạn agent" in msg

    @pytest.mark.asyncio
    async def test_pro_user_can_create_more_agents(
        self, db_session: AsyncSession, quota_service: QuotaService, pro_user: User
    ):
        # PRO plan allows 10 agents — create 5, should still be OK
        await _create_agents(db_session, pro_user, 5)

        can, msg = await quota_service.can_create_agent(pro_user.id)
        assert can is True

    @pytest.mark.asyncio
    async def test_superadmin_bypasses_agent_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, superadmin_user: User
    ):
        # Create more agents than FREE plan allows
        await _create_agents(db_session, superadmin_user, 10)

        can, msg = await quota_service.can_create_agent(superadmin_user.id)
        assert can is True, "SuperAdmin should bypass agent quota"


class TestDeviceQuota:
    """Tests for device creation gating."""

    @pytest.mark.asyncio
    async def test_free_user_blocked_at_device_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, free_user: User
    ):
        # FREE plan allows 1 device
        await _create_devices(db_session, free_user, 1)

        can, msg = await quota_service.can_create_device(free_user.id)
        assert can is False
        assert "Vượt quá giới hạn thiết bị" in msg

    @pytest.mark.asyncio
    async def test_pro_user_can_create_within_device_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, pro_user: User
    ):
        await _create_devices(db_session, pro_user, 3)

        can, msg = await quota_service.can_create_device(pro_user.id)
        assert can is True

    @pytest.mark.asyncio
    async def test_superadmin_bypasses_device_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, superadmin_user: User
    ):
        await _create_devices(db_session, superadmin_user, 20)

        can, msg = await quota_service.can_create_device(superadmin_user.id)
        assert can is True


class TestTokenQuota:
    """Tests for monthly token usage gating."""

    @pytest.mark.asyncio
    async def test_free_user_blocked_when_tokens_exceeded(
        self, db_session: AsyncSession, quota_service: QuotaService, free_user: User
    ):
        # Set token usage near limit (FREE = 50,000)
        sub = (await db_session.execute(
            select(UserSubscription).where(UserSubscription.user_id == free_user.id)
        )).scalar_one()
        sub.monthly_tokens_used = 49_000
        await db_session.commit()

        # Requesting 2000 would exceed 50,000 limit
        can, msg = await quota_service.can_use_tokens(free_user.id, 2000)
        assert can is False
        assert "Không đủ quota token" in msg

    @pytest.mark.asyncio
    async def test_free_user_allowed_within_token_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, free_user: User
    ):
        can, msg = await quota_service.can_use_tokens(free_user.id, 1000)
        assert can is True

    @pytest.mark.asyncio
    async def test_superadmin_bypasses_token_limit(
        self, db_session: AsyncSession, quota_service: QuotaService, superadmin_user: User
    ):
        # Set extreme usage
        sub = (await db_session.execute(
            select(UserSubscription).where(UserSubscription.user_id == superadmin_user.id)
        )).scalar_one()
        sub.monthly_tokens_used = 999_999
        await db_session.commit()

        can, msg = await quota_service.can_use_tokens(superadmin_user.id, 100_000)
        assert can is True


class TestProviderAccess:
    """Tests for provider access gating."""

    @pytest.mark.asyncio
    async def test_free_user_restricted_to_allowed_providers(
        self, quota_service: QuotaService, free_user: User
    ):
        # FREE plan only allows the retained TTS providers
        can, msg = await quota_service.can_use_provider(free_user.id, "openai")
        assert can is False
        assert "không hỗ trợ nhà cung cấp" in msg

    @pytest.mark.asyncio
    async def test_free_user_can_use_allowed_provider(
        self, quota_service: QuotaService, free_user: User
    ):
        can, msg = await quota_service.can_use_provider(free_user.id, "edge_tts")
        assert can is True

    @pytest.mark.asyncio
    async def test_pro_user_can_use_any_provider(
        self, quota_service: QuotaService, pro_user: User
    ):
        # PRO plan has no provider restrictions
        can, msg = await quota_service.can_use_provider(pro_user.id, "openai")
        assert can is True

    @pytest.mark.asyncio
    async def test_free_user_cannot_add_custom_provider(
        self, quota_service: QuotaService, free_user: User
    ):
        can, msg = await quota_service.can_use_custom_provider(free_user.id)
        assert can is False

    @pytest.mark.asyncio
    async def test_pro_user_can_add_custom_provider(
        self, quota_service: QuotaService, pro_user: User
    ):
        can, msg = await quota_service.can_use_custom_provider(pro_user.id)
        assert can is True


class TestDeviceFeatures:
    """Tests for device feature toggles based on plan."""

    @pytest.mark.asyncio
    async def test_superadmin_gets_all_features(
        self, quota_service: QuotaService, superadmin_user: User
    ):
        features = await quota_service.get_device_features_for_user(superadmin_user.id)
        assert features["intercom"] is True
        assert features["memory"] is True
        assert features["reminder"] is True
        assert features["education"] is True

    @pytest.mark.asyncio
    async def test_feature_flags_from_plan(
        self, quota_service: QuotaService, free_user: User
    ):
        # Even with no explicit features on free plan, should return something
        features = await quota_service.get_device_features_for_user(free_user.id)
        assert isinstance(features, dict)

    @pytest.mark.asyncio
    async def test_api_access_flag(
        self, quota_service: QuotaService, free_user: User, pro_user: User
    ):
        free_api = await quota_service.has_api_access(free_user.id)
        pro_api = await quota_service.has_api_access(pro_user.id)
        assert free_api is False
        assert pro_api is True


class TestFullQuotaSummary:
    """Tests for the full quota summary endpoint."""

    @pytest.mark.asyncio
    async def test_free_user_quota_summary(
        self, quota_service: QuotaService, free_user: User
    ):
        quotas = await quota_service.get_user_quotas(free_user.id)
        assert quotas.plan_name == "Free"
        assert quotas.agents.limit == 2
        assert quotas.devices.limit == 1
        assert quotas.monthly_tokens.limit == 50_000
        assert quotas.enable_api_access is False

    @pytest.mark.asyncio
    async def test_pro_user_quota_summary(
        self, quota_service: QuotaService, pro_user: User
    ):
        quotas = await quota_service.get_user_quotas(pro_user.id)
        assert quotas.plan_name == "Pro"
        assert quotas.agents.limit == 10
        assert quotas.devices.limit == 5
        assert quotas.enable_api_access is True
        assert quotas.enable_webhook is True

    @pytest.mark.asyncio
    async def test_superadmin_quota_summary_all_unlimited(
        self, quota_service: QuotaService, superadmin_user: User
    ):
        quotas = await quota_service.get_user_quotas(superadmin_user.id)
        assert quotas.agents.is_unlimited is True
        assert quotas.devices.is_unlimited is True
        assert quotas.monthly_tokens.is_unlimited is True
        assert quotas.enable_api_access is True


class TestNoSubscription:
    """Tests for users without any subscription."""

    @pytest.mark.asyncio
    async def test_no_subscription_returns_default(
        self, db_session: AsyncSession, quota_service: QuotaService
    ):
        """User without subscription should get default (zero) quotas."""
        from app.crud.crud_users import crud_users
        from app.schemas.user import UserCreateInternal

        user = await crud_users.create(
            db=db_session,
            object=UserCreateInternal(
                email="nosub@example.com",
                username="nosub",
                hashed_password="$2b$12$dummy",
                is_verified=True,
                is_superuser=False,
            ),
        )

        quotas = await quota_service.get_user_quotas(user.id)
        assert quotas.plan_name == "FREE"
        assert quotas.agents.limit == 0
