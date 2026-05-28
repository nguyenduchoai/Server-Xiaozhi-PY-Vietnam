"""
Agents API Tests

Tests for:
- Agent CRUD operations
- Agent templates
- Agent chat
"""

import pytest
from httpx import AsyncClient


class TestAgentsEndpoints:
    """Test agents API endpoints."""

    @pytest.mark.asyncio
    async def test_list_agents_empty(self, client: AsyncClient, auth_headers: dict):
        """Test listing agents when none exist."""
        response = await client.get("/api/v1/agents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("data", data), list)

    @pytest.mark.asyncio
    async def test_create_agent_success(self, client: AsyncClient, auth_headers: dict, test_agent_data: dict):
        """Test successful agent creation."""
        response = await client.post(
            "/api/v1/agents",
            json=test_agent_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        data = response.json()
        agent = data.get("data", data)
        assert agent.get("name") == test_agent_data["name"]
        assert "id" in agent

    @pytest.mark.asyncio
    async def test_create_agent_no_auth(self, client: AsyncClient, test_agent_data: dict):
        """Test creating agent without auth fails."""
        response = await client.post("/api/v1/agents", json=test_agent_data)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_agent_by_id(self, client: AsyncClient, auth_headers: dict, test_agent_data: dict):
        """Test getting agent by ID."""
        # Create agent first
        create_response = await client.post(
            "/api/v1/agents",
            json=test_agent_data,
            headers=auth_headers
        )
        agent = create_response.json().get("data", create_response.json())
        agent_id = agent["id"]
        
        # Get by ID
        response = await client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        fetched = data.get("data", data)
        assert fetched["id"] == agent_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, client: AsyncClient, auth_headers: dict):
        """Test getting non-existent agent returns 404."""
        response = await client.get(
            "/api/v1/agents/nonexistent-id-12345",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_agent(self, client: AsyncClient, auth_headers: dict, test_agent_data: dict):
        """Test updating an agent."""
        # Create agent
        create_response = await client.post(
            "/api/v1/agents",
            json=test_agent_data,
            headers=auth_headers
        )
        agent = create_response.json().get("data", create_response.json())
        agent_id = agent["id"]
        
        # Update
        update_data = {"name": "Updated Agent Name"}
        response = await client.patch(
            f"/api/v1/agents/{agent_id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        updated = response.json().get("data", response.json())
        assert updated["name"] == "Updated Agent Name"

    @pytest.mark.asyncio
    async def test_delete_agent(self, client: AsyncClient, auth_headers: dict, test_agent_data: dict):
        """Test deleting an agent."""
        # Create agent
        create_response = await client.post(
            "/api/v1/agents",
            json=test_agent_data,
            headers=auth_headers
        )
        agent = create_response.json().get("data", create_response.json())
        agent_id = agent["id"]
        
        # Delete
        response = await client.delete(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert response.status_code in [200, 204]
        
        # Verify deleted
        get_response = await client.get(f"/api/v1/agents/{agent_id}", headers=auth_headers)
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_agent_validation_empty_name(self, client: AsyncClient, auth_headers: dict):
        """Test creating agent with empty name fails."""
        response = await client.post(
            "/api/v1/agents",
            json={"name": "", "description": "Test"},
            headers=auth_headers
        )
        assert response.status_code == 422


class TestAgentTemplates:
    """Test agent template endpoints."""

    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers: dict):
        """Test listing available templates."""
        response = await client.get("/api/v1/templates", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("data", data), list)

    @pytest.mark.asyncio
    async def test_get_template_by_id(self, client: AsyncClient, auth_headers: dict):
        """Test getting template by ID."""
        # First get list of templates
        list_response = await client.get("/api/v1/templates", headers=auth_headers)
        templates = list_response.json().get("data", list_response.json())
        
        if templates and len(templates) > 0:
            template_id = templates[0]["id"]
            response = await client.get(f"/api/v1/templates/{template_id}", headers=auth_headers)
            assert response.status_code == 200
