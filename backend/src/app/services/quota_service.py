"""
Quota Service - Centralized quota management for subscription plans.

This service provides a single point for checking and enforcing quotas
based on user subscription plans.
"""

import logging
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_subscription import UserSubscription, SubscriptionStatus
from app.models.subscription_plan import SubscriptionPlan
from app.models.agent import Agent
from app.models.device import Device
from app.models.server_mcp_config import ServerMCPConfig
from app.models.user import User, UserRole
from app.models.template import Template

logger = logging.getLogger(__name__)


@dataclass
class QuotaStatus:
    """Status of a specific quota"""
    current: int
    limit: int
    remaining: int
    is_unlimited: bool
    exceeded: bool
    
    @property
    def usage_percent(self) -> float:
        if self.is_unlimited or self.limit == 0:
            return 0.0
        return min(100.0, (self.current / self.limit) * 100)


@dataclass
class UserQuotas:
    """All quotas for a user"""
    agents: QuotaStatus
    devices: QuotaStatus
    mcps: QuotaStatus
    templates: QuotaStatus
    tools: QuotaStatus
    monthly_tokens: QuotaStatus
    monthly_tts_minutes: QuotaStatus
    knowledge_base_mb: QuotaStatus
    
    # Feature flags from plan
    enable_api_access: bool = False
    enable_webhook: bool = False
    enable_custom_branding: bool = False
    enable_priority_support: bool = False
    
    # Provider access control
    allowed_provider_types: list[str] | None = None
    allow_custom_providers: bool = True
    allowed_provider_categories: list[str] | None = None
    
    # Device feature toggles from plan
    allowed_device_features: dict | None = None
    
    # Plan info
    plan_name: str = "FREE"
    plan_id: int | None = None


class QuotaService:
    """
    Centralized service for quota management.
    
    Usage:
        quota_service = QuotaService(db)
        
        # Check single quota
        can_create, message = await quota_service.can_create_agent(user_id)
        
        # Get all quotas
        quotas = await quota_service.get_user_quotas(user_id)
        
        # Check provider access
        can_use = await quota_service.can_use_provider(user_id, "openai", "LLM")
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _is_privileged_user(self, user_id: str) -> bool:
        """Check if user has admin privileges to bypass quotas"""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if user and (user.is_superuser or user.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]):
            return True
        return False
    
    async def get_user_subscription(self, user_id: str) -> Optional[UserSubscription]:
        """Get user's active subscription with plan loaded"""
        stmt = (
            select(UserSubscription)
            .where(UserSubscription.user_id == user_id)
            .where(UserSubscription.status == SubscriptionStatus.ACTIVE)
            .order_by(UserSubscription.created_at.desc())
        )
        result = await self.db.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if subscription:
            await self.db.refresh(subscription, ["plan"])
        
        return subscription
    
    async def get_user_plan(self, user_id: str) -> Optional[SubscriptionPlan]:
        """Get user's current plan"""
        subscription = await self.get_user_subscription(user_id)
        return subscription.plan if subscription else None
    
    async def get_all_counts(self, user_id: str) -> dict[str, int]:
        """Batch count all user entities in single query to avoid N+1"""
        from sqlalchemy import and_
        
        user_filter = Agent.user_id == user_id
        agents_stmt = select(func.count(Agent.id)).where(and_(user_filter, Agent.is_deleted == False))
        
        devices_stmt = select(func.count(Device.id)).where(Device.user_id == user_id)
        
        mcps_stmt = select(func.count(ServerMCPConfig.id)).where(
            and_(ServerMCPConfig.user_id == user_id, ServerMCPConfig.is_deleted == False)
        )
        
        templates_stmt = select(func.count(Template.id)).where(
            and_(Template.user_id == user_id, Template.is_deleted == False)
        )
        
        mcps_fetch_stmt = select(ServerMCPConfig).where(
            and_(ServerMCPConfig.user_id == user_id, ServerMCPConfig.is_deleted == False)
        )
        
        results = await self.db.execute(
            select(agents_stmt, devices_stmt, mcps_stmt, templates_stmt, mcps_fetch_stmt)
        )
        all_results = results.all()
        
        agents_count = all_results[0][0] if all_results else 0
        devices_count = all_results[1][0] if len(all_results) > 1 else 0
        mcps_count = all_results[2][0] if len(all_results) > 2 else 0
        templates_count = all_results[3][0] if len(all_results) > 3 else 0
        
        mcps_configs = all_results[4][0].scalars().all() if len(all_results) > 4 else []
        tools_count = sum(len(c.tools) if c.tools else 0 for c in mcps_configs)
        
        return {
            "agents": agents_count,
            "devices": devices_count,
            "mcps": mcps_count,
            "templates": templates_count,
            "tools": tools_count
        }
    
    def _create_quota_status(self, current: int, limit: int) -> QuotaStatus:
        """Create QuotaStatus from current count and limit"""
        is_unlimited = limit == -1
        exceeded = not is_unlimited and current >= limit
        remaining = -1 if is_unlimited else max(0, limit - current)
        
        return QuotaStatus(
            current=current,
            limit=limit,
            remaining=remaining,
            is_unlimited=is_unlimited,
            exceeded=exceeded
        )
    
    # ===== Count methods =====
    
    async def count_agents(self, user_id: str) -> int:
        """Count user's agents"""
        stmt = select(func.count(Agent.id)).where(
            Agent.user_id == user_id,
            Agent.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def count_devices(self, user_id: str) -> int:
        """Count user's devices"""
        stmt = select(func.count(Device.id)).where(
            Device.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def count_mcps(self, user_id: str) -> int:
        """Count user's MCP server configs"""
        stmt = select(func.count(ServerMCPConfig.id)).where(
            ServerMCPConfig.user_id == user_id,
            ServerMCPConfig.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def count_templates(self, user_id: str) -> int:
        """Count user's templates"""
        stmt = select(func.count(Template.id)).where(
            Template.user_id == user_id,
            Template.is_deleted == False
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def count_tools(self, user_id: str) -> int:
        """Count user's tools (from MCP configs)"""
        # Tools are stored in MCP configs, count total tools across all configs
        stmt = select(ServerMCPConfig).where(
            ServerMCPConfig.user_id == user_id,
            ServerMCPConfig.is_deleted == False
        )
        result = await self.db.execute(stmt)
        configs = result.scalars().all()
        
        total_tools = 0
        for config in configs:
            if config.tools:
                total_tools += len(config.tools)
        
        return total_tools
    
    # ===== Quota check methods =====
    
    async def can_create_agent(self, user_id: str) -> tuple[bool, str]:
        """Check if user can create a new agent"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription. Vui lòng liên hệ hỗ trợ."
        
        current = await self.count_agents(user_id)
        limit = plan.max_agents
        
        if limit != -1 and current >= limit:
            return False, f"Vượt quá giới hạn agent. Gói {plan.display_name} cho phép tối đa {limit} agent. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    async def can_create_device(self, user_id: str) -> tuple[bool, str]:
        """Check if user can create/activate a new device"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription. Vui lòng liên hệ hỗ trợ."
        
        current = await self.count_devices(user_id)
        limit = plan.max_devices
        
        if limit != -1 and current >= limit:
            return False, f"Vượt quá giới hạn thiết bị. Gói {plan.display_name} cho phép tối đa {limit} thiết bị. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    async def can_create_mcp(self, user_id: str) -> tuple[bool, str]:
        """Check if user can create a new MCP server config"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription. Vui lòng liên hệ hỗ trợ."
        
        current = await self.count_mcps(user_id)
        limit = plan.max_mcps
        
        if limit != -1 and current >= limit:
            return False, f"Vượt quá giới hạn MCP servers. Gói {plan.display_name} cho phép tối đa {limit} MCP servers. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    async def can_create_template(self, user_id: str) -> tuple[bool, str]:
        """Check if user can create a new template"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription. Vui lòng liên hệ hỗ trợ."
        
        current = await self.count_templates(user_id)
        limit = plan.max_templates
        
        if limit != -1 and current >= limit:
            return False, f"Vượt quá giới hạn mẫu. Gói {plan.display_name} cho phép tối đa {limit} mẫu. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    async def can_add_tools(self, user_id: str, new_tools_count: int = 1) -> tuple[bool, str]:
        """Check if user can add more tools"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription. Vui lòng liên hệ hỗ trợ."
        
        current = await self.count_tools(user_id)
        limit = plan.max_tools
        
        if limit != -1 and (current + new_tools_count) > limit:
            return False, f"Vượt quá giới hạn công cụ. Gói {plan.display_name} cho phép tối đa {limit} công cụ. Hiện có {current}. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    async def can_use_tokens(self, user_id: str, tokens_needed: int) -> tuple[bool, str]:
        """Check if user has enough token quota"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return False, "Không tìm thấy gói subscription."
        
        plan = subscription.plan
        limit = plan.max_monthly_tokens
        used = subscription.monthly_tokens_used
        
        if limit != -1 and (used + tokens_needed) > limit:
            remaining = max(0, limit - used)
            return False, f"Không đủ quota token. Còn lại {remaining:,} tokens trong tháng này."
        
        return True, "OK"
    
    async def can_use_tts_minutes(self, user_id: str, minutes_needed: float) -> tuple[bool, str]:
        """Check if user has enough TTS minutes quota"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return False, "Không tìm thấy gói subscription."
        
        plan = subscription.plan
        limit = plan.max_tts_minutes_monthly
        used = subscription.monthly_tts_minutes_used
        
        if limit != -1 and (used + minutes_needed) > limit:
            remaining = max(0, limit - used)
            return False, f"Không đủ quota TTS. Còn lại {remaining} phút trong tháng này."
        
        return True, "OK"
    
    # ===== Provider access methods =====
    
    async def can_use_provider(
        self, 
        user_id: str, 
        provider_type: str, 
        category: str | None = None
    ) -> tuple[bool, str]:
        """
        Check if user can use a specific provider.
        
        Args:
            user_id: User ID
            provider_type: Provider type (openai, gemini, claude, etc.)
            category: Provider category (LLM, TTS, ASR, VAD, Memory)
        
        Returns:
            (can_use, message)
        """
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription."
        
        # Check provider type
        allowed_types = plan.allowed_provider_types
        if allowed_types is not None and provider_type not in allowed_types:
            return False, f"Gói {plan.display_name} không hỗ trợ nhà cung cấp {provider_type}. Vui lòng nâng cấp gói."
        
        # Check category
        if category:
            allowed_categories = plan.allowed_provider_categories
            if allowed_categories is not None and category not in allowed_categories:
                return False, f"Gói {plan.display_name} không hỗ trợ loại dịch vụ {category}. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    async def can_use_custom_provider(self, user_id: str) -> tuple[bool, str]:
        """Check if user can add their own provider API keys"""
        if await self._is_privileged_user(user_id):
            return True, "OK"

        plan = await self.get_user_plan(user_id)
        if not plan:
            return False, "Không tìm thấy gói subscription."
        
        if not plan.allow_custom_providers:
            return False, f"Gói {plan.display_name} không cho phép thêm API key riêng. Vui lòng nâng cấp gói."
        
        return True, "OK"
    
    # ===== Device feature methods =====
    
    # Default features for FREE plan (fallback)
    DEFAULT_FREE_FEATURES = {
        "music": True,
        "radio": True,
        "weather": True,
        "alarm": True,
        "sdCardMusic": True,
        "bluetooth": True,
        "homeAssistant": False,
        "voiceRecording": False,
        "reminder": False,
        "memory": False,
        "intercom": False,
        "education": False,
        "customFirmware": False,
    }
    
    # All features enabled (for admins/enterprise)
    ALL_FEATURES = {
        "music": True,
        "radio": True,
        "weather": True,
        "alarm": True,
        "sdCardMusic": True,
        "bluetooth": True,
        "homeAssistant": True,
        "voiceRecording": True,
        "reminder": True,
        "memory": True,
        "intercom": True,
        "education": True,
        "customFirmware": True,
    }
    
    async def get_device_features_for_user(self, user_id: str) -> dict:
        """
        Get allowed device features based on user's subscription plan.
        
        Features are merged: plan features + device-specific overrides.
        Returns a dict of feature_name -> bool.
        """
        if await self._is_privileged_user(user_id):
            return self.ALL_FEATURES.copy()
        
        plan = await self.get_user_plan(user_id)
        if not plan:
            return self.DEFAULT_FREE_FEATURES.copy()
        
        # Use plan's allowed_device_features, fallback to all features
        plan_features = getattr(plan, 'allowed_device_features', None)
        if plan_features:
            return plan_features.copy()
        
        # If plan has no explicit features, allow all (backwards compatible)
        return self.ALL_FEATURES.copy()
    
    async def get_device_effective_features(
        self, user_id: str, device_features: dict | None = None
    ) -> dict:
        """
        Get effective features for a specific device.
        
        Merges plan-level features with device-specific overrides.
        Device overrides can only DISABLE features allowed by the plan,
        never ENABLE features not in the plan.
        
        Args:
            user_id: User ID
            device_features: Device-specific feature overrides (from device.features)
        
        Returns:
            Effective features dict
        """
        plan_features = await self.get_device_features_for_user(user_id)
        
        if not device_features:
            return plan_features
        
        # Merge: plan sets ceiling, device can only turn OFF
        effective = {}
        for key, plan_allowed in plan_features.items():
            device_value = device_features.get(key)
            if device_value is not None:
                # Device can only disable what plan allows, never enable what plan denies
                effective[key] = plan_allowed and device_value
            else:
                effective[key] = plan_allowed
        
        return effective
    
    async def can_use_device_feature(
        self, user_id: str, feature_name: str, device_features: dict | None = None
    ) -> tuple[bool, str]:
        """
        Check if a specific device feature is allowed for the user.
        
        Args:
            user_id: User ID
            feature_name: Feature to check (e.g., 'reminder', 'memory', 'intercom')
            device_features: Optional device-specific overrides
        
        Returns:
            (can_use, message)
        """
        effective = await self.get_device_effective_features(user_id, device_features)
        
        if feature_name not in effective:
            return True, "OK"  # Unknown features are allowed by default
        
        if not effective[feature_name]:
            plan = await self.get_user_plan(user_id)
            plan_name = plan.display_name if plan else "Free"
            return False, f"Tính năng '{feature_name}' không khả dụng trong gói {plan_name}. Vui lòng nâng cấp."
        
        return True, "OK"
    
    # ===== Feature flags =====
    
    async def has_api_access(self, user_id: str) -> bool:
        """Check if user has API access enabled"""
        plan = await self.get_user_plan(user_id)
        return plan.enable_api_access if plan else False
    
    async def has_webhook_access(self, user_id: str) -> bool:
        """Check if user has webhook access enabled"""
        plan = await self.get_user_plan(user_id)
        return plan.enable_webhook if plan else False
    
    async def has_custom_branding(self, user_id: str) -> bool:
        """Check if user has custom branding enabled"""
        plan = await self.get_user_plan(user_id)
        return plan.enable_custom_branding if plan else False
    
    async def has_priority_support(self, user_id: str) -> bool:
        """Check if user has priority support enabled"""
        plan = await self.get_user_plan(user_id)
        return plan.enable_priority_support if plan else False
    
    # ===== Full quota summary =====
    
    async def get_user_quotas(self, user_id: str) -> UserQuotas:
        """Get complete quota status for a user"""
        subscription = await self.get_user_subscription(user_id)
        
        if not subscription:
            # Return default quotas for users without subscription
            default_status = self._create_quota_status(0, 0)
            return UserQuotas(
                agents=default_status,
                devices=default_status,
                mcps=default_status,
                templates=default_status,
                tools=default_status,
                monthly_tokens=default_status,
                monthly_tts_minutes=default_status,
                knowledge_base_mb=default_status,
            )
        
        # Helper for privileged users (return unlimited/enabled for everything)
        if await self._is_privileged_user(user_id):
            unlimited_status = lambda current: self._create_quota_status(current, -1)
            
            counts = await self.get_all_counts(user_id)
            
            return UserQuotas(
                agents=unlimited_status(counts["agents"]),
                devices=unlimited_status(counts["devices"]),
                mcps=unlimited_status(counts["mcps"]),
                templates=unlimited_status(counts["templates"]),
                tools=unlimited_status(counts["tools"]),
                monthly_tokens=unlimited_status(subscription.monthly_tokens_used),
                monthly_tts_minutes=unlimited_status(subscription.monthly_tts_minutes_used),
                knowledge_base_mb=unlimited_status(0),
                
                # Enable all features
                enable_api_access=True,
                enable_webhook=True,
                enable_custom_branding=True,
                enable_priority_support=True,
                
                # Allow all providers
                allowed_provider_types=None,
                allow_custom_providers=True,
                allowed_provider_categories=None,
                
                plan_name="ADMIN / SUPER USER",
                plan_id=subscription.plan_id if subscription else None
            )

        plan = subscription.plan
        
        counts = await self.get_all_counts(user_id)
        
        return UserQuotas(
            agents=self._create_quota_status(counts["agents"], plan.max_agents),
            devices=self._create_quota_status(counts["devices"], plan.max_devices),
            mcps=self._create_quota_status(counts["mcps"], plan.max_mcps),
            templates=self._create_quota_status(counts["templates"], plan.max_templates),
            tools=self._create_quota_status(counts["tools"], plan.max_tools),
            monthly_tokens=self._create_quota_status(
                subscription.monthly_tokens_used, 
                plan.max_monthly_tokens
            ),
            monthly_tts_minutes=self._create_quota_status(
                subscription.monthly_tts_minutes_used,
                plan.max_tts_minutes_monthly
            ),
            knowledge_base_mb=self._create_quota_status(0, plan.max_knowledge_base_size_mb),  # TODO: Implement KB size tracking
            
            # Feature flags
            enable_api_access=plan.enable_api_access,
            enable_webhook=plan.enable_webhook,
            enable_custom_branding=plan.enable_custom_branding,
            enable_priority_support=plan.enable_priority_support,
            
            # Provider access
            allowed_provider_types=plan.allowed_provider_types,
            allow_custom_providers=plan.allow_custom_providers,
            allowed_provider_categories=plan.allowed_provider_categories,
            
            # Device features
            allowed_device_features=getattr(plan, 'allowed_device_features', None),
            
            # Plan info
            plan_name=plan.display_name,
            plan_id=plan.id,
        )


# Dependency for FastAPI
async def get_quota_service(db: AsyncSession) -> QuotaService:
    """FastAPI dependency to get QuotaService instance"""
    return QuotaService(db)
