"""
Tests for QuotaService

Tests comprehensive quota management including:
- User quota checks
- Subscription plan limits
- Batch counting for N+1 prevention
- Privileged user bypass
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.services.quota_service import QuotaService, QuotaStatus, UserQuotas
from app.models.subscription_plan import SubscriptionPlan
from app.models.user_subscription import UserSubscription, SubscriptionStatus
from app.models.agent import Agent
from app.models.device import Device
from app.models.server_mcp_config import ServerMCPConfig
from app.models.template import Template
from app.models.user import User, UserRole


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def quota_service(mock_db_session):
    """Create QuotaService with mock session."""
    return QuotaService(mock_db_session)


@pytest.fixture
def sample_plan():
    """Create sample subscription plan."""
    plan = MagicMock(spec=SubscriptionPlan)
    plan.id = 1
    plan.name = "PRO"
    plan.display_name = "Pro Plan"
    plan.max_agents = 10
    plan.max_devices = 5
    plan.max_mcps = 3
    plan.max_templates = 20
    plan.max_tools = 50
    plan.max_monthly_tokens = 1000000
    plan.max_tts_minutes_monthly = 600
    plan.max_knowledge_base_size_mb = 500
    plan.enable_api_access = True
    plan.enable_webhook = True
    plan.enable_custom_branding = True
    plan.enable_priority_support = True
    plan.allowed_provider_types = None
    plan.allow_custom_providers = True
    plan.allowed_provider_categories = None
    plan.allowed_device_features = None
    return plan


@pytest.fixture
def sample_subscription(sample_plan):
    """Create sample user subscription."""
    sub = MagicMock(spec=UserSubscription)
    sub.id = 1
    sub.user_id = "user-123"
    sub.plan_id = sample_plan.id
    sub.plan = sample_plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.monthly_tokens_used = 500000
    sub.monthly_tts_minutes_used = 300
    return sub


class TestQuotaStatus:
    """Tests for QuotaStatus dataclass."""

    def test_quota_status_creation(self):
        """Test QuotaStatus creation with limits."""
        status = QuotaStatus(
            current=5,
            limit=10,
            remaining=5,
            is_unlimited=False,
            exceeded=False
        )
        assert status.current == 5
        assert status.limit == 10
        assert status.remaining == 5
        assert not status.is_unlimited
        assert not status.exceeded

    def test_quota_status_unlimited(self):
        """Test QuotaStatus with unlimited limit."""
        status = QuotaStatus(
            current=100,
            limit=-1,
            remaining=-1,
            is_unlimited=True,
            exceeded=False
        )
        assert status.is_unlimited
        assert not status.exceeded

    def test_usage_percent_calculation(self):
        """Test usage percentage calculation."""
        status = QuotaStatus(
            current=5,
            limit=10,
            remaining=5,
            is_unlimited=False,
            exceeded=False
        )
        assert status.usage_percent == 50.0

    def test_usage_percent_unlimited(self):
        """Test usage percentage for unlimited returns 0."""
        status = QuotaStatus(
            current=100,
            limit=-1,
            remaining=-1,
            is_unlimited=True,
            exceeded=False
        )
        assert status.usage_percent == 0.0

    def test_usage_percent_at_limit(self):
        """Test usage percentage at limit caps at 100."""
        status = QuotaStatus(
            current=10,
            limit=10,
            remaining=0,
            is_unlimited=False,
            exceeded=True
        )
        assert status.usage_percent == 100.0


class TestQuotaService:
    """Tests for QuotaService class."""

    @pytest.mark.asyncio
    async def test_is_privileged_user_admin(self, quota_service, mock_db_session):
        """Test admin user bypasses quotas."""
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user.role = UserRole.ADMIN
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        
        is_privileged = await quota_service._is_privileged_user("admin-user-id")
        assert is_privileged is True

    @pytest.mark.asyncio
    async def test_is_privileged_user_super_admin(self, quota_service, mock_db_session):
        """Test superadmin user bypasses quotas."""
        mock_user = MagicMock()
        mock_user.is_superuser = True
        mock_user.role = UserRole.USER
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        
        is_privileged = await quota_service._is_privileged_user("superuser-id")
        assert is_privileged is True

    @pytest.mark.asyncio
    async def test_is_privileged_user_regular(self, quota_service, mock_db_session):
        """Test regular user does not bypass quotas."""
        mock_user = MagicMock()
        mock_user.is_superuser = False
        mock_user.role = UserRole.USER
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        
        is_privileged = await quota_service._is_privileged_user("regular-user-id")
        assert is_privileged is False

    @pytest.mark.asyncio
    async def test_get_user_subscription(self, quota_service, mock_db_session, sample_subscription):
        """Test getting user subscription."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_subscription
        mock_db_session.execute.return_value = mock_result
        
        subscription = await quota_service.get_user_subscription("user-123")
        assert subscription is not None
        assert subscription.user_id == "user-123"
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_subscription_none(self, quota_service, mock_db_session):
        """Test getting subscription for user without subscription."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        subscription = await quota_service.get_user_subscription("no-sub-user")
        assert subscription is None

    def test_create_quota_status_normal(self, quota_service):
        """Test creating quota status for normal limits."""
        status = quota_service._create_quota_status(current=5, limit=10)
        
        assert status.current == 5
        assert status.limit == 10
        assert status.remaining == 5
        assert not status.is_unlimited
        assert not status.exceeded

    def test_create_quota_status_unlimited(self, quota_service):
        """Test creating quota status for unlimited."""
        status = quota_service._create_quota_status(current=100, limit=-1)
        
        assert status.current == 100
        assert status.limit == -1
        assert status.remaining == -1
        assert status.is_unlimited
        assert not status.exceeded

    def test_create_quota_status_exceeded(self, quota_service):
        """Test creating quota status when exceeded."""
        status = quota_service._create_quota_status(current=15, limit=10)
        
        assert status.current == 15
        assert status.limit == 10
        assert status.remaining == 0
        assert not status.is_unlimited
        assert status.exceeded

    @pytest.mark.asyncio
    async def test_count_agents(self, quota_service, mock_db_session):
        """Test counting user agents."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db_session.execute.return_value = mock_result
        
        count = await quota_service.count_agents("user-123")
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_devices(self, quota_service, mock_db_session):
        """Test counting user devices."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_db_session.execute.return_value = mock_result
        
        count = await quota_service.count_devices("user-123")
        assert count == 3

    @pytest.mark.asyncio
    async def test_can_create_agent_privileged(self, quota_service, mock_db_session):
        """Test privileged user can always create agents."""
        with patch.object(quota_service, '_is_privileged_user', return_value=True):
            can_create, message = await quota_service.can_create_agent("admin-id")
            assert can_create is True
            assert message == "OK"

    @pytest.mark.asyncio
    async def test_can_create_agent_limit_exceeded(self, quota_service, mock_db_session, sample_plan, sample_subscription):
        """Test user at agent limit cannot create more."""
        with patch.object(quota_service, '_is_privileged_user', return_value=False):
            with patch.object(quota_service, 'get_user_plan', return_value=sample_plan):
                with patch.object(quota_service, 'count_agents', return_value=10):
                    can_create, message = await quota_service.can_create_agent("user-123")
                    assert can_create is False
                    assert "agent" in message.lower()

    @pytest.mark.asyncio
    async def test_can_create_agent_no_plan(self, quota_service, mock_db_session):
        """Test user without plan cannot create agents."""
        with patch.object(quota_service, '_is_privileged_user', return_value=False):
            with patch.object(quota_service, 'get_user_plan', return_value=None):
                can_create, message = await quota_service.can_create_agent("user-123")
                assert can_create is False
                assert "subscription" in message.lower() or "không tìm thấy" in message.lower()

    @pytest.mark.asyncio
    async def test_can_create_device_privileged(self, quota_service, mock_db_session):
        """Test privileged user can always create devices."""
        with patch.object(quota_service, '_is_privileged_user', return_value=True):
            can_create, message = await quota_service.can_create_device("admin-id")
            assert can_create is True

    @pytest.mark.asyncio
    async def test_can_create_mcp_privileged(self, quota_service, mock_db_session):
        """Test privileged user can always create MCP servers."""
        with patch.object(quota_service, '_is_privileged_user', return_value=True):
            can_create, message = await quota_service.can_create_mcp("admin-id")
            assert can_create is True

    @pytest.mark.asyncio
    async def test_can_create_template_privileged(self, quota_service, mock_db_session):
        """Test privileged user can always create templates."""
        with patch.object(quota_service, '_is_privileged_user', return_value=True):
            can_create, message = await quota_service.can_create_template("admin-id")
            assert can_create is True


class TestGetAllCounts:
    """Tests for batch count optimization (N+1 prevention)."""

    @pytest.mark.asyncio
    async def test_get_all_counts_returns_dict(self, quota_service, mock_db_session):
        """Test get_all_counts returns dictionary with all counts."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (5,),   # agents count
            (3,),   # devices count
            (2,),   # mcps count
            (10,),  # templates count
            MagicMock()  # mcps configs
        ]
        mock_result.all.return_value[4].scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        counts = await quota_service.get_all_counts("user-123")
        
        assert isinstance(counts, dict)
        assert "agents" in counts
        assert "devices" in counts
        assert "mcps" in counts
        assert "templates" in counts
        assert "tools" in counts
        assert counts["agents"] == 5
        assert counts["devices"] == 3

    @pytest.mark.asyncio
    async def test_get_all_counts_calculates_tools_from_mcps(self, quota_service, mock_db_session):
        """Test tools count is calculated from MCP configs."""
        mock_config = MagicMock()
        mock_config.tools = ["tool1", "tool2", "tool3"]
        
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (0,),   # agents count
            (0,),   # devices count
            (1,),   # mcps count
            (0,),   # templates count
            MagicMock()  # mcps configs
        ]
        mock_result.all.return_value[4].scalars.return_value.all.return_value = [mock_config]
        mock_db_session.execute.return_value = mock_result
        
        counts = await quota_service.get_all_counts("user-123")
        
        assert counts["tools"] == 3
        assert counts["mcps"] == 1

    @pytest.mark.asyncio
    async def test_get_all_counts_empty_returns_zeros(self, quota_service, mock_db_session):
        """Test get_all_counts returns zeros for new user."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (0,),   # agents count
            (0,),   # devices count
            (0,),   # mcps count
            (0,),   # templates count
            MagicMock()  # mcps configs
        ]
        mock_result.all.return_value[4].scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result
        
        counts = await quota_service.get_all_counts("new-user")
        
        assert counts["agents"] == 0
        assert counts["devices"] == 0
        assert counts["mcps"] == 0
        assert counts["templates"] == 0
        assert counts["tools"] == 0


class TestGetUserQuotas:
    """Tests for complete user quota summary."""

    @pytest.mark.asyncio
    async def test_get_user_quotas_no_subscription(self, quota_service, mock_db_session):
        """Test quotas for user without subscription returns default."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        quotas = await quota_service.get_user_quotas("no-sub-user")
        
        assert isinstance(quotas, UserQuotas)
        assert quotas.agents.current == 0
        assert quotas.agents.exceeded is True  # No plan = exceeded

    @pytest.mark.asyncio
    async def test_get_user_quotas_privileged(self, quota_service, mock_db_session, sample_subscription):
        """Test quotas for privileged user shows unlimited."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_subscription
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(quota_service, '_is_privileged_user', return_value=True):
            with patch.object(quota_service, 'get_all_counts', return_value={
                "agents": 50, "devices": 20, "mcps": 5, "templates": 100, "tools": 200
            }):
                quotas = await quota_service.get_user_quotas("admin-user")
                
                assert quotas.plan_name == "ADMIN / SUPER USER"
                assert quotas.agents.is_unlimited is True
                assert quotas.agents.current == 50

    @pytest.mark.asyncio
    async def test_get_user_quotas_regular_user(self, quota_service, mock_db_session, sample_subscription, sample_plan):
        """Test quotas for regular user shows actual limits."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_subscription
        mock_db_session.execute.return_value = mock_result
        
        with patch.object(quota_service, '_is_privileged_user', return_value=False):
            with patch.object(quota_service, 'get_all_counts', return_value={
                "agents": 5, "devices": 2, "mcps": 1, "templates": 10, "tools": 20
            }):
                quotas = await quota_service.get_user_quotas("regular-user")
                
                assert quotas.plan_name == "Pro Plan"
                assert quotas.agents.current == 5
                assert quotas.agents.limit == 10
                assert quotas.devices.current == 2
                assert quotas.devices.limit == 5