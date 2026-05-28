"""
Agent-Device Assignment schemas for Many-to-Many relationship.
"""

from datetime import datetime
from pydantic import BaseModel


class AgentDeviceAssignmentBase(BaseModel):
    """Base schema for agent-device assignment."""
    agent_id: str
    device_id: str
    is_active: bool = False
    display_order: int = 0


class AgentDeviceAssignmentCreate(AgentDeviceAssignmentBase):
    """Schema for creating an assignment."""
    pass


class AgentDeviceAssignmentRead(AgentDeviceAssignmentBase):
    """Schema for reading an assignment."""
    id: str
    created_at: datetime
    updated_at: datetime


class AgentDeviceAssignmentUpdate(BaseModel):
    """Schema for updating an assignment."""
    is_active: bool | None = None
    display_order: int | None = None


class DeviceWithActiveAgent(BaseModel):
    """Schema showing a device with its active agent info."""
    device_id: str
    device_name: str | None = None
    mac_address: str | None = None
    board: str | None = None
    firmware_version: str | None = None
    active_agent_id: str | None = None
    active_agent_name: str | None = None
    assigned_agents_count: int = 0


class AgentForDevice(BaseModel):
    """Schema for an agent assigned to a device (for switch UI)."""
    agent_id: str
    agent_name: str
    description: str = ""
    is_active: bool = False
    display_order: int = 0
    assignment_id: str | None = None
