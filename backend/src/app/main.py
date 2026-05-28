"""
Xiaozhi CE (Community Edition) - Application Entry Point
Simplified: Online-only providers, no local ASR/TTS, no sales/edu/meeting.
"""
import asyncio
import inspect
import os
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from .api import router, root_websocket_router, legacy_router
from .config import Settings, load_config
from .core.auth import AuthManager
from .core.config import EnvironmentOption, settings
from .core.logger import setup_logging
from .ai.module_factory import initialize_modules
from .core.setup import create_application, lifespan_factory
from .core.uvicorn_config import setup_uvicorn_logging
from .services import (
    ThreadPoolService,
    ReminderService,
    scheduler_service,
    MQTTService,
    seed_default_hardware_types,
)
from .services.mqtt_presence_tracker import init_presence_tracker
from .services.udp_audio_server import UdpAudioServer
from .services.mqtt_device_handler import MqttDeviceProtocolHandler, set_mqtt_device_handler
from .core.db.database import local_session

# Thiết lập logging từ đầu
setup_logging()
setup_uvicorn_logging()

# Initialize Sentry error tracking (if SENTRY_DSN is configured)
try:
    from app.core.sentry import init_sentry
    init_sentry()
except Exception:
    pass  # Sentry is optional

# Initialize comprehensive exception handlers
from app.core.exceptions import register_exception_handlers


def _public_metrics_enabled() -> bool:
    value = os.getenv("ENABLE_PUBLIC_METRICS", "").strip().lower()
    if value:
        return value in {"1", "true", "yes", "on"}
    return getattr(settings, "ENVIRONMENT", None) != EnvironmentOption.PRODUCTION


# Khởi tạo Prometheus Instrumentator (lazy expose)
prometheus_instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,  # Always enable metrics
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/api/v1/health", "/metrics"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)


async def startup_realtime_components(app: FastAPI) -> None:
    """Khởi tạo ThreadPool, AuthManager, và các mô-đun realtime."""
    logger = setup_logging().bind(tag=__name__)

    raw_config = load_config()
    module_settings = Settings.from_dict(raw_config)
    app.state.config = module_settings

    max_workers = raw_config.get("thread_pool", {}).get("max_workers", 10)
    app.state.thread_pool = ThreadPoolService(max_workers=max_workers)
    app.state.active_connections = set()
    app.state.modules = {}
    app.state.auth_manager = None
    app.state.reminder_service = None
    app.state.mqtt_service = None

    if module_settings.auth.enabled:
        try:
            app.state.auth_manager = AuthManager(
                secret_key=module_settings.server.auth_key,
                expire_seconds=module_settings.auth.expire_seconds,
            )
            logger.info("[Startup] AuthManager initialized (auth enabled)")
        except Exception as exc:
            logger.warning(f"[Startup] Failed to initialize AuthManager: {exc}")
            app.state.auth_manager = None
    else:
        logger.debug("[Startup] Auth disabled")

    # Initialize MQTT service
    try:
        mqtt_service = MQTTService.from_config(module_settings.mqtt)
        await mqtt_service.start()
        app.state.mqtt_service = mqtt_service
        if mqtt_service.is_available():
            logger.info("[Startup] MQTT service initialized")
        else:
            logger.debug("[Startup] MQTT service running in degraded mode (no config)")
    except Exception as exc:
        logger.warning(f"[Startup] Failed to initialize MQTT service: {exc}")
        app.state.mqtt_service = None

    try:
        modules = await initialize_modules(
            thread_pool=app.state.thread_pool,
            config=module_settings,
        )
        app.state.modules = modules
        logger.info(f"[Startup] Modules initialized: {list(modules.keys())}")
    except Exception as exc:
        logger.error(f"[Startup] Module initialization failed: {exc}")
        traceback.print_exc()
        app.state.modules = {}

    try:
        reminder_service = ReminderService(
            reminder_config=module_settings.reminder,
            server_config=module_settings.server,
            mqtt_service=app.state.mqtt_service,
        )
        reminder_service.init_app(app)
        app.state.reminder_service = reminder_service
        logger.info("[Startup] Reminder service initialized")
    except Exception as exc:
        logger.warning(f"[Startup] Failed to initialize Reminder service: {exc}")
        app.state.reminder_service = None

    # Initialize scheduler service for cleanup jobs
    try:
        await scheduler_service.start()
        app.state.scheduler_service = scheduler_service
        logger.info("[Startup] Cleanup scheduler service started")
    except Exception as exc:
        logger.warning(f"[Startup] Cannot start scheduler service: {exc}")
        app.state.scheduler_service = None

    # Seed default hardware types (board types, screen types)
    try:
        async with local_session() as db:
            await seed_default_hardware_types(db)
        logger.info("[Startup] Hardware types seeding completed")
    except Exception as exc:
        logger.warning(f"[Startup] Failed to seed hardware types: {exc}")

    # Initialize MQTT presence tracker
    try:
        presence_tracker = await init_presence_tracker()
        app.state.presence_tracker = presence_tracker
        logger.info("[Startup] MQTT presence tracker initialized")

        # Initialize Idle Banner Manager
        from app.services.idle_banner_manager import IdleBannerManager, set_idle_banner_manager
        if app.state.mqtt_service:
            idle_banner_mgr = IdleBannerManager(app.state.mqtt_service)
            await idle_banner_mgr.start()
            set_idle_banner_manager(idle_banner_mgr)
            app.state.idle_banner_manager = idle_banner_mgr
            logger.info("[Startup] Idle Banner Manager initialized")
    except Exception as exc:
        logger.warning(f"[Startup] Failed to initialize presence tracker or banner manager: {exc}")
        app.state.presence_tracker = None

    # Initialize UDP Audio Server for MQTT protocol devices
    try:
        udp_port = raw_config.get("udp_audio", {}).get("port", 8765)
        udp_public_ip = raw_config.get("udp_audio", {}).get("public_ip")

        udp_server = UdpAudioServer(
            host="0.0.0.0",
            port=udp_port,
            public_ip=udp_public_ip,
        )
        await udp_server.start()
        app.state.udp_audio_server = udp_server
        logger.info(f"[Startup] UDP Audio Server started on port {udp_port}")
    except Exception as exc:
        logger.warning(f"[Startup] Failed to start UDP Audio Server: {exc}")
        app.state.udp_audio_server = None

    # Initialize MQTT Device Protocol Handler (for MQTT-based devices)
    try:
        mqtt_service = app.state.mqtt_service
        udp_server = app.state.udp_audio_server
        modules = app.state.modules or {}

        if mqtt_service and mqtt_service.is_available() and udp_server:
            mqtt_device_handler = MqttDeviceProtocolHandler(
                mqtt_service=mqtt_service,
                udp_server=udp_server,
                subscribe_topic="device-server",
                config=raw_config,
                thread_pool=app.state.thread_pool,
                vad=modules.get("vad"),
                asr=modules.get("asr"),
                llm=modules.get("llm"),
                memory=modules.get("memory"),
                intent=modules.get("intent"),
                agent_service=None,
            )
            await mqtt_device_handler.start()
            app.state.mqtt_device_handler = mqtt_device_handler
            set_mqtt_device_handler(mqtt_device_handler)
            logger.info("[Startup] MQTT Device Protocol Handler initialized with audio pipeline")
        else:
            logger.debug("[Startup] MQTT Device Handler not started (MQTT or UDP not available)")
            app.state.mqtt_device_handler = None
    except Exception as exc:
        logger.warning(f"[Startup] Failed to initialize MQTT Device Handler: {exc}")
        app.state.mqtt_device_handler = None


async def shutdown_realtime_components(app: FastAPI) -> None:
    """Giải phóng tài nguyên realtime khi shutdown."""
    logger = setup_logging().bind(tag=__name__)

    modules = getattr(app.state, "modules", {}) or {}
    thread_pool: ThreadPoolService | None = getattr(app.state, "thread_pool", None)
    reminder_service: ReminderService | None = getattr(
        app.state, "reminder_service", None
    )
    scheduler_service_instance = getattr(app.state, "scheduler_service", None)
    mqtt_service: MQTTService | None = getattr(app.state, "mqtt_service", None)

    # Shutdown scheduler service first
    if scheduler_service_instance:
        try:
            await scheduler_service_instance.shutdown()
            logger.info("[Shutdown] Cleanup scheduler shutdown")
        except Exception as exc:
            logger.warning(f"[Shutdown] Error shutting down scheduler service: {exc}")

    # Shutdown reminder service
    if reminder_service:
        try:
            await reminder_service.shutdown()
            logger.info("[Shutdown] Reminder service shutdown completed")
        except Exception as exc:
            logger.warning(f"[Shutdown] Error shutting down reminder service: {exc}")

    idle_banner_manager = getattr(app.state, "idle_banner_manager", None)
    if idle_banner_manager:
        try:
            await idle_banner_manager.stop()
        except:
            pass

    # Shutdown MQTT service
    if mqtt_service:
        try:
            await mqtt_service.shutdown()
            logger.info("[Shutdown] MQTT service shutdown completed")
        except Exception as exc:
            logger.warning(f"[Shutdown] Error shutting down MQTT service: {exc}")

    # Close modules
    for module_name, module in modules.items():
        close_callable = getattr(module, "close", None)
        if not close_callable:
            continue
        try:
            if inspect.iscoroutinefunction(close_callable) or hasattr(
                close_callable, "__await__"
            ):
                await close_callable()
            elif thread_pool:
                await thread_pool.run_blocking(close_callable)
            else:
                close_callable()
            logger.info(f"[Shutdown] Closed module: {module_name}")
        except Exception as exc:
            logger.warning(f"[Shutdown] Error closing module {module_name}: {exc}")

    # Shutdown ThreadPool
    if thread_pool:
        thread_pool.shutdown(wait=True)
        logger.info("[Shutdown] ThreadPool shutdown completed")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Custom lifespan for the application."""
    default_lifespan = lifespan_factory(settings)

    async with default_lifespan(app):
        await startup_realtime_components(app)
        try:
            yield
        finally:
            await shutdown_realtime_components(app)


app = create_application(router=router, settings=settings, lifespan=lifespan)

# Mount root-level compatibility routes for old firmware
app.include_router(root_websocket_router)
# Old firmware OTA: POST /xiaozhi/ota/ instead of /api/v1/ota
app.include_router(legacy_router)

# Register comprehensive exception handlers for consistent error responses
register_exception_handlers(app)

# Add Rate Limiting Middleware
try:
    from app.middleware.rate_limit import RateLimitMiddleware
    from app.core.cache import cache
    app.add_middleware(RateLimitMiddleware, redis_client=getattr(cache, 'pool', None))
except Exception as e:
    logger = setup_logging().bind(tag=__name__)
    logger.warning(f"Rate limiting middleware not loaded: {e}")

# Expose Prometheus metrics only when explicitly enabled in production.
if _public_metrics_enabled():
    prometheus_instrumentator.instrument(app).expose(
        app,
        include_in_schema=False,
        should_gzip=True,
    )

# Mount static files for knowledge image uploads
try:
    from starlette.staticfiles import StaticFiles
    import os
    uploads_dir = os.environ.get("UPLOADS_DIR", "/app/data/uploads")
    os.makedirs(f"{uploads_dir}/knowledge/images", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    logger = setup_logging().bind(tag=__name__)
    logger.info(f"[Startup] Static files mounted at /uploads")
except Exception as e:
    logger = setup_logging().bind(tag=__name__)
    logger.warning(f"Static files mount failed: {e}")
