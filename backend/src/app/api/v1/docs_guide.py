"""
Documentation API Endpoints

Serves project documentation and feature guides.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

import httpx

router = APIRouter(prefix="/docs-guide", tags=["documentation"])


# Documentation content
DOCS_CONTENT = {
    "byo_policy": {
        "title": "BYO Provider Setup",
        "description": "Bring Your Own Key - Tự cung cấp API keys cho các dịch vụ AI",
        "content": """
## BYO (Bring Your Own) Policy

### Tổng quan
BYO là chính sách yêu cầu users tự cung cấp API keys cho các dịch vụ trả phí.

### Nguyên tắc

| Service Type | Policy |
|--------------|--------|
| **LLM** | ⚠️ BYO bắt buộc |
| **TTS (trả phí)** | ⚠️ BYO bắt buộc |
| **TTS (miễn phí)** | ✅ Có sẵn |
| **ASR (trả phí)** | ⚠️ BYO bắt buộc |
| **ASR (miễn phí)** | ✅ Có sẵn |

### Free Services Available
- **TTS**: Edge TTS, Sherpa ONNX Vietnamese, Valtec
- **ASR**: Qwen3 ASR (0.6B), Sherpa ONNX, Chunkformer
        """
    },
    "tts_providers": {
        "title": "TTS Providers",
        "description": "Text-to-Speech services với giọng tiếng Việt",
        "content": """
## TTS Providers

### Free Options

#### 1. Edge TTS (Microsoft)
- Type: `edge`
- Quality: Tốt
- Latency: Thấp
- Voice: `vi-VN-HoaiMyNeural`

#### 2. Valtec TTS v2.0 (Local GPU/CPU)
- Type: `valtec`
- Port: 8101
- Quality: 22-24kHz
- Features: Multi-Speaker 5 voices (NF/SF/NM1/SM/NM2), Zero-Shot Voice Cloning (6 reference voices)
- Params: 74.8M, 3-4x realtime on CPU

        """
    },
    "admin_management": {
        "title": "Admin Role Management",
        "description": "Quản lý users, subscriptions và payments",
        "content": """
## Admin Role Management

### Roles

| Role | Quyền |
|------|-------|
| `USER` | Quản lý tài nguyên cá nhân |
| `ADMIN` | Quản lý users, payments |
| `SUPER_ADMIN` | Toàn quyền |

### Security Rules
1. Không ai có thể tự xóa account của mình
2. Admin không thể xóa Admin hoặc Super Admin
3. Role = SUPER_ADMIN → is_superuser = True
        """
    },
    "api_endpoints": {
        "title": "API Endpoints",
        "description": "Danh sách các API endpoints",
        "content": """
## API Endpoints

### Admin APIs
```
GET    /api/v1/admin/users             # List users
POST   /api/v1/admin/users             # Create user
GET    /api/v1/admin/users/{id}        # Get user detail
PATCH  /api/v1/admin/users/{id}        # Update user
DELETE /api/v1/admin/users/{id}        # Delete user
```

### Provider APIs
```
GET    /api/v1/providers/schemas       # Get all schemas
POST   /api/v1/providers/test          # Test provider
```

POST   http://localhost:8104/synthesize  # Gwen TTS
POST   http://localhost:8105/v1/audio/transcriptions # Qwen3 ASR

        """
    }
}


@router.get("/", response_model=dict)
async def get_documentation_index():
    """Get documentation index."""
    return {
        "success": True,
        "data": {
            "title": "Agent Chat AI Documentation",
            "version": "1.0.0",
            "sections": [
                {
                    "id": key,
                    "title": value["title"],
                    "description": value["description"]
                }
                for key, value in DOCS_CONTENT.items()
            ]
        }
    }


@router.get("/{section_id}", response_model=dict)
async def get_documentation_section(section_id: str):
    """Get a specific documentation section."""
    if section_id not in DOCS_CONTENT:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Section not found"}
        )
    
    section = DOCS_CONTENT[section_id]
    return {
        "success": True,
        "data": {
            "id": section_id,
            "title": section["title"],
            "description": section["description"],
            "content": section["content"].strip()
        }
    }


@router.get("/status/services", response_model=dict)
async def get_services_status():
    """Get status of TTS services."""
    # httpx imported at top-level
    
    services = [
        {"name": "Valtec TTS", "url": "http://valtec-tts:8101/health", "type": "GPU"},
        {"name": "Edge TTS", "url": None, "type": "Cloud"},
    ]
    
    results = []
    async with httpx.AsyncClient(timeout=5) as client:
        for service in services:
            status = "unknown"
            
            if service["url"]:
                try:
                    response = await client.get(service["url"])
                    status = "online" if response.status_code == 200 else "offline"
                except Exception:
                    status = "offline"
            else:
                status = "available"
            
            results.append({
                "name": service["name"],
                "type": service["type"],
                "status": status
            })
    
    return {
        "success": True,
        "data": {
            "services": results,
            "timestamp": "2025-12-28T03:58:00Z"
        }
    }
