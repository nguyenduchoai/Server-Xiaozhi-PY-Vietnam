from fastapi import APIRouter

from ..api.v1 import router as v1_router
from ..api.v1.ota import router as ota_router
from ..api.v1.websocket import router as websocket_router

router = APIRouter(prefix="/api")
router.include_router(v1_router)

# Add shortcut route /api/ota -> same as /api/v1/ota for firmware compatibility
router.include_router(ota_router, tags=["ota"])

# ============================================================
# Root-level compatibility routes for old firmware
# Standard protocol paths:
#   OTA:       POST /ota/           (Java manager-api: @RequestMapping("/ota/"))
#   WebSocket: ws://server:port/    (Python server: root path)
#   OTA:       POST /xiaozhi/ota/   (alternative path)
#   WebSocket: ws://server:port/xiaozhi/websocket  (alternative path)
# ============================================================

# Root-level routes (outside /api prefix)
# Mounted at app level in main.py
root_websocket_router = APIRouter()
root_websocket_router.include_router(websocket_router)         # ws://host/ws, ws://host/
root_websocket_router.include_router(ota_router, tags=["ota-root"])  # POST /ota, /ota/

# Legacy /xiaozhi/ prefix routes for original firmware compatibility
legacy_router = APIRouter(prefix="/xiaozhi")
legacy_router.include_router(ota_router, tags=["ota-legacy"])     # POST /xiaozhi/ota
legacy_router.include_router(websocket_router, tags=["ws-legacy"])  # ws://host/xiaozhi/ws

