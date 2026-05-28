"""
AgentDeviceAssignment model - Many-to-Many junction table between Agent and Device.

Enables:
- One Agent can be assigned to multiple Devices
- One Device can have multiple Agents assigned
- At any time, a Device has exactly ONE active Agent
- Users can switch the active Agent on a Device

The `is_active` flag determines which Agent is currently active for a Device.
Only one assignment per device can have is_active=True at any time.
"""

from datetime import datetime, timezone
from uuid6 import uuid7

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Boolean,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class AgentDeviceAssignment(Base):
    """Many-to-Many assignment between Agent and Device."""

    __tablename__ = "agent_device_assignment"
    __table_args__ = (
        UniqueConstraint("agent_id", "device_id", name="uq_agent_device"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default_factory=lambda: str(uuid7()), init=False
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agent.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    device_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("device.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Only ONE assignment per device can be active at a time
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )

    # Display order for UI sorting
    display_order: Mapped[int] = mapped_column(
        Integer, default=0
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        init=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        init=False,
    )
