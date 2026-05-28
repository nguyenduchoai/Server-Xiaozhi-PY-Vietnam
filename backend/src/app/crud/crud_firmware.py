"""
CRUD operations for Firmware and FirmwareDeployment.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from uuid import uuid4

from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.firmware import (
    Firmware,
    FirmwareDeployment,
    BoardType,
    DeploymentStatus,
    DeploymentTargetType,
)
from ..schemas.firmware import (
    FirmwareCreate,
    FirmwareUpdate,
    DeploymentCreate,
    DeploymentUpdate,
)
from ..core.logger import get_logger

logger = get_logger(__name__)

# Firmware storage path
FIRMWARE_STORAGE_PATH = Path("/app/data/firmware")


class CRUDFirmware:
    """CRUD operations for Firmware."""
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: FirmwareCreate,
        file_path: str,
        file_name: str,
        checksum: str,
        size: int,
        created_by: Optional[str] = None,
    ) -> Firmware:
        """Create new firmware entry."""
        firmware_id = str(uuid4())
        
        # Check if should be marked as latest
        is_latest = await self._should_be_latest(db, obj_in.board_type, obj_in.version)
        
        # If this is latest, unset previous latest
        if is_latest:
            await self._unset_latest(db, obj_in.board_type)
        
        db_obj = Firmware(
            id=firmware_id,
            version=obj_in.version,
            board_type=obj_in.board_type,
            file_path=file_path,
            file_name=file_name,
            checksum=checksum,
            size=size,
            release_notes=obj_in.release_notes,
            is_active=obj_in.is_active,
            is_latest=is_latest,
            created_by=created_by,
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        logger.info(f"Created firmware {obj_in.version} for {obj_in.board_type}")
        return db_obj
    
    async def get(self, db: AsyncSession, id: str) -> Optional[Firmware]:
        """Get firmware by ID."""
        result = await db.execute(select(Firmware).where(Firmware.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_version(
        self,
        db: AsyncSession,
        version: str,
        board_type: Optional[BoardType] = None,
    ) -> Optional[Firmware]:
        """Get firmware by version and optionally board type."""
        query = select(Firmware).where(Firmware.version == version)
        if board_type:
            query = query.where(Firmware.board_type == board_type)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_latest(
        self,
        db: AsyncSession,
        board_type: BoardType,
        variant: Optional[str] = None,
    ) -> Optional[Firmware]:
        """Get latest active firmware for board type, optionally filtered by variant."""
        conditions = [
            Firmware.board_type == board_type,
            Firmware.is_active == True,
            Firmware.is_latest == True,
        ]
        if variant:
            conditions.append(Firmware.firmware_variant == variant)
        
        # First try exact board type
        result = await db.execute(
            select(Firmware).where(and_(*conditions))
        )
        firmware = result.scalar_one_or_none()
        
        # Fallback to "all" board type
        if not firmware:
            conditions_all = [
                Firmware.board_type == BoardType.ALL,
                Firmware.is_active == True,
                Firmware.is_latest == True,
            ]
            if variant:
                conditions_all.append(Firmware.firmware_variant == variant)
            
            result = await db.execute(
                select(Firmware).where(and_(*conditions_all))
            )
            firmware = result.scalar_one_or_none()
        
        return firmware
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        board_type: Optional[BoardType] = None,
        is_active: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Get list of firmwares with pagination."""
        query = select(Firmware)
        count_query = select(func.count(Firmware.id))
        
        if board_type:
            query = query.where(Firmware.board_type == board_type)
            count_query = count_query.where(Firmware.board_type == board_type)
        
        if is_active is not None:
            query = query.where(Firmware.is_active == is_active)
            count_query = count_query.where(Firmware.is_active == is_active)
        
        query = query.order_by(Firmware.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        return {
            "data": result.scalars().all(),
            "total_count": count_result.scalar_one(),
        }
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Firmware,
        obj_in: FirmwareUpdate,
    ) -> Firmware:
        """Update firmware metadata."""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # Handle is_latest change
        if update_data.get("is_latest") is True:
            await self._unset_latest(db, db_obj.board_type)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_obj)
        
        return db_obj
    
    async def delete(self, db: AsyncSession, *, id: str) -> bool:
        """Delete firmware (soft delete by setting is_active=False)."""
        firmware = await self.get(db, id)
        if not firmware:
            return False
        
        firmware.is_active = False
        firmware.is_latest = False
        await db.commit()
        
        logger.info(f"Deactivated firmware {firmware.version}")
        return True
    
    async def increment_download_count(self, db: AsyncSession, id: str) -> None:
        """Increment download count for firmware."""
        await db.execute(
            update(Firmware)
            .where(Firmware.id == id)
            .values(download_count=Firmware.download_count + 1)
        )
        await db.commit()
    
    async def _should_be_latest(
        self,
        db: AsyncSession,
        board_type: BoardType,
        version: str,
    ) -> bool:
        """Check if this version should be marked as latest."""
        # Simple logic: new uploads are latest unless there's a newer version
        # In production, you might want semver comparison
        return True
    
    async def _unset_latest(self, db: AsyncSession, board_type: BoardType) -> None:
        """Unset is_latest for all firmwares of this board type."""
        await db.execute(
            update(Firmware)
            .where(
                or_(
                    Firmware.board_type == board_type,
                    Firmware.board_type == BoardType.ALL,
                )
            )
            .values(is_latest=False)
        )


class CRUDFirmwareDeployment:
    """CRUD operations for FirmwareDeployment."""
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: DeploymentCreate,
        created_by: Optional[str] = None,
    ) -> FirmwareDeployment:
        """Create new deployment."""
        deployment_id = str(uuid4())
        
        status = DeploymentStatus.PENDING
        started_at = None
        
        # Start immediately if not scheduled
        if not obj_in.scheduled_at:
            status = DeploymentStatus.ROLLING_OUT
            started_at = datetime.utcnow()
        
        db_obj = FirmwareDeployment(
            id=deployment_id,
            firmware_id=obj_in.firmware_id,
            target_type=obj_in.target_type,
            target_value=obj_in.target_value,
            rollout_percentage=obj_in.rollout_percentage,
            scheduled_at=obj_in.scheduled_at,
            status=status,
            started_at=started_at,
            created_by=created_by,
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        logger.info(f"Created deployment {deployment_id} for firmware {obj_in.firmware_id}")
        return db_obj
    
    async def get(
        self,
        db: AsyncSession,
        id: str,
    ) -> Optional[FirmwareDeployment]:
        """Get deployment by ID with firmware info."""
        result = await db.execute(
            select(FirmwareDeployment)
            .options(selectinload(FirmwareDeployment.firmware))
            .where(FirmwareDeployment.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[DeploymentStatus] = None,
        firmware_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get list of deployments with pagination."""
        query = (
            select(FirmwareDeployment)
            .options(selectinload(FirmwareDeployment.firmware))
        )
        count_query = select(func.count(FirmwareDeployment.id))
        
        if status:
            query = query.where(FirmwareDeployment.status == status)
            count_query = count_query.where(FirmwareDeployment.status == status)
        
        if firmware_id:
            query = query.where(FirmwareDeployment.firmware_id == firmware_id)
            count_query = count_query.where(FirmwareDeployment.firmware_id == firmware_id)
        
        query = query.order_by(FirmwareDeployment.created_at.desc()).offset(skip).limit(limit)
        
        result = await db.execute(query)
        count_result = await db.execute(count_query)
        
        return {
            "data": result.scalars().all(),
            "total_count": count_result.scalar_one(),
        }
    
    async def get_active_for_device(
        self,
        db: AsyncSession,
        *,
        mac_address: str,
        board_type: str,
        user_id: Optional[str] = None,
    ) -> Optional[FirmwareDeployment]:
        """Get active deployment targeting this device."""
        # Check deployments in order of specificity
        conditions = [
            # Specific device
            and_(
                FirmwareDeployment.target_type == DeploymentTargetType.DEVICE,
                FirmwareDeployment.target_value.contains(mac_address),
            ),
        ]
        
        if user_id:
            conditions.append(
                and_(
                    FirmwareDeployment.target_type == DeploymentTargetType.USER,
                    FirmwareDeployment.target_value == user_id,
                )
            )
        
        # Board type
        conditions.append(
            and_(
                FirmwareDeployment.target_type == DeploymentTargetType.BOARD,
                FirmwareDeployment.target_value == board_type,
            )
        )
        
        # All devices
        conditions.append(
            FirmwareDeployment.target_type == DeploymentTargetType.ALL,
        )
        
        result = await db.execute(
            select(FirmwareDeployment)
            .options(selectinload(FirmwareDeployment.firmware))
            .where(
                and_(
                    FirmwareDeployment.status == DeploymentStatus.ROLLING_OUT,
                    or_(*conditions),
                )
            )
            .order_by(FirmwareDeployment.created_at.desc())
            .limit(1)
        )
        
        return result.scalar_one_or_none()
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: FirmwareDeployment,
        obj_in: DeploymentUpdate,
    ) -> FirmwareDeployment:
        """Update deployment."""
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        # Handle status changes
        if obj_in.status == DeploymentStatus.COMPLETED:
            db_obj.completed_at = datetime.utcnow()
        elif obj_in.status == DeploymentStatus.ROLLING_OUT and not db_obj.started_at:
            db_obj.started_at = datetime.utcnow()
        
        db_obj.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_obj)
        
        return db_obj
    
    async def increment_deployed(self, db: AsyncSession, id: str) -> None:
        """Increment deployed count."""
        await db.execute(
            update(FirmwareDeployment)
            .where(FirmwareDeployment.id == id)
            .values(deployed_count=FirmwareDeployment.deployed_count + 1)
        )
        await db.commit()
    
    async def increment_failed(self, db: AsyncSession, id: str) -> None:
        """Increment failed count."""
        await db.execute(
            update(FirmwareDeployment)
            .where(FirmwareDeployment.id == id)
            .values(failed_count=FirmwareDeployment.failed_count + 1)
        )
        await db.commit()


# Singleton instances
crud_firmware = CRUDFirmware()
crud_firmware_deployment = CRUDFirmwareDeployment()
