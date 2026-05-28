"""
MCP Endpoint Server Proxy API
Provides endpoints to manage and monitor MCP connections through the mcp-endpoint-server container
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ...core.config import settings
from ...api.dependencies import get_current_user


def require_superuser(current_user: dict) -> dict:
    is_superuser = current_user.get("is_superuser")
    role = current_user.get("role")
    
    if is_superuser:
        return current_user
        
    if role in ["admin", "super_admin"]:
        return current_user
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superuser access required"
    )


router = APIRouter(prefix="/mcp-endpoint", tags=["mcp-endpoint"])

LOGGER = logging.getLogger(__name__)

# MCP Endpoint Server internal URL (container name in docker network)
MCP_SERVER_URL = "http://xiaozhi-mcp:8004"

# Chinese to Vietnamese error message translations
CHINESE_TO_VIETNAMESE = {
    "密钥验证失败": "Xác thực key thất bại",
    "提供的密钥无效或缺失": "Key không hợp lệ hoặc không được cung cấp",
    "连接失败": "Kết nối thất bại",
    "服务器错误": "Lỗi server",
    "请求超时": "Yêu cầu quá thời gian",
    "无效请求": "Yêu cầu không hợp lệ",
    "未授权": "Chưa được xác thực",
    "禁止访问": "Truy cập bị từ chối",
}


def translate_error(text: str) -> str:
    """Translate Chinese error messages to Vietnamese"""
    if not text:
        return text
    result = text
    for zh, vi in CHINESE_TO_VIETNAMESE.items():
        result = result.replace(zh, vi)
    return result


class MCPHealthResponse(BaseModel):
    """Response model for MCP health check"""
    status: str
    connections: Optional[dict] = None
    error: Optional[str] = None


class MCPStatsResponse(BaseModel):
    """Response model for MCP connection statistics"""
    tool_connections: int = 0
    robot_connections: int = 0
    total_connections: int = 0
    robot_connections_by_agent: dict = {}


class MCPServerInfo(BaseModel):
    """Response model for MCP server info"""
    message: str
    version: str
    status: str


class MCPConfigResponse(BaseModel):
    """Response model for MCP configuration"""
    key: Optional[str] = None
    websocket_tool_url: str
    websocket_robot_url: str
    health_url: str


async def get_mcp_key() -> str:
    """
    Get MCP server key from settings.
    The key is auto-generated and stored in mcp-endpoint-server config file.
    """
    return settings.MCP_ENDPOINT_KEY


async def make_mcp_request(
    method: str,
    path: str,
    params: Optional[dict] = None,
    timeout: float = 10.0
) -> dict:
    """
    Make HTTP request to MCP Endpoint Server
    """
    url = f"{MCP_SERVER_URL}{path}"
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "GET":
                response = await client.get(url, params=params)
            elif method.upper() == "POST":
                response = await client.post(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
    except httpx.ConnectError:
        LOGGER.error(f"Cannot connect to MCP Endpoint Server at {url}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP Endpoint Server is not available"
        )
    except httpx.TimeoutException:
        LOGGER.error(f"Timeout connecting to MCP Endpoint Server at {url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="MCP Endpoint Server request timed out"
        )
    except httpx.HTTPStatusError as e:
        LOGGER.error(f"MCP Endpoint Server returned error: {e.response.status_code}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"MCP Endpoint Server error: {e.response.text}"
        )
    except Exception as e:
        LOGGER.exception(f"Error communicating with MCP Endpoint Server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/info", response_model=MCPServerInfo)
async def get_mcp_server_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get MCP Endpoint Server info (requires admin)
    """
    require_superuser(current_user)
    try:
        result = await make_mcp_request("GET", "/mcp_endpoint/")
        return MCPServerInfo(
            message=result.get("result", {}).get("message", "MCP Endpoint Server"),
            version=result.get("result", {}).get("version", "unknown"),
            status=result.get("result", {}).get("status", "unknown")
        )
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.exception(f"Error getting MCP server info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MCP server info"
        )


@router.get("/health", response_model=MCPHealthResponse)
async def get_mcp_health(
    current_user: dict = Depends(get_current_user)
):
    """
    Get MCP Endpoint Server health status and connection stats (requires admin)
    """
    require_superuser(current_user)
    try:
        key = await get_mcp_key()
        params = {"key": key} if key else {}
        
        result = await make_mcp_request("GET", "/mcp_endpoint/health", params=params)
        
        # Defensive check: if result is None or malformed
        if not result:
            return MCPHealthResponse(
                status="error",
                error="MCP server returned empty response"
            )
        
        if result.get("error"):
            error_data = result.get("error", {})
            error_message = error_data.get("message", str(error_data)) if isinstance(error_data, dict) else str(error_data)
            return MCPHealthResponse(
                status="error",
                error=translate_error(error_message)
            )
        
        return MCPHealthResponse(
            status=result.get("result", {}).get("status", "unknown"),
            connections=result.get("result", {}).get("connections", {})
        )
    except HTTPException as e:
        return MCPHealthResponse(
            status="unavailable",
            error=e.detail
        )
    except Exception as e:
        LOGGER.exception(f"Error checking MCP health: {e}")
        return MCPHealthResponse(
            status="error",
            error=str(e)
        )


@router.get("/stats", response_model=MCPStatsResponse)
async def get_mcp_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get MCP connection statistics (requires admin)
    """
    require_superuser(current_user)
    try:
        key = await get_mcp_key()
        params = {"key": key} if key else {}
        
        result = await make_mcp_request("GET", "/mcp_endpoint/health", params=params)
        
        # Defensive check: if result is None or doesn't have expected structure
        if not result or "result" not in result:
            return MCPStatsResponse(
                tool_connections=0,
                robot_connections=0,
                total_connections=0,
                robot_connections_by_agent={}
            )
        
        connections = result.get("result", {}).get("connections", {})
        
        return MCPStatsResponse(
            tool_connections=connections.get("tool_connections", 0),
            robot_connections=connections.get("robot_connections", 0),
            total_connections=connections.get("total_connections", 0),
            robot_connections_by_agent=connections.get("robot_connections_by_agent", {})
        )
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.exception(f"Error getting MCP stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MCP statistics"
        )


@router.get("/config", response_model=MCPConfigResponse)
async def get_mcp_config(
    current_user: dict = Depends(get_current_user)
):
    """
    Get MCP Endpoint Server connection URLs (requires admin)
    Returns WebSocket URLs for tool and robot connections
    """
    require_superuser(current_user)
    # Get the public-facing URLs from settings
    base_url = settings.MCP_ENDPOINT_PUBLIC_URL
    key = await get_mcp_key()
    
    return MCPConfigResponse(
        key=key if key else None,
        websocket_tool_url=f"{base_url}/mcp_endpoint/mcp/",
        websocket_robot_url=f"{base_url}/mcp_endpoint/call/",
        health_url=f"{base_url.replace('ws://', 'http://').replace('wss://', 'https://')}/mcp_endpoint/health"
    )


@router.get("/status")
async def get_mcp_status():
    """
    Simple status check for MCP Endpoint Server (public endpoint)
    Returns basic availability status without detailed stats
    """
    try:
        result = await make_mcp_request("GET", "/mcp_endpoint/", timeout=5.0)
        return {
            "available": True,
            "version": result.get("result", {}).get("version", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")
        }
    except Exception:
        return {
            "available": False,
            "version": None,
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds")
        }
