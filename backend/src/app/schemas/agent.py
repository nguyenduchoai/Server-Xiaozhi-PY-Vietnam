"""
Agent schemas - Pydantic models for validation and serialization.

Agent is the CORE entity — contains all AI configuration inline.
"""

from datetime import datetime
from typing import Annotated, Optional

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..core.enums import StatusEnum
from .device import DeviceRead
from .banner import BannerConfig


class MCPServerReference(BaseModel):
    """Reference to an MCP server (user-defined or config-based).

    Format:
    - db:{uuid} - User's MCP server from database
    - config:{name} - System MCP server from config.yml

    Example:
    - db:550e8400-e29b-41d4-a716-446655440000
    - config:filesystem
    - config:fetch
    """

    reference: Annotated[
        str,
        Field(
            pattern=r"^(db:[a-f0-9\-]{36}|config:[a-zA-Z0-9_\-]+)$",
            description="MCP server reference format: 'db:{uuid}' or 'config:{name}'",
            examples=["db:550e8400-e29b-41d4-a716-446655440000", "config:filesystem"],
        ),
    ]

    @property
    def source(self) -> str:
        """Get source type: 'user' or 'config'."""
        return "user" if self.reference.startswith("db:") else "config"

    @property
    def identifier(self) -> str:
        """Get the identifier (uuid for user, name for config)."""
        return self.reference.split(":", 1)[1]


class MCPSelection(BaseModel):
    """MCP server selection configuration for agent.

    Mode:
    - "all": Agent uses ALL available MCP servers (user + config)
    - "selected": Agent uses only selected MCP servers
    """

    mode: Annotated[str, Field(pattern="^(all|selected)$")] = "all"
    servers: Annotated[list[MCPServerReference] | None, Field(max_length=50)] = None

    @field_validator("servers", mode="before")
    @classmethod
    def validate_servers_required_if_selected(cls, v, info):
        """Validate that servers array is provided when mode is 'selected'."""
        if info.data.get("mode") == "selected" and not v:
            raise ValueError("servers array is required when mode is 'selected'")
        return v


# ============ Provider Config Mixin ============

class ProviderConfigMixin(BaseModel):
    """Mixin for AI provider configuration fields.
    
    Used by both Agent (personal) and Template (marketplace).
    """
    
    # System prompt
    prompt: str | None = Field(default=None, description="System prompt for AI persona")
    
    # Provider references — format: "config:{name}" or "db:{uuid}" or NULL
    ASR: str | None = Field(default=None, description="ASR provider reference")
    LLM: str | None = Field(default=None, description="LLM provider reference")
    VLLM: str | None = Field(default=None, description="VLLM provider reference")
    TTS: str | None = Field(default=None, description="TTS provider reference")
    tts_voice: str | None = Field(default=None, description="TTS voice override")
    Memory: str | None = Field(default=None, description="Memory provider reference")
    Intent: str | None = Field(default=None, description="Intent provider reference")
    
    # Tools
    tools: list | None = Field(default_factory=list, description="Tool references")
    
    # Knowledge & Memory toggles
    enable_memory: bool = Field(default=True, description="Enable OpenMemory")
    enable_knowledge_base: bool = Field(default=True, description="Enable KB RAG")

    # Knowledge IDs
    knowledge_base_ids: list | None = Field(default_factory=list, description="KB UUIDs")

    # Feature modules
    enable_education: bool = Field(default=False, description="Enable Education module")
    enable_sales: bool = Field(default=False, description="Enable Sales module")
    enable_meeting: bool = Field(default=False, description="Enable Meeting module")
    course_ids: list | None = Field(default_factory=list, description="Education course UUIDs")
    sales_program_ids: list | None = Field(default_factory=list, description="Sales program UUIDs")
    meeting_room_ids: list | None = Field(default_factory=list, description="Meeting room UUIDs")


# ============ Agent Schemas ============

class AgentBase(BaseModel):
    """Base agent schema with common fields."""

    agent_name: Annotated[
        str, Field(min_length=1, max_length=255, examples=["My AI Bot"])
    ]
    description: Annotated[str, Field(examples=["An intelligent chatbot agent"])]
    status: StatusEnum = Field(
        default=StatusEnum.disabled, examples=[StatusEnum.disabled]
    )
    user_profile: Annotated[
        str | None,
        Field(
            max_length=2000, default=None, examples=["Enthusiastic user who loves AI"]
        ),
    ] = None
    chat_history_conf: Annotated[
        int,
        Field(
            ge=0,
            le=50,
            default=1,
            description="Chat history messages to keep (0=disabled, 1-50=number of messages)",
        ),
    ] = 1


class AgentCreate(AgentBase, ProviderConfigMixin):
    """Schema for creating a new agent (public API).
    
    Includes all AI config fields inline.
    """

    model_config = ConfigDict(extra="forbid")


class AgentCreateInternal(AgentBase, ProviderConfigMixin):
    """Internal schema for creating a new agent (with user_id)."""

    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(examples=["550e8400-e29b-41d4-a716-446655440000"])


class AgentRead(AgentBase, ProviderConfigMixin):
    """Schema for reading agent data — includes full AI config."""

    id: str
    user_id: str
    avatar_url: str | None = None
    source_template_id: str | None = None
    summary_memory: str | None = None
    
    # Legacy fields (kept for backward compatibility)
    active_template_id: str | None = None
    device_id: str | None = None
    device_mac_address: str | None = None
    
    # Notification channels config
    notification_channels: dict | None = Field(default=None, description="Multi-channel notification config")
    banner_images: list[BannerConfig] | list[dict] | None = Field(default=None, description="List of default banner URLs")
    
    created_at: datetime
    updated_at: datetime


class AgentWebhookRead(AgentRead):
    """Schema for reading agent data with webhook API key (internal use only)."""

    api_key: str | None = Field(
        default=None, description="Unique API key for webhook authentication"
    )


class AgentUpdate(BaseModel):
    """Schema for updating agent data — ALL fields optional."""

    model_config = ConfigDict(extra="ignore")

    agent_name: Annotated[str | None, Field(min_length=1, max_length=255, default=None)]
    description: Annotated[str | None, Field(default=None)]
    status: StatusEnum | None = Field(default=None)
    user_profile: Annotated[str | None, Field(max_length=2000, default=None)]
    chat_history_conf: Annotated[int | None, Field(ge=0, le=50, default=None)] = None
    
    # AI Config fields (all optional for partial update)
    prompt: str | None = Field(default=None)
    ASR: str | None = Field(default=None)
    LLM: str | None = Field(default=None)
    VLLM: str | None = Field(default=None)
    TTS: str | None = Field(default=None)
    tts_voice: str | None = Field(default=None)
    Memory: str | None = Field(default=None)
    Intent: str | None = Field(default=None)
    tools: list | None = Field(default=None)
    enable_memory: bool | None = Field(default=None)
    enable_knowledge_base: bool | None = Field(default=None)
    knowledge_base_ids: list | None = Field(default=None)
    enable_education: bool | None = Field(default=None)
    enable_sales: bool | None = Field(default=None)
    enable_meeting: bool | None = Field(default=None)
    course_ids: list | None = Field(default=None)
    sales_program_ids: list | None = Field(default=None)
    meeting_room_ids: list | None = Field(default=None)
    source_template_id: str | None = Field(default=None)
    summary_memory: str | None = Field(default=None)
    notification_channels: dict | None = Field(default=None)
    banner_images: list[BannerConfig] | list[dict] | None = Field(default=None, description="List of default banner URLs")
    
    # Legacy fields (kept for backward compat)
    active_template_id: str | None = Field(default=None)
    device_id: str | None = Field(default=None)
    device_mac_address: str | None = Field(default=None, max_length=17)


class AgentUpdateInternal(AgentUpdate):
    """Internal schema for updating agent (includes timestamp)."""

    updated_at: datetime


class AgentDelete(BaseModel):
    """Schema for deleting agent (soft delete)."""

    model_config = ConfigDict(extra="forbid")

    is_deleted: bool = Field(default=True, examples=[True])


class BindDeviceByIdRequest(BaseModel):
    """Schema for binding device to agent by ID."""

    model_config = ConfigDict(extra="forbid")

    device_id: Annotated[
        str,
        Field(
            min_length=36,
            max_length=36,
            examples=["550e8400-e29b-41d4-a716-446655440000"],
            description="Device UUID",
        ),
    ]

class BindDeviceRequest(BaseModel):
    """Schema for binding device to agent."""

    model_config = ConfigDict(extra="forbid")

    code: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            examples=["abc123def456"],
            description="Activation code from Redis",
        ),
    ]


class AgentDetailRead(BaseModel):
    """Schema for reading agent with full details."""

    id: str
    user_id: str
    agent_name: str
    description: str
    avatar_url: str | None = None
    status: StatusEnum
    
    # AI Config inline
    prompt: str | None = None
    ASR: str | None = None
    LLM: str | None = None
    VLLM: str | None = None
    TTS: str | None = None
    tts_voice: str | None = None
    Memory: str | None = None
    Intent: str | None = None
    tools: list | None = None
    enable_memory: bool = True
    enable_knowledge_base: bool = True
    knowledge_base_ids: list | None = None
    source_template_id: str | None = None
    notification_channels: dict | None = None
    banner_images: list[BannerConfig] | list[dict] | None = None
    
    # Legacy
    active_template_id: str | None = None
    device_id: str | None = None
    device_mac_address: str | None = None
    
    created_at: datetime
    updated_at: datetime
    device: Optional[dict] = None


class AgentWithDeviceAndTemplatesRead(BaseModel):
    """Schema for reading agent with devices and templates."""

    agent: AgentRead
    device: Optional[DeviceRead] = None  # Legacy: single device
    devices: list[DeviceRead] = Field(default_factory=list)  # Multiple devices
    templates: list = Field(default_factory=list)  # Templates with provider info


# ============ Webhook Schemas ============

class WebhookConfig(BaseModel):
    """Schema for webhook API key response."""

    agent_id: str = Field(examples=["550e8400-e29b-41d4-a716-446655440000"])
    api_key: str | None = Field(
        default=None,
        examples=["dGVzdF9rZXlfdGhhdF9pc19sb25nX2Vub3VnaF9mb3Jfd2Vic29ja2V0X2F1dGg="],
    )

    model_config = ConfigDict(
        json_schema_extra={"description": "Webhook API key configuration"}
    )


class WebhookNotificationPayload(BaseModel):
    """Schema for webhook notification payload."""

    type: Annotated[
        Literal["notification"],
        Field(description="Notification type identifier"),
    ] = "notification"
    useLLM: Annotated[
        bool,
        Field(description="Whether to use LLM for processing"),
    ]
    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=256,
            description="Notification title",
            examples=["System Alert"],
        ),
    ]
    content: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2048,
            description="Notification content",
            examples=["This is a test notification."],
        ),
    ]

    model_config = ConfigDict(
        json_schema_extra={"description": "Webhook notification payload format"}
    )


# ============ MCP Schemas ============

class AgentMCPServerSelectedRead(BaseModel):
    """Schema for reading selected MCP server from agent_mcp_server_selected table."""

    id: str = Field(description="Selected MCP server record ID")
    agent_mcp_selection_id: str = Field(description="Parent selection record ID")
    reference: str = Field(description="MCP reference: 'db:{uuid}' or 'config:{name}'")
    mcp_name: str = Field(description="Resolved MCP server name")
    mcp_type: str = Field(description="MCP transport type: stdio, sse, or http")
    mcp_description: str | None = Field(default=None, description="MCP description")
    source: str = Field(description="MCP source: 'user' or 'config'")
    is_active: bool = Field(default=True, description="Whether MCP is active")
    resolved_at: datetime | None = Field(
        default=None, description="When metadata was last resolved"
    )
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Record update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AgentMCPServerSelectedCreate(BaseModel):
    """Schema for creating selected MCP server record."""

    agent_mcp_selection_id: str = Field(description="Parent selection record ID")
    reference: str = Field(description="MCP reference: 'db:{uuid}' or 'config:{name}'")
    mcp_name: str = Field(description="Resolved MCP server name")
    mcp_type: str = Field(description="MCP transport type: stdio, sse, or http")
    mcp_description: str | None = Field(default=None, description="MCP description")
    source: str = Field(description="MCP source: 'user' or 'config'")
    is_active: bool = Field(default=True, description="Whether MCP is active")
    resolved_at: datetime | None = Field(
        default=None, description="When metadata was last resolved"
    )

    model_config = ConfigDict(extra="forbid")


class AgentMCPSelectionRead(BaseModel):
    """Schema for reading agent MCP selection with all selected servers and metadata."""

    id: str = Field(description="Selection record ID")
    agent_id: str = Field(description="Agent ID")
    mcp_selection_mode: str = Field(description="Selection mode: 'all' or 'selected'")
    servers: list[AgentMCPServerSelectedRead] = Field(
        default_factory=list,
        description="List of selected MCP servers with resolved metadata",
    )
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Record update timestamp")

    model_config = ConfigDict(from_attributes=True)


class AgentMCPSelectionCreate(BaseModel):
    """Schema for creating agent MCP selection."""

    agent_id: str = Field(description="Agent ID")
    mcp_selection_mode: str = Field(
        pattern="^(all|selected)$",
        default="all",
        description="Selection mode: 'all' or 'selected'",
    )

    model_config = ConfigDict(extra="forbid")
