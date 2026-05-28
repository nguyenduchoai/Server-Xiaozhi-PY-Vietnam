import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

class TestDeviceAgents:
    """Test device-agent assignment list."""

    @pytest.mark.asyncio
    async def test_get_device_agents_includes_details(self, client: AsyncClient, auth_headers: dict):
        """Test getting device agents includes required fields and soft-deleted agents."""
        
        # 1. Generate activation code
        activate_response = await client.post(
            "/api/v1/devices/request-activation",
            json={"mac_address": "DD:AA:BB:CC:DD:EE", "device_name": "Test Device For Agent"}
        )
        assert activate_response.status_code == 200
        code = activate_response.json()["code"]
        
        # 2. Activate device
        create_device_resp = await client.post(
            "/api/v1/devices/activate",
            json={"code": code},
            headers=auth_headers
        )
        assert create_device_resp.status_code in [200, 201]
        device_id = create_device_resp.json()["id"]

        # 3. Create a test agent
        create_agent_resp = await client.post(
            "/api/v1/agents",
            json={
                "agent_name": "Test Agent Active",
                "description": "An active test agent",
                "llm_provider": "openai",
                "tts_provider": "edge",
                "asr_provider": "local"
            },
            headers=auth_headers
        )
        assert create_agent_resp.status_code in [200, 201]
        agent_id = create_agent_resp.json()["data"]["id"]

        # 4. Create another deleted agent for test
        create_agent_deleted = await client.post(
            "/api/v1/agents",
            json={
                "agent_name": "Test Agent Deleted",
                "description": "A soft-deleted test agent",
                "llm_provider": "openai",
                "tts_provider": "edge",
                "asr_provider": "local"
            },
            headers=auth_headers
        )
        assert create_agent_deleted.status_code in [200, 201]
        agent_id_deleted = create_agent_deleted.json()["data"]["id"]

        # 5. Assign both agents to device
        assign_resp1 = await client.post(
            f"/api/v1/devices/{device_id}/agents",
            json={"agent_id": agent_id, "set_active": True},
            headers=auth_headers
        )
        assert assign_resp1.status_code == 200
        
        assign_resp2 = await client.post(
            f"/api/v1/devices/{device_id}/agents",
            json={"agent_id": agent_id_deleted, "set_active": False},
            headers=auth_headers
        )
        assert assign_resp2.status_code == 200
        
        # 6. Soft delete the second agent
        delete_agent_resp = await client.delete(
            f"/api/v1/agents/{agent_id_deleted}",
            headers=auth_headers
        )
        assert delete_agent_resp.status_code == 200

        # 7. Fetch the agents list for the device
        agents_resp = await client.get(
            f"/api/v1/devices/{device_id}/agents",
            headers=auth_headers
        )
        assert agents_resp.status_code == 200
        data = agents_resp.json()
        assert data["success"] is True
        assert data["total"] >= 2
        
        agents_list = data["agents"]
        
        # Check active agent
        active_agent = next((a for a in agents_list if a["agent_id"] == agent_id), None)
        assert active_agent is not None
        assert active_agent["agent_name"] == "Test Agent Active"
        assert active_agent["agent_status"] == "active"
        assert "assigned_date" in active_agent
        assert active_agent["is_active"] is True
        
        # Check deleted agent
        deleted_agent = next((a for a in agents_list if a["agent_id"] == agent_id_deleted), None)
        assert deleted_agent is not None
        assert deleted_agent["agent_name"] == "Test Agent Deleted"
        assert deleted_agent["agent_status"] == "deleted"
        assert "assigned_date" in deleted_agent
        assert deleted_agent["is_active"] is False
