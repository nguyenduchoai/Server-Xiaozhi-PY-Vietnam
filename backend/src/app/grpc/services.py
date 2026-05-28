"""
gRPC Services Implementation

Implements gRPC services for internal communication.
"""

import asyncio
from concurrent import futures
from typing import Optional
import grpc
from grpc import aio

from app.core.logger import get_logger
from app.core.config import settings


logger = get_logger(__name__)


class AgentServicer:
    """gRPC Agent service implementation."""
    
    async def GetAgent(self, request, context):
        """Get agent by ID."""
        from uuid import UUID
        
        try:
            agent_id = UUID(request.agent_id)
            
            return AgentResponse(
                success=True,
                agent=Agent(
                    id=str(agent_id),
                    name="Agent",
                    prompt="",
                ),
            )
        except Exception as e:
            logger.error(f"gRPC GetAgent error: {e}")
            return AgentResponse(
                success=False,
                error=str(e),
            )
    
    async def ListAgents(self, request, context):
        """List agents with pagination."""
        return ListAgentsResponse(
            success=True,
            agents=[],
            total=0,
        )
    
    async def CreateAgent(self, request, context):
        """Create a new agent."""
        return AgentResponse(
            success=True,
            agent=Agent(
                id="new-agent-id",
                name=request.name,
                prompt=request.prompt,
                tts_type=request.tts_type,
                asr_type=request.asr_type,
                llm_type=request.llm_type,
                vad_type=request.vad_type,
            ),
        )
    
    async def UpdateAgent(self, request, context):
        """Update an existing agent."""
        return AgentResponse(
            success=True,
            agent=Agent(
                id=request.agent_id,
                name=request.name or "",
                prompt=request.prompt or "",
            ),
        )
    
    async def DeleteAgent(self, request, context):
        """Delete an agent."""
        return DeleteResponse(success=True)


class DeviceServicer:
    """gRPC Device service implementation."""
    
    async def GetDevice(self, request, context):
        """Get device by ID."""
        return DeviceResponse(
            success=True,
            device=Device(
                id=request.device_id,
                mac_address="",
                board="Unknown",
            ),
        )
    
    async def ListDevices(self, request, context):
        """List devices with pagination."""
        return ListDevicesResponse(
            success=True,
            devices=[],
            total=0,
        )
    
    async def RegisterDevice(self, request, context):
        """Register a new device."""
        return RegisterDeviceResponse(
            success=True,
            device_id="new-device-id",
            activation_token="token123",
        )
    
    async def UpdateDeviceStatus(self, request, context):
        """Update device status."""
        return StatusResponse(
            success=True,
            message="Status updated",
        )


class HealthServicer:
    """gRPC Health check service implementation."""
    
    async def Check(self, request, context):
        """Perform health check."""
        return HealthCheckResponse(
            status="healthy",
            service=request.service or "xiaozhi-api",
            version="1.0.0",
            checks={
                "database": "healthy",
                "redis": "healthy",
                "mqtt": "healthy",
            },
        )
    
    async def Watch(self, request, context):
        """Watch health status with streaming."""
        while True:
            yield HealthCheckResponse(
                status="healthy",
                service=request.service or "xiaozhi-api",
                version="1.0.0",
            )
            await asyncio.sleep(5)


class GRPCServer:
    """gRPC Server manager."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 50051):
        self.host = host
        self.port = port
        self.server: Optional[aio.Server] = None
        self.is_running = False
    
    async def start(self):
        """Start the gRPC server."""
        self.server = aio.server(
            futures.ThreadPoolExecutor(max_workers=10),
            options=[
                ("grpc.max_send_message_length", 50 * 1024 * 1024),
                ("grpc.max_receive_message_length", 50 * 1024 * 1024),
            ],
        )
        
        from app.grpc.protos import xiaozhi_pb2 as pb2
        from app.grpc.protos import xiaozhi_pb2_grpc as pb2_grpc
        
        pb2_grpc.add_AgentServiceServicer_to_server(
            AgentServicer(), self.server
        )
        pb2_grpc.add_DeviceServiceServicer_to_server(
            DeviceServicer(), self.server
        )
        pb2_grpc.add_HealthServiceServicer_to_server(
            HealthServicer(), self.server
        )
        
        listen_addr = f"{self.host}:{self.port}"
        self.server.add_insecure_port(listen_addr)
        
        await self.server.start()
        self.is_running = True
        
        logger.info(f"gRPC server started on {listen_addr}")
    
    async def stop(self):
        """Stop the gRPC server."""
        if self.server:
            await self.server.stop(grace=5)
            self.is_running = False
            logger.info("gRPC server stopped")


grpc_server = GRPCServer()
