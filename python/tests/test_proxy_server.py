"""
Tests for core/proxy_server.py - Mitmproxy addon.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestAiPlugsAddonInitialization:
    """Tests for AiPlugsAddon initialization."""

    @patch('core.proxy_server.plugin_loader')
    def test_initialization_with_empty_plugins(self, mock_loader):
        from core.proxy_server import AiPlugsAddon

        mock_loader.plugins = {}

        addon = AiPlugsAddon(api_port=8000)

        assert addon.api_port == 8000
        assert len(addon.pipeline) > 0
        mock_loader.load_plugins.assert_called_once()

    @patch('core.proxy_server.plugin_loader')
    def test_initialization_with_existing_plugins(self, mock_loader):
        from core.proxy_server import AiPlugsAddon

        mock_loader.plugins = {"plugin1": MagicMock()}

        addon = AiPlugsAddon(api_port=8000)

        # Should not call load_plugins if plugins already exist
        mock_loader.load_plugins.assert_not_called()

    @patch('core.proxy_server.plugin_loader')
    def test_pipeline_has_expected_handlers(self, mock_loader):
        from core.proxy_server import AiPlugsAddon

        mock_loader.plugins = {"test": MagicMock()}

        addon = AiPlugsAddon(api_port=8000)

        # Pipeline should have multiple handlers
        assert len(addon.pipeline) >= 5


class TestAiPlugsAddonResponse:
    """Tests for AiPlugsAddon.response method."""

    @patch('core.proxy_server.plugin_loader')
    def test_response_processes_pipeline(self, mock_loader):
        from core.proxy_server import AiPlugsAddon

        mock_loader.plugins = {"test": MagicMock()}

        addon = AiPlugsAddon(api_port=8000)

        # Mock flow
        flow = MagicMock()
        flow.request.url = "https://example.com/page"
        flow.response.headers = {"Content-Type": "text/html"}

        # Mock all pipeline handlers to return True
        for handler in addon.pipeline:
            handler.process = MagicMock(return_value=True)

        addon.response(flow)

        # All handlers should have been called
        for handler in addon.pipeline:
            handler.process.assert_called_once()

    @patch('core.proxy_server.plugin_loader')
    def test_response_stops_on_false(self, mock_loader):
        from core.proxy_server import AiPlugsAddon

        mock_loader.plugins = {"test": MagicMock()}

        addon = AiPlugsAddon(api_port=8000)

        flow = MagicMock()

        # First handler returns False
        addon.pipeline[0].process = MagicMock(return_value=False)
        addon.pipeline[1].process = MagicMock(return_value=True)

        addon.response(flow)

        # Second handler should not be called
        addon.pipeline[0].process.assert_called_once()
        addon.pipeline[1].process.assert_not_called()

    @patch('core.proxy_server.plugin_loader')
    def test_response_handles_exception(self, mock_loader):
        from core.proxy_server import AiPlugsAddon

        mock_loader.plugins = {"test": MagicMock()}

        addon = AiPlugsAddon(api_port=8000)

        flow = MagicMock()
        flow.request.url = "https://example.com/page"

        # Handler raises exception
        addon.pipeline[0].process = MagicMock(side_effect=Exception("Test error"))

        # Should not raise
        addon.response(flow)
