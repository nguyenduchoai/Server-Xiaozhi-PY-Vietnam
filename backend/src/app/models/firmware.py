"""
Firmware and FirmwareDeployment models for OTA management.

Manages firmware versions and deployments to devices.
"""

from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
import enum

from ..core.db.database import Base


class BoardType(str, enum.Enum):
    """Supported board types for firmware."""
    ESP32 = "esp32"
    ESP32_S3 = "esp32s3"
    ESP32_C3 = "esp32c3"
    ALL = "all"


class DeploymentStatus(str, enum.Enum):
    """Deployment status."""
    PENDING = "pending"
    ROLLING_OUT = "rolling_out"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class DeploymentTargetType(str, enum.Enum):
    """Target type for deployment."""
    ALL = "all"  # All devices
    BOARD = "board"  # By board type
    USER = "user"  # By user_id
    DEVICE = "device"  # Specific device(s)


class Firmware(Base):
    """
    Firmware model - stores firmware versions.
    
    Attributes:
        id: UUID primary key
        version: Semantic version (e.g., "1.0.0")
        board_type: Target board type (esp32, esp32s3, etc.)
        file_path: Path to firmware .bin file
        file_name: Original filename
        checksum: MD5 hash of firmware file
        size: File size in bytes
        release_notes: Description of changes
        is_active: Whether this version is available for OTA
        is_latest: Whether this is the latest version for board_type
        download_count: Number of times downloaded
        created_at: Upload timestamp
        created_by: User who uploaded
    """
    
    __tablename__ = "firmware"
    
    id = Column(String(36), primary_key=True)
    version = Column(String(50), nullable=False, index=True)
    board_type = Column(
        SQLEnum(BoardType, name="board_type_enum"),
        default=BoardType.ALL,
        nullable=False,
        index=True
    )
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    checksum = Column(String(64), nullable=False)  # MD5 or SHA256
    size = Column(Integer, nullable=False)
    release_notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_latest = Column(Boolean, default=False, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    
    # Feature toggles (master switch per firmware)
    # JSON: {"music": true, "radio": true, "weather": true, ...}
    features = Column(JSON, nullable=True, default=None)
    
    # Firmware variant: "common" (default) or custom slug for per-device firmware
    firmware_variant = Column(String(100), default="common", nullable=False)
    # Original custom label for display (e.g., "TIẾN HUY")
    custom_variant_label = Column(String(255), nullable=True, default=None)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(36), ForeignKey("user.id"), nullable=True)
    
    # Relationships
    deployments = relationship("FirmwareDeployment", back_populates="firmware")
    
    def __repr__(self):
        return f"<Firmware {self.version} ({self.board_type})>"


class FirmwareDeployment(Base):
    """
    Firmware deployment model - manages rollouts.
    
    Attributes:
        id: UUID primary key
        firmware_id: Reference to firmware version
        target_type: all/board/user/device
        target_value: Value for target (board_type, user_id, device_mac)
        status: Deployment status
        rollout_percentage: Percentage of targets to deploy (0-100)
        deployed_count: Number of devices that received update
        failed_count: Number of failed deployments
        scheduled_at: When to start deployment (null = immediate)
        started_at: When deployment actually started
        completed_at: When deployment finished
        created_by: User who created deployment
    """
    
    __tablename__ = "firmware_deployment"
    
    id = Column(String(36), primary_key=True)
    firmware_id = Column(String(36), ForeignKey("firmware.id"), nullable=False, index=True)
    
    target_type = Column(
        SQLEnum(DeploymentTargetType, name="deployment_target_type_enum"),
        default=DeploymentTargetType.ALL,
        nullable=False
    )
    target_value = Column(String(255), nullable=True)  # board_type, user_id, or comma-separated device macs
    
    status = Column(
        SQLEnum(DeploymentStatus, name="deployment_status_enum"),
        default=DeploymentStatus.PENDING,
        nullable=False,
        index=True
    )
    rollout_percentage = Column(Integer, default=100, nullable=False)
    
    deployed_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    
    scheduled_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by = Column(String(36), ForeignKey("user.id"), nullable=True)
    
    # Relationships
    firmware = relationship("Firmware", back_populates="deployments")
    
    def __repr__(self):
        return f"<FirmwareDeployment {self.id} - {self.status}>"
