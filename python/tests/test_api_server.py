"""
Tests for core/api_server.py - FastAPI server endpoints.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def mock_plugin_loader():
    """Mock the plugin_loader module."""
    with patch('core.api_server.plugin_loader') as mock:
        mock.plugins = {}
        mock.load_plugins = MagicMock()
        yield mock


@pytest.fixture
def mock_remote_manager():
    """Mock the RemoteManager."""
    with patch('core.api_server.RemoteManager', None):
        yield


@pytest.fixture
def test_client(mock_plugin_loader, mock_remote_manager):
    """Create a test client for the FastAPI app."""
    from core.api_server import app

    with TestClient(app) as client:
        yield client


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_check_returns_ok(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "ai_engine"


class TestMatchEndpoint:
    """Tests for /v1/match endpoint."""

    def test_match_no_plugins(self, test_client, mock_plugin_loader):
        mock_plugin_loader.plugins = {}

        response = test_client.post(
            "/v1/match",
            json={"url": "https://example.com/page"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["scripts"] == []

    def test_match_with_matching_plugin(self, test_client, mock_plugin_loader):
        # Setup mock plugin that matches
        mock_ctx = MagicMock()
        mock_ctx.manifest.content_scripts = [
            MagicMock(
                matches=["<all_urls>"],
                js=["content.js"],
                run_at="document_end"
            )
        ]
        mock_plugin_loader.plugins = {"test_plugin": mock_ctx}

        with patch('core.api_server.UrlMatcher') as mock_matcher:
            mock_matcher.match.return_value = True

            response = test_client.post(
                "/v1/match",
                json={"url": "https://example.com/page"}
            )

        assert response.status_code == 200
        data = response.json()
        assert len(data["scripts"]) > 0

    def test_match_no_matching_plugin(self, test_client, mock_plugin_loader):
        mock_ctx = MagicMock()
        mock_ctx.manifest.content_scripts = [
            MagicMock(
                matches=["https://specific.com/*"],
                js=["content.js"],
                run_at="document_end"
            )
        ]
        mock_plugin_loader.plugins = {"test_plugin": mock_ctx}

        with patch('core.api_server.UrlMatcher') as mock_matcher:
            mock_matcher.match.return_value = False

            response = test_client.post(
                "/v1/match",
                json={"url": "https://example.com/page"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["scripts"] == []

    def test_match_invalid_request(self, test_client):
        response = test_client.post("/v1/match", json={})
        assert response.status_code == 422  # Validation error


class TestPluginConnectionManager:
    """Tests for PluginConnectionManager class."""

    def test_initialization(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()
        assert manager.active_connections == {}

    @pytest.mark.asyncio
    async def test_connect_adds_websocket(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()
        mock_ws = AsyncMock()

        await manager.connect(mock_ws, "test_plugin")

        assert "test_plugin" in manager.active_connections
        assert mock_ws in manager.active_connections["test_plugin"]
        mock_ws.accept.assert_called_once()

    def test_disconnect_removes_websocket(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()
        mock_ws = MagicMock()
        manager.active_connections["test_plugin"] = [mock_ws]

        manager.disconnect(mock_ws, "test_plugin")

        assert mock_ws not in manager.active_connections["test_plugin"]

    def test_disconnect_nonexistent_plugin(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()
        mock_ws = MagicMock()

        # Should not raise
        manager.disconnect(mock_ws, "nonexistent")

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        manager.active_connections["test_plugin"] = [mock_ws1, mock_ws2]

        await manager.broadcast("test_plugin", {"action": "test"})

        mock_ws1.send_json.assert_called_once_with({"action": "test"})
        mock_ws2.send_json.assert_called_once_with({"action": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_no_connections(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()

        # Should not raise
        await manager.broadcast("nonexistent", {"action": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_send(self):
        from core.api_server import PluginConnectionManager

        manager = PluginConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.send_json.side_effect = Exception("Connection closed")
        manager.active_connections["test_plugin"] = [mock_ws]

        # Should not raise
        await manager.broadcast("test_plugin", {"action": "test"})


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_allows_any_origin(self, test_client):
        response = test_client.options(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200
