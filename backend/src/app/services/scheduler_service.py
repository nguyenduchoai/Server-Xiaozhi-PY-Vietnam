"""
Scheduler service for periodic background tasks.
Handles scheduling of cleanup jobs and other periodic operations.
"""

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..core.logger import get_logger
from ..core.worker.functions import cleanup_expired_deleted_users
from .device_offline_monitor import run_device_offline_check

logger = get_logger(__name__)

# Suppress verbose APScheduler logs
logging.getLogger("apscheduler").setLevel(logging.WARNING)


class SchedulerService:
    """Service for managing scheduled background tasks."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self._is_running = False

    async def start(self) -> None:
        """Start the scheduler and register jobs."""
        if self._is_running:
            logger.warning("Scheduler đã chạy rồi")
            return

        try:
            self.scheduler = AsyncIOScheduler()

            # Schedule cleanup job to run daily at 3:00 AM
            self.scheduler.add_job(
                self._run_cleanup_job,
                trigger=CronTrigger(hour=3, minute=0),
                id="cleanup_expired_deleted_users",
                name="Cleanup Expired Deleted Users",
                replace_existing=True,
                max_instances=1,  # Prevent concurrent runs
            )

            # Device offline alert daily at 09:00 — sent in the morning
            # (in user-local time roughly) so people see it during their
            # day. Runs separately from subscription maintenance to keep
            # job runtimes small and isolate failures.
            self.scheduler.add_job(
                self._run_device_offline_check,
                trigger=CronTrigger(hour=9, minute=0),
                id="device_offline_alert",
                name="Device Offline Alert (>24h)",
                replace_existing=True,
                max_instances=1,
            )

            self.scheduler.start()
            self._is_running = True
            logger.info("Cleanup scheduler đã khởi động (chạy lúc 3:00 AM hàng ngày)")
            logger.info("Device offline alert scheduler đã khởi động (chạy lúc 09:00 hàng ngày)")

        except Exception as e:
            logger.error(f"Không thể khởi động scheduler: {str(e)}")
            raise

    async def _run_cleanup_job(self) -> None:
        """Wrapper to run cleanup job with proper error handling."""
        try:
            logger.info("Bắt đầu cleanup expired user accounts")

            # Create a mock context object for ARQ compatibility
            class MockContext:
                pass

            ctx = MockContext()
            result = await cleanup_expired_deleted_users(ctx)
            logger.info(f"Cleanup job hoàn thành: {result}")

        except Exception as e:
            logger.error(f"Cleanup job thất bại: {str(e)}")

    async def _run_device_offline_check(self) -> None:
        """Wrapper for the device-offline alert cron."""
        try:
            logger.info("Bắt đầu device offline check")
            await run_device_offline_check()
            logger.info("Device offline check hoàn thành")
        except Exception as e:
            logger.error(f"Device offline check thất bại: {str(e)}")


    async def shutdown(self) -> None:
        """Shutdown the scheduler gracefully."""
        if not self._is_running:
            logger.warning("Scheduler chưa được khởi động")
            return

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)
                self._is_running = False
                logger.info("Scheduler đã shutdown")
        except Exception as e:
            logger.error(f"Lỗi khi shutdown scheduler: {str(e)}")

    async def run_cleanup_now(self) -> str:
        """Manually trigger cleanup job immediately (for testing/admin)."""
        try:
            logger.info("Thực thi cleanup job thủ công")

            class MockContext:
                pass

            ctx = MockContext()
            result = await cleanup_expired_deleted_users(ctx)
            logger.info(f"Cleanup thủ công hoàn thành: {result}")
            return result

        except Exception as e:
            error_msg = f"Cleanup thủ công thất bại: {str(e)}"
            logger.error(error_msg)
            raise

    def add_interval_job(self, func, seconds: int, id: str):
        """Add an interval job to the scheduler."""
        if self.scheduler:
            self.scheduler.add_job(
                func,
                "interval",
                seconds=seconds,
                id=id,
                replace_existing=True,
                max_instances=1,
            )
            logger.info(f"Added interval job: {id} (every {seconds}s)")
        else:
             logger.warning(f"Cannot add job {id}: Scheduler not initialized")


# Global scheduler instance
scheduler_service = SchedulerService()
