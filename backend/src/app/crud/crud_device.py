"""
CRUD operations for Device model using FastCRUD pattern.

Methods:
- get_device_by_mac_address: Get device by mac_address with optional agent and template joins
- Standard FastCRUD methods: create, get, get_multi, update, delete
"""

from fastcrud import FastCRUD
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


from ..core.logger import get_logger
from ..models.device import Device
from ..schemas.device import (
    DeviceCreate,
    DeviceRead,
    DeviceUpdate,
    DeviceUpdateInternal,
)

logger = get_logger(__name__)


def normalize_mac_address(mac_address: str | None) -> str:
    """Normalize MAC consistently across firmware/OTA/admin flows."""
    return (mac_address or "").strip().upper()


class CRUDDevice(
    FastCRUD[Device, DeviceCreate, DeviceUpdate, DeviceUpdateInternal, None, DeviceRead]
):
    """CRUD operations for Device model using FastCRUD with custom methods."""

    async def _get_device_by_mac_for_user(
        self,
        db: AsyncSession,
        mac_address: str,
        user_id: str | None = None,
    ) -> DeviceRead | None:
        mac_norm = normalize_mac_address(mac_address)
        if not mac_norm:
            return None

        stmt = select(Device).where(func.lower(Device.mac_address) == mac_norm.lower())
        if user_id:
            stmt = stmt.where(Device.user_id == user_id)
        stmt = stmt.order_by(Device.updated_at.desc())

        result = await db.execute(stmt)
        device = result.scalars().first()
        if not device:
            return None
        return DeviceRead.model_validate(device, from_attributes=True)

    async def bind_device_safe(
        self,
        db: AsyncSession,
        mac_address: str,
        user_id: str,
        agent_id: str,
        device_data: dict,
    ) -> DeviceRead:
        """
        Bind device to agent with comprehensive validation.

        Flow:
        1. Check if device exists for this user
        2. If exists: validate not bound to different agent, update it
        3. If not exists: create new device
        4. Return created/updated device

        Args:
            db: AsyncSession
            mac_address: Device MAC address
            user_id: User UUID (owner)
            agent_id: Agent UUID (to bind)
            device_data: dict with device_name, board, firmware_version, status

        Returns:
            DeviceRead: Created or updated device

        Raises:
            ValueError: If device already bound to different agent
        """
        try:
            mac_address = normalize_mac_address(mac_address)
            logger.debug(
                f"Binding device {mac_address} to agent {agent_id} for user {user_id}"
            )

            # Check if device already exists for this user
            existing_device = await self._get_device_by_mac_for_user(
                db=db,
                mac_address=mac_address,
                user_id=user_id,
            )

            if existing_device:
                logger.debug(f"Device exists: {existing_device.id}")
                # Check if bound to another agent
                if existing_device.agent_id and existing_device.agent_id != agent_id:
                    raise ValueError(
                        f"Device is already bound to agent {existing_device.agent_id}"
                    )
                # Update device with agent_id
                from datetime import datetime, timezone

                update_data = DeviceUpdateInternal(
                    agent_id=agent_id,
                    device_name=device_data.get(
                        "device_name", existing_device.device_name
                    ),
                    board=device_data.get("board", existing_device.board),
                    firmware_version=device_data.get(
                        "firmware_version", existing_device.firmware_version
                    ),
                    status=device_data.get("status", existing_device.status),
                    updated_at=datetime.now(timezone.utc),
                )
                device = await self.update(
                    db=db,
                    object=update_data,
                    id=existing_device.id,
                    schema_to_select=DeviceRead,
                    return_as_model=True,
                )
                logger.info(f"Device {device.id} updated with agent_id {agent_id}")
                return device
            else:
                # Create new device
                logger.debug(f"Creating new device for mac {mac_address}")
                device_create = DeviceCreate(
                    mac_address=mac_address,
                    user_id=user_id,
                    agent_id=agent_id,
                    device_name=device_data.get("device_name"),
                    board=device_data.get("board"),
                    firmware_version=device_data.get("firmware_version"),
                    status=device_data.get("status", "active"),
                )
                device = await self.create(
                    db=db,
                    object=device_create,
                    schema_to_select=DeviceRead,
                    return_as_model=True,
                )
                logger.info(
                    f"Device {device.id} created for user {user_id}, agent {agent_id}"
                )
                return device

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to bind device {mac_address}: {str(e)}")
            raise

    async def create_device_from_activation(
        self,
        db: AsyncSession,
        mac_address: str,
        user_id: str,
        device_data: dict,
    ) -> DeviceRead:
        """
        Create or get device from activation without binding to agent.

        Flow:
        1. Check if device exists for this user
        2. If exists: return existing device
        3. If not exists: create new device (no agent binding)

        Args:
            db: AsyncSession
            mac_address: Device MAC address
            user_id: User UUID (owner)
            device_data: dict with device_name, board, firmware_version, status

        Returns:
            DeviceRead: Created or existing device

        Raises:
            ValueError: If validation fails
        """
        try:
            mac_address = normalize_mac_address(mac_address)
            logger.debug(f"Creating device {mac_address} for user {user_id}")

            # Check if device already exists for this user
            existing_device = await self._get_device_by_mac_for_user(
                db=db,
                mac_address=mac_address,
                user_id=user_id,
            )

            if existing_device:
                logger.debug(f"Device already exists: {existing_device.id}")
                return existing_device

            # Create new device without agent binding
            logger.debug(f"Creating new device for mac {mac_address}")
            
            # Extract device info from nested structure if present
            nested_device = device_data.get("device_data", {}) if isinstance(device_data, dict) else {}
            if isinstance(nested_device, dict) and nested_device:
                device_info = nested_device.get("device", {}) if isinstance(nested_device.get("device"), dict) else {}
            else:
                device_info = device_data.get("device", {}) if isinstance(device_data.get("device"), dict) else {}
            
            device_create = DeviceCreate(
                mac_address=mac_address,
                user_id=user_id,
                agent_id=None,  # No agent binding
                device_name=device_info.get("model") or device_data.get("device_name"),
                board=device_info.get("board") or device_data.get("board"),
                firmware_version=device_info.get("app_version") or device_data.get("firmware_version"),
                status=device_data.get("status", "active"),
            )
            device = await self.create(
                db=db,
                object=device_create,
                schema_to_select=DeviceRead,
                return_as_model=True,
            )
            logger.info(f"Device {device.id} created for user {user_id} (no agent)")
            return device

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to create device {mac_address}: {str(e)}")
            raise

    async def get_device_with_agent(
        self,
        db: AsyncSession,
        mac_address: str,
        user_id: str,
    ) -> dict | None:
        """
        Get device with bound agent relation.

        Args:
            db: AsyncSession
            mac_address: Device MAC address
            user_id: User UUID (ownership filter)

        Returns:
            dict: {device: {...}, agent: {...} or None} or None if not found
        """
        try:
            mac_address = normalize_mac_address(mac_address)
            logger.debug(f"Fetching device {mac_address} with agent for user {user_id}")

            from fastcrud import JoinConfig
            from ..models.agent import Agent

            device_with_agent = await self.get_joined(
                db=db,
                joins_config=[
                    JoinConfig(
                        model=Agent,
                        join_on=Device.agent_id == Agent.id,
                        join_type="left",
                    ),
                ],
                nest_joins=True,
                mac_address=mac_address,
                user_id=user_id,  # Ownership filter
            )

            if not device_with_agent:
                logger.debug(f"Device {mac_address} not found for user {user_id}")
                return None

            logger.info(f"Successfully fetched device {mac_address} with agent")
            return device_with_agent

        except Exception as e:
            logger.error(f"Failed to get device {mac_address} with agent: {str(e)}")
            raise

    async def check_device_ownership(
        self,
        db: AsyncSession,
        device_id: str,
        user_id: str,
    ) -> bool:
        """
        Check if device is owned by user.

        Args:
            db: AsyncSession
            device_id: Device UUID
            user_id: User UUID

        Returns:
            bool: True if owned, False otherwise
        """
        try:
            logger.debug(f"Checking ownership of device {device_id} for user {user_id}")

            device = await self.get(
                db=db,
                id=device_id,
                user_id=user_id,
            )

            is_owned = device is not None
            logger.debug(f"Device {device_id} ownership check: {is_owned}")
            return is_owned

        except Exception as e:
            logger.error(f"Failed to check device ownership: {str(e)}")
            return False

    async def get_device_by_mac_address(
        self,
        db: AsyncSession,
        mac_address: str,
        schema_to_select: type = DeviceRead,
        **_ignored_filters,
    ) -> DeviceRead | None:
        """
        Get device by mac_address.

        Args:
            db: AsyncSession for database operations
            mac_address: MAC address to search for
            schema_to_select: Schema for response

        Returns:
            DeviceRead: Device data if found, None otherwise

        Raises:
            Exception: If query fails
        """
        try:
            mac_address = normalize_mac_address(mac_address)
            logger.debug(f"Fetching device with mac_address: {mac_address}")

            if not mac_address:
                return None

            stmt = (
                select(Device)
                .where(func.lower(Device.mac_address) == mac_address.lower())
                .order_by(Device.updated_at.desc())
            )
            result = await db.execute(stmt)
            device_obj = result.scalars().first()
            device = (
                schema_to_select.model_validate(device_obj, from_attributes=True)
                if device_obj and schema_to_select
                else device_obj
            )

            if device:
                logger.debug(f"Device found: {device.id}")
            else:
                logger.debug(f"Device not found with mac_address: {mac_address}")

            return device

        except Exception as e:
            logger.error(f"Failed to get device by mac_address: {str(e)}")
            raise


    async def update_capabilities(
        self,
        db,
        device_id: str | None,
        capabilities: dict,
        updated_at=None,
    ) -> None:
        """Persist firmware-reported capabilities on the device row.

        Called from the WS/MQTT hello handler whenever a device sends its
        `capabilities` block. Idempotent — repeats on every reconnect; we
        store latest. ``device_id`` may be the row id OR the MAC address;
        we accept both for convenience from connection handler context.
        """
        from sqlalchemy import select, update
        if not device_id or not isinstance(capabilities, dict):
            return

        # Try lookup by primary key first; fall back to MAC.
        result = await db.execute(
            select(Device).where(Device.id == device_id)
        )
        device = result.scalar_one_or_none()
        if device is None:
            result = await db.execute(
                select(Device).where(
                    func.lower(Device.mac_address)
                    == normalize_mac_address(device_id).lower()
                )
            )
            device = result.scalar_one_or_none()
        if device is None:
            logger.warning(
                "update_capabilities: device %s not found", device_id
            )
            return

        await db.execute(
            update(Device)
            .where(Device.id == device.id)
            .values(
                capabilities=capabilities,
                capabilities_updated_at=updated_at,
                # Mirror useful fields onto top-level columns so existing
                # admin queries that filter by `board` / `firmware_version`
                # keep working without joining JSON.
                board=capabilities.get("board_type") or device.board,
                firmware_version=(
                    capabilities.get("fw_version") or device.firmware_version
                ),
            )
        )
        await db.commit()


crud_device = CRUDDevice(Device)
