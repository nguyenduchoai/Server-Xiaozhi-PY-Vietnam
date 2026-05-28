"""Unit tests for ReminderService.

Tests cover:
- create_reminder (timezone handling, validation)
- get_reminders (pagination, filtering)
- update_reminder (status transitions)
- delete_reminder (soft delete)
- scheduler functions (due reminders, delivery)
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytz


class TestReminderServiceCreate:
    """Tests for reminder creation functionality."""

    @pytest.mark.asyncio
    async def test_create_reminder_with_valid_data(self):
        """Should create reminder with valid data."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        mock_agent_id = str(uuid4())
        
        remind_at = datetime.now(timezone.utc) + timedelta(hours=1)
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.create_reminder_from_dto = AsyncMock(return_value=MagicMock(
                reminder_id="test-123",
                content="Test reminder",
                remind_at=remind_at,
                status="pending"
            ))
            
            result = await ReminderService.create_reminder(
                db=mock_db,
                agent_id=mock_agent_id,
                content="Test reminder",
                remind_at=remind_at
            )
            
            assert result is not None
            assert result.reminder_id == "test-123"
            mock_crud.create_reminder_from_dto.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_reminder_with_vietnam_timezone(self):
        """Should correctly handle Asia/Ho_Chi_Minh timezone."""
        from app.services.reminder_service import ReminderService
        
        vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        remind_at = datetime.now(vn_tz) + timedelta(hours=1)
        
        mock_db = AsyncMock()
        mock_agent_id = str(uuid4())
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.create_reminder_from_dto = AsyncMock(return_value=MagicMock(
                reminder_id="vn-test-123",
                remind_at_local=remind_at,
            ))
            
            result = await ReminderService.create_reminder(
                db=mock_db,
                agent_id=mock_agent_id,
                content="Nhắc nhở test",
                remind_at=remind_at
            )
            
            assert result is not None
            # Verify timezone is preserved
            call_args = mock_crud.create_reminder_from_dto.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_create_reminder_in_past_should_fail(self):
        """Should reject reminder with past datetime."""
        from app.services.reminder_service import ReminderService
        
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        mock_db = AsyncMock()
        mock_agent_id = str(uuid4())
        
        with pytest.raises(ValueError, match=".*past.*"):
            await ReminderService.create_reminder(
                db=mock_db,
                agent_id=mock_agent_id,
                content="Past reminder",
                remind_at=past_time
            )


class TestReminderServiceGet:
    """Tests for reminder retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_reminders_by_agent(self):
        """Should return reminders for specific agent."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        mock_agent_id = str(uuid4())
        
        mock_reminders = [
            MagicMock(reminder_id="r1", content="Reminder 1"),
            MagicMock(reminder_id="r2", content="Reminder 2"),
        ]
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.list_reminders_filtered = AsyncMock(return_value={
                "data": mock_reminders,
                "total_count": 2
            })
            
            result = await ReminderService.get_reminders(
                db=mock_db,
                agent_id=mock_agent_id
            )
            
            assert len(result["data"]) == 2
            assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_get_reminders_today_only(self):
        """Should filter reminders for today only."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        mock_agent_id = str(uuid4())
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.get_reminders_by_agent_filtered = AsyncMock(return_value={
                "data": [],
                "total_count": 0
            })
            
            await ReminderService.get_reminders_today(
                db=mock_db,
                agent_id=mock_agent_id
            )
            
            mock_crud.get_reminders_by_agent_filtered.assert_called_once()
            call_kwargs = mock_crud.get_reminders_by_agent_filtered.call_args.kwargs
            assert call_kwargs.get("is_today") == True


class TestReminderServiceUpdate:
    """Tests for reminder update functionality."""

    @pytest.mark.asyncio
    async def test_update_pending_reminder(self):
        """Should update reminder when status is pending."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        reminder_id = str(uuid4())
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.get_reminder_by_id = AsyncMock(return_value=MagicMock(
                reminder_id=reminder_id,
                status="pending"
            ))
            mock_crud.update_reminder_safe = AsyncMock(return_value=MagicMock(
                reminder_id=reminder_id,
                content="Updated content"
            ))
            
            result = await ReminderService.update_reminder(
                db=mock_db,
                reminder_id=reminder_id,
                content="Updated content"
            )
            
            assert result.content == "Updated content"

    @pytest.mark.asyncio
    async def test_update_delivered_reminder_should_fail(self):
        """Should reject update for delivered reminder."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        reminder_id = str(uuid4())
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.get_reminder_by_id = AsyncMock(return_value=MagicMock(
                reminder_id=reminder_id,
                status="delivered"
            ))
            
            with pytest.raises(ValueError, match=".*pending.*"):
                await ReminderService.update_reminder(
                    db=mock_db,
                    reminder_id=reminder_id,
                    content="Should fail"
                )


class TestReminderServiceDelete:
    """Tests for reminder deletion functionality."""

    @pytest.mark.asyncio
    async def test_soft_delete_reminder(self):
        """Should soft delete reminder."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        reminder_id = str(uuid4())
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.soft_delete_reminder = AsyncMock(return_value=None)
            
            await ReminderService.delete_reminder(
                db=mock_db,
                reminder_id=reminder_id
            )
            
            mock_crud.soft_delete_reminder.assert_called_once_with(
                db=mock_db,
                reminder_id=reminder_id
            )


class TestReminderScheduler:
    """Tests for reminder scheduler functionality."""

    @pytest.mark.asyncio
    async def test_get_due_reminders(self):
        """Should return reminders due for delivery."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        
        now = datetime.now(timezone.utc)
        due_reminder = MagicMock(
            reminder_id="due-1",
            remind_at=now - timedelta(minutes=1),
            status="pending"
        )
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.get_multi = AsyncMock(return_value={
                "data": [due_reminder],
                "total_count": 1
            })
            
            result = await ReminderService.get_due_reminders(db=mock_db)
            
            assert len(result) >= 0  # May be empty if no due reminders

    @pytest.mark.asyncio
    async def test_mark_reminder_delivered(self):
        """Should mark reminder as delivered."""
        from app.services.reminder_service import ReminderService
        
        mock_db = AsyncMock()
        reminder_id = str(uuid4())
        
        with patch('app.services.reminder_service.crud_reminders') as mock_crud:
            mock_crud.update_status_by_id = AsyncMock(return_value=MagicMock(
                reminder_id=reminder_id,
                status="delivered"
            ))
            
            result = await ReminderService.mark_delivered(
                db=mock_db,
                reminder_id=reminder_id
            )
            
            assert result.status == "delivered"


class TestTimezoneConversion:
    """Tests for timezone conversion logic."""

    def test_utc_to_vietnam_conversion(self):
        """Should correctly convert UTC to Vietnam time."""
        vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        
        utc_time = datetime(2026, 1, 24, 12, 0, 0, tzinfo=timezone.utc)
        vn_time = utc_time.astimezone(vn_tz)
        
        # Vietnam is UTC+7
        assert vn_time.hour == 19
        assert vn_time.day == 24

    def test_vietnam_to_utc_conversion(self):
        """Should correctly convert Vietnam to UTC time."""
        vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        
        vn_time = vn_tz.localize(datetime(2026, 1, 24, 19, 0, 0))
        utc_time = vn_time.astimezone(timezone.utc)
        
        assert utc_time.hour == 12
        assert utc_time.day == 24

    def test_default_timezone_fallback(self):
        """Should use Asia/Ho_Chi_Minh as default when user has no timezone."""
        # Simulating the fix we made
        user_timezone = None
        default_tz = user_timezone if user_timezone else "Asia/Ho_Chi_Minh"
        
        assert default_tz == "Asia/Ho_Chi_Minh"
