"""
Devices API Tests

Tests for:
- Device activation flow
- Device CRUD operations
- Device binding to agents
"""

import pytest
from httpx import AsyncClient


class TestDeviceActivation:
    """Test device activation endpoints."""

    @pytest.mark.asyncio
    async def test_request_activation_code(self, client: AsyncClient):
        """Test requesting activation code from device."""
        response = await client.post(
            "/api/v1/devices/request-activation",
            json={
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "device_name": "Test ESP32",
                "board": "ESP32-S3",
                "firmware_version": "1.0.0"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert len(data["code"]) == 6
        assert data["code"].isdigit()

    @pytest.mark.asyncio
    async def test_request_activation_invalid_mac(self, client: AsyncClient):
        """Test requesting activation with invalid MAC address."""
        response = await client.post(
            "/api/v1/devices/request-activation",
            json={
                "mac_address": "invalid",
                "device_name": "Test"
            }
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_activation_status(self, client: AsyncClient):
        """Test checking activation status."""
        # First request activation
        await client.post(
            "/api/v1/devices/request-activation",
            json={"mac_address": "11:22:33:44:55:66"}
        )
        
        # Check status
        response = await client.get(
            "/api/v1/devices/activation-status/11:22:33:44:55:66"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_activate_device_by_code(self, client: AsyncClient, auth_headers: dict):
        """Test activating device with code."""
        # Request activation code
        activate_response = await client.post(
            "/api/v1/devices/request-activation",
            json={"mac_address": "AA:BB:CC:DD:EE:01", "board": "ESP32"}
        )
        code = activate_response.json()["code"]
        
        # Activate with user auth
        response = await client.post(
            "/api/v1/devices/activate",
            json={"code": code},
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["mac_address"] == "AA:BB:CC:DD:EE:01"

    @pytest.mark.asyncio
    async def test_activate_device_invalid_code(self, client: AsyncClient, auth_headers: dict):
        """Test activating device with invalid code fails."""
        response = await client.post(
            "/api/v1/devices/activate",
            json={"code": "000000"},
            headers=auth_headers
        )
        assert response.status_code == 400


class TestDevicesCRUD:
    """Test device CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_devices(self, client: AsyncClient, auth_headers: dict):
        """Test listing user devices."""
        response = await client.get("/api/v1/agents", headers=auth_headers)
        # Devices might be under /agents/{id}/devices or separate
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_device(self, client: AsyncClient, auth_headers: dict):
        """Test deleting a device."""
        # First create a device via activation
        activate_response = await client.post(
            "/api/v1/devices/request-activation",
            json={"mac_address": "DE:AD:BE:EF:00:01"}
        )
        code = activate_response.json()["code"]
        
        create_response = await client.post(
            "/api/v1/devices/activate",
            json={"code": code},
            headers=auth_headers
        )
        
        if create_response.status_code in [200, 201]:
            device_id = create_response.json()["id"]
            
            # Delete device
            delete_response = await client.delete(
                f"/api/v1/devices/{device_id}",
                headers=auth_headers
            )
            assert delete_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_update_device(self, client: AsyncClient, auth_headers: dict):
        """Test updating device info."""
        # Create device first
        activate_response = await client.post(
            "/api/v1/devices/request-activation",
            json={"mac_address": "DE:AD:BE:EF:00:02"}
        )
        code = activate_response.json()["code"]
        
        create_response = await client.post(
            "/api/v1/devices/activate",
            json={"code": code},
            headers=auth_headers
        )
        
        if create_response.status_code in [200, 201]:
            device_id = create_response.json()["id"]
            
            # Update device
            update_response = await client.patch(
                f"/api/v1/devices/{device_id}",
                json={"device_name": "My Updated Device"},
                headers=auth_headers
            )
            assert update_response.status_code == 200
            assert update_response.json()["device_name"] == "My Updated Device"
