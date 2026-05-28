"""
Xiaozhi CE (Community Edition) - Data Models
Core models only. No sales/education/meeting models.
"""
from .reminder import Reminder

from .user import User
from .agent import Agent
from .agent_template import AgentTemplate  # Keep for migration compatibility
from .template import Template
from .agent_template_assignment import AgentTemplateAssignment
from .device import Device
from .agent_message import AgentMessage
from .provider import Provider
from .server_mcp_config import ServerMCPConfig
from .agent_mcp_selection import AgentMCPSelection, AgentMCPServerSelected
from .subscription_plan import SubscriptionPlan
from .user_subscription import UserSubscription, SubscriptionStatus, SubscriptionBillingCycle
from .subscription_payment import SubscriptionPayment, PaymentStatus, PaymentMethod
from .usage_tracker import UsageTracker
from .user_tool import UserTool
from .firmware import (
    Firmware,
    FirmwareDeployment,
    BoardType as FirmwareBoardType,
    DeploymentStatus,
    DeploymentTargetType,
)
from .asset_template import AssetTemplate, BoardType as AssetBoardType, ScreenType as AssetScreenType
from .board_type import BoardType, ScreenType

# Advanced AI Features
from .conversation_memory import ConversationMemory, EmotionLog, MemoryType, MemorySource
from .skill import Skill, SkillInstallation, SkillReview, SkillType, SkillCategory
from .voice import Voice

# Emoji Pack Feature
from .emoji_pack import EmojiPack, EmojiPackAsset, FlashJob, ApprovalStatus, EMOTION_NAMES, EMOTION_IDS

# Knowledge Base (pgvector)
from .knowledge_embedding import KnowledgeEmbedding
from .knowledge_base import KnowledgeBase
from .agent_knowledge_base import AgentKnowledgeBase  # DEPRECATED: Use TemplateKnowledgeBase
from .template_knowledge_base import TemplateKnowledgeBase

# Site Settings
from .site_settings import SiteSettings

# User Integrations (Centralized Channel Config)
from .user_connection import UserConnection
