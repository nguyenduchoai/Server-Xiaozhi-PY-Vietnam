"""
Site Settings API Tests

Tests for:
- Public settings retrieval
- Admin settings update
"""

import pytest
from httpx import AsyncClient


class TestSiteSettings:
    """Test site settings endpoints."""

    @pytest.mark.asyncio
    async def test_get_site_settings_public(self, client: AsyncClient):
        """Test getting public site settings (no auth required)."""
        response = await client.get("/api/v1/site-settings")
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert "web" in data
        assert "home" in data
        
        # Check web section
        assert "site_name" in data["web"]
        
        # Check home section has expected subsections
        assert "hero" in data["home"]
        assert "features" in data["home"]
        assert "pricing" in data["home"]
        assert "footer" in data["home"]

    @pytest.mark.asyncio
    async def test_update_site_settings_requires_admin(self, client: AsyncClient, auth_headers: dict):
        """Test that updating settings requires admin role."""
        response = await client.put(
            "/api/v1/site-settings",
            json={"web": {"site_name": "Updated Name"}},
            headers=auth_headers  # Regular user, not admin
        )
        # Should be forbidden for non-admin
        assert response.status_code in [403, 422]

    @pytest.mark.asyncio
    async def test_update_site_settings_as_admin(self, client: AsyncClient, admin_headers: dict):
        """Test updating settings as admin."""
        response = await client.put(
            "/api/v1/site-settings",
            json={
                "web": {"site_name": "Test Site Updated"},
                "home": {
                    "hero": {
                        "hero_title": "Updated Hero Title"
                    }
                }
            },
            headers=admin_headers
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_site_settings_contains_branding(self, client: AsyncClient):
        """Test that site settings includes branding section."""
        response = await client.get("/api/v1/site-settings")
        data = response.json()
        
        assert "branding" in data
        assert "parent_company_name" in data["branding"]

    @pytest.mark.asyncio
    async def test_site_settings_contains_solutions(self, client: AsyncClient):
        """Test that site settings includes solutions section."""
        response = await client.get("/api/v1/site-settings")
        data = response.json()
        
        assert "solutions" in data["home"]
        assert "solutions_enabled" in data["home"]["solutions"]

    @pytest.mark.asyncio
    async def test_site_settings_contains_faq(self, client: AsyncClient):
        """Test that site settings includes FAQ section."""
        response = await client.get("/api/v1/site-settings")
        data = response.json()
        
        assert "faq" in data["home"]
        assert "faq_enabled" in data["home"]["faq"]
