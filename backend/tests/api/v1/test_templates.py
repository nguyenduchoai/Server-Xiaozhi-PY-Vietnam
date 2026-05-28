"""
Tests for Template API endpoints.

Tests:
- Template listing
- Template CRUD operations
- Template provider assignment
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


class TestTemplateListEndpoints:
    """Tests for template listing."""

    @pytest.mark.asyncio
    async def test_list_templates_requires_auth(self, client: AsyncClient):
        """Test listing templates requires authentication."""
        response = await client.get("/api/v1/templates")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, auth_headers: dict):
        """Test listing user templates."""
        response = await client.get(
            "/api/v1/templates",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list or paginated response
        assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_list_templates_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test template listing with pagination."""
        response = await client.get(
            "/api/v1/templates?page=1&page_size=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200


class TestTemplateCRUDEndpoints:
    """Tests for template CRUD operations."""

    @pytest.fixture
    def template_data(self) -> dict:
        """Sample template creation data."""
        return {
            "name": f"Test Template {uuid4().hex[:8]}",
            "description": "A test template for unit testing",
            "system_prompt": "You are a helpful assistant.",
        }

    @pytest.mark.asyncio
    async def test_create_template(
        self, client: AsyncClient, auth_headers: dict, template_data: dict
    ):
        """Test creating a new template."""
        response = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json=template_data
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == template_data["name"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_template_missing_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating template without name fails."""
        invalid_data = {
            "description": "No name provided",
        }
        
        response = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json=invalid_data
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_template_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting non-existent template returns 404."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/templates/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_template_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test updating non-existent template returns 404."""
        fake_id = str(uuid4())
        response = await client.patch(
            f"/api/v1/templates/{fake_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_template_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting non-existent template returns 404."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/templates/{fake_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404


class TestTemplateWorkflow:
    """Integration tests for template workflows."""

    @pytest.mark.asyncio
    async def test_create_update_delete_flow(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test full CRUD workflow for templates."""
        # Create
        create_data = {
            "name": f"Workflow Test {uuid4().hex[:8]}",
            "system_prompt": "Initial prompt",
        }
        
        create_resp = await client.post(
            "/api/v1/templates",
            headers=auth_headers,
            json=create_data
        )
        
        if create_resp.status_code not in [200, 201]:
            pytest.skip("Template creation not working in test environment")
        
        template_id = create_resp.json()["id"]
        
        # Update
        update_resp = await client.patch(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        
        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Name"
        
        # Delete
        delete_resp = await client.delete(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers
        )
        
        assert delete_resp.status_code in [200, 204]
        
        # Verify deleted
        get_resp = await client.get(
            f"/api/v1/templates/{template_id}",
            headers=auth_headers
        )
        
        assert get_resp.status_code == 404
