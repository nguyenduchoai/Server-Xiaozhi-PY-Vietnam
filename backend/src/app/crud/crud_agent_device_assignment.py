"""
CRUD operations for Agent-Device Assignment (Many-to-Many).
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.agent_device_assignment import AgentDeviceAssignment
from ..models.agent import Agent
from ..models.device import Device

logger = logging.getLogger(__name__)


async def assign_device_to_agent(
    db: AsyncSession,
    agent_id: str,
    device_id: str,
    set_active: bool = False,
) -> AgentDeviceAssignment:
    """
    Assign a device to an agent (create M2M link).
    
    If set_active=True, deactivate all other assignments for this device first.
    """
    # Check if assignment already exists
    existing = await db.execute(
        select(AgentDeviceAssignment).where(
            and_(
                AgentDeviceAssignment.agent_id == agent_id,
                AgentDeviceAssignment.device_id == device_id,
            )
        )
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row:
        if set_active and not existing_row.is_active:
            await switch_active_agent(db, device_id, agent_id)
        return existing_row

    if set_active:
        # Deactivate all other assignments for this device
        await db.execute(
            update(AgentDeviceAssignment)
            .where(AgentDeviceAssignment.device_id == device_id)
            .values(is_active=False)
        )

    # Get current max display_order for device
    result = await db.execute(
        select(func.max(AgentDeviceAssignment.display_order)).where(
            AgentDeviceAssignment.device_id == device_id
        )
    )
    max_order = result.scalar() or 0

    assignment = AgentDeviceAssignment(
        agent_id=agent_id,
        device_id=device_id,
        is_active=set_active,
        display_order=max_order + 1,
    )
    db.add(assignment)
    await db.flush()

    # Sync legacy FK if active
    if set_active:
        await _sync_legacy_fk(db, agent_id, device_id)

    logger.info(f"Assigned device {device_id} to agent {agent_id} (active={set_active})")
    return assignment


async def unassign_device_from_agent(
    db: AsyncSession,
    agent_id: str,
    device_id: str,
) -> bool:
    """Remove device-agent assignment. Returns True if was found and deleted."""
    result = await db.execute(
        select(AgentDeviceAssignment).where(
            and_(
                AgentDeviceAssignment.agent_id == agent_id,
                AgentDeviceAssignment.device_id == device_id,
            )
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return False

    was_active = assignment.is_active
    await db.delete(assignment)
    await db.flush()

    # If the removed assignment was active, activate the next available one
    if was_active:
        next_result = await db.execute(
            select(AgentDeviceAssignment)
            .where(AgentDeviceAssignment.device_id == device_id)
            .order_by(AgentDeviceAssignment.display_order.asc())
            .limit(1)
        )
        next_assignment = next_result.scalar_one_or_none()
        if next_assignment:
            next_assignment.is_active = True
            await _sync_legacy_fk(db, next_assignment.agent_id, device_id)
        else:
            # No more agents assigned, clear legacy FK
            await db.execute(
                update(Device)
                .where(Device.id == device_id)
                .values(agent_id=None)
            )
            await db.execute(
                update(Agent)
                .where(and_(Agent.device_id == device_id, Agent.id == agent_id))
                .values(device_id=None, device_mac_address=None)
            )

    logger.info(f"Unassigned device {device_id} from agent {agent_id}")
    return True


async def switch_active_agent(
    db: AsyncSession,
    device_id: str,
    agent_id: str,
) -> AgentDeviceAssignment | None:
    """
    Switch the active agent for a device.
    
    Deactivates current active agent, activates the specified one.
    The assignment must already exist.
    """
    # Verify assignment exists
    result = await db.execute(
        select(AgentDeviceAssignment).where(
            and_(
                AgentDeviceAssignment.agent_id == agent_id,
                AgentDeviceAssignment.device_id == device_id,
            )
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        return None

    # Deactivate all assignments for this device
    await db.execute(
        update(AgentDeviceAssignment)
        .where(AgentDeviceAssignment.device_id == device_id)
        .values(is_active=False)
    )

    # Activate the target
    assignment.is_active = True
    assignment.updated_at = datetime.now(timezone.utc)
    await db.flush()

    # Sync legacy FK
    await _sync_legacy_fk(db, agent_id, device_id)

    logger.info(f"Switched device {device_id} to agent {agent_id}")
    return assignment


async def get_agents_for_device(
    db: AsyncSession,
    device_id: str,
) -> list[dict]:
    """
    Get all agents assigned to a device, with active flag.
    Returns list of dicts with agent info, including soft-deleted ones.
    """
    result = await db.execute(
        select(
            AgentDeviceAssignment.id.label("assignment_id"),
            AgentDeviceAssignment.is_active,
            AgentDeviceAssignment.display_order,
            AgentDeviceAssignment.created_at.label("assigned_date"),
            Agent.id.label("agent_id"),
            Agent.agent_name,
            Agent.description,
            Agent.is_deleted,
        )
        .join(Agent, Agent.id == AgentDeviceAssignment.agent_id)
        .where(
            AgentDeviceAssignment.device_id == device_id
        )
        .order_by(AgentDeviceAssignment.display_order.asc())
    )
    rows = result.all()
    
    agents = []
    for row in rows:
        # Xử lý logic agent_status
        if row.is_deleted:
            agent_status = "deleted"
        elif row.is_active:
            agent_status = "active"
        else:
            agent_status = "inactive"
            
        agents.append({
            "assignment_id": row.assignment_id,
            "agent_id": row.agent_id,
            "agent_name": row.agent_name,
            "description": row.description or "",
            "is_active": row.is_active,
            "display_order": row.display_order,
            "assigned_date": row.assigned_date.isoformat() if row.assigned_date else None,
            "agent_status": agent_status,
        })
        
    return agents


async def get_devices_for_agent(
    db: AsyncSession,
    agent_id: str,
) -> list[dict]:
    """
    Get all devices assigned to an agent.
    """
    result = await db.execute(
        select(
            AgentDeviceAssignment.id.label("assignment_id"),
            AgentDeviceAssignment.is_active,
            AgentDeviceAssignment.display_order,
            Device.id.label("device_id"),
            Device.device_name,
            Device.mac_address,
            Device.board,
            Device.firmware_version,
        )
        .join(Device, Device.id == AgentDeviceAssignment.device_id)
        .where(AgentDeviceAssignment.agent_id == agent_id)
        .order_by(AgentDeviceAssignment.display_order.asc())
    )
    rows = result.all()
    return [
        {
            "assignment_id": row.assignment_id,
            "device_id": row.device_id,
            "device_name": row.device_name,
            "mac_address": row.mac_address,
            "board": row.board,
            "firmware_version": row.firmware_version,
            "is_active": row.is_active,
            "display_order": row.display_order,
        }
        for row in rows
    ]


async def get_active_agent_for_device(
    db: AsyncSession,
    device_id: str,
) -> str | None:
    """Get the active agent_id for a device, or None."""
    result = await db.execute(
        select(AgentDeviceAssignment.agent_id).where(
            and_(
                AgentDeviceAssignment.device_id == device_id,
                AgentDeviceAssignment.is_active == True,
            )
        )
    )
    row = result.scalar_one_or_none()
    return row


async def get_assignment(
    db: AsyncSession,
    agent_id: str,
    device_id: str,
) -> AgentDeviceAssignment | None:
    """Get a specific assignment."""
    result = await db.execute(
        select(AgentDeviceAssignment).where(
            and_(
                AgentDeviceAssignment.agent_id == agent_id,
                AgentDeviceAssignment.device_id == device_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def _sync_legacy_fk(
    db: AsyncSession,
    agent_id: str,
    device_id: str,
) -> None:
    """
    Sync legacy device.agent_id and agent.device_id FKs for backward compatibility.
    
    This ensures the old 1:1 relationship still works while we transition
    to the new M2M model.
    """
    # Get device details
    device_result = await db.execute(
        select(Device).where(Device.id == device_id)
    )
    device = device_result.scalar_one_or_none()
    if not device:
        return

    # Update device.agent_id
    await db.execute(
        update(Device)
        .where(Device.id == device_id)
        .values(agent_id=agent_id)
    )

    # Update agent.device_id and agent.device_mac_address
    await db.execute(
        update(Agent)
        .where(Agent.id == agent_id)
        .values(
            device_id=device_id,
            device_mac_address=device.mac_address,
        )
    )

    logger.debug(f"Synced legacy FK: device={device_id} ↔ agent={agent_id}")
