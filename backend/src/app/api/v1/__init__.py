"""
Xiaozhi CE (Community Edition) - API Router Registry
Only core features, online-only AI providers.
"""
from fastapi import APIRouter
import logging

# ============ Core Imports ============
from .auth import router as auth_router
from .health import router as health_router
from .reminder import router as reminder_router, reminder_detail_router
from .users import router as users_router
from .ota import router as ota_router
from .vision import router as vision_router
from .websocket import router as websocket_router
from .agent import router as agent_router
from .template import router as template_router
from .config import router as config_router
from .providers import router as providers_router
from .tools import router as tools_router
from .embeddings import router as embeddings_router

from .knowledge_base_chromadb import router as knowledge_base_chromadb_router
from .knowledge_base_pgvector import router as knowledge_base_pgvector_router
from .knowledge_unified import router as knowledge_unified_router
from .mcp_configs import router as mcp_configs_router
from .agent_mcp import router as agent_mcp_router
from .system_mcp import router as system_mcp_router
from .mcp_endpoint import router as mcp_endpoint_router
from .devices import router as devices_router
from .cache import router as cache_router
from .admin import router as admin_router
from .admin_plans import router as admin_plans_router
from .site_settings import router as site_settings_router
from .firmware import router as firmware_router
from .asset_templates import router as asset_templates_router
from .hardware_types import router as hardware_types_router
from .ota_dashboard import router as ota_dashboard_router

# Advanced AI Features
from .memory import router as memory_router
from .marketplace import router as marketplace_router
from .news import router as news_router
from .docs_guide import router as docs_guide_router

# Enhancement Features
from .analytics import router as analytics_router
from .notifications import router as notifications_router

# Notification Channels
from .notification_channels import router as notification_channels_router

# Themes & Boards
from .themes import router as themes_router
from .boards import router as boards_router

# Agent Chat
from .agent_chat import router as agent_chat_router

# Device extended features
from .device_control import router as device_control_router
from .device_display import router as device_display_router
from .device_backgrounds import router as device_backgrounds_router

# Firmware device endpoints (ESP32-facing)
from .firmware_device import router as firmware_device_router

# Server config management
from .server_config import router as server_config_router

# Agent avatars
from .agent_avatar import router as agent_avatar_router
from .avatar_static import router as avatar_static_router

# Agent knowledge bases
from .agent_knowledge_bases import router as agent_knowledge_bases_router

# Knowledge base entries
from .knowledge_bases import router as knowledge_bases_router
from .knowledge_base_entries import router as knowledge_base_entries_router
from .kb_entries import router as kb_entries_router

# Plugins
from .plugins import router as plugins_router


# ============ Optional imports ============

# Device Camera
try:
    from .device_camera import router as device_camera_router
    _device_camera_imported = True
except Exception as e:
    logging.warning(f"Failed to import device_camera: {e}")
    _device_camera_imported = False

# Emoji Pack Feature
try:
    from .emoji_packs import router as emoji_packs_router
    _emoji_packs_imported = True
except Exception as e:
    logging.error(f"Failed to import emoji_packs: {e}")
    _emoji_packs_imported = False


# ============ Register all routers ============
router = APIRouter(prefix="/v1")

# Core
router.include_router(health_router)
router.include_router(auth_router)

# OAuth
from .auth_oauth import router as auth_oauth_router
router.include_router(auth_oauth_router)
router.include_router(users_router)
router.include_router(cache_router)
router.include_router(admin_router)
router.include_router(admin_plans_router)
router.include_router(site_settings_router)

# Reminders
router.include_router(reminder_router)
router.include_router(reminder_detail_router)

# OTA & Firmware
router.include_router(ota_router)
router.include_router(firmware_router)
router.include_router(firmware_device_router)
router.include_router(asset_templates_router)
router.include_router(hardware_types_router)
router.include_router(ota_dashboard_router)
router.include_router(boards_router)

# Communication
router.include_router(vision_router)
router.include_router(websocket_router)

# Agent & Template
router.include_router(agent_router)
router.include_router(agent_mcp_router)
router.include_router(agent_avatar_router)
router.include_router(avatar_static_router)
router.include_router(agent_knowledge_bases_router)
router.include_router(template_router)

# Config & Providers
router.include_router(config_router)
router.include_router(server_config_router)
router.include_router(providers_router)
router.include_router(tools_router)
router.include_router(plugins_router)
router.include_router(embeddings_router)

# Knowledge Base

router.include_router(knowledge_base_chromadb_router)
router.include_router(knowledge_base_pgvector_router)
router.include_router(knowledge_unified_router)
router.include_router(knowledge_bases_router)
router.include_router(knowledge_base_entries_router)
router.include_router(kb_entries_router)

# MCP
router.include_router(mcp_configs_router)
router.include_router(system_mcp_router)
router.include_router(mcp_endpoint_router)

# Devices
router.include_router(devices_router)
router.include_router(device_control_router)
router.include_router(device_display_router)
router.include_router(device_backgrounds_router)

# Device Camera (optional)
if _device_camera_imported:
    router.include_router(device_camera_router)

# Advanced AI Features
router.include_router(memory_router)
router.include_router(marketplace_router)
router.include_router(news_router)

# Themes
router.include_router(themes_router)

# Agent Chat
router.include_router(agent_chat_router)

# Emoji Pack Routes
if _emoji_packs_imported:
    router.include_router(emoji_packs_router)
    logging.info(f"✅ Emoji Pack routes added: {len(emoji_packs_router.routes)} routes")

# Enhancement Features
router.include_router(analytics_router)
router.include_router(notifications_router)

# Notification Channels
router.include_router(notification_channels_router)

# User Connections / Integrations
from .connections import router as connections_router
router.include_router(connections_router)

# System Settings (Super Admin)
from .system_settings import router as system_settings_router
router.include_router(system_settings_router)

# Documentation
router.include_router(docs_guide_router)
