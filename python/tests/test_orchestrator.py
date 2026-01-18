"""
Tests for core/orchestrator.py - System orchestration.
"""
import pytest
import sys
from unittest.mock import patch, MagicMock, AsyncMock


class TestSystemOrchestrator:
    """Tests for SystemOrchestrator class."""

    @patch('core.orchestrator.SystemProxy')
    def test_initialization(self, mock_proxy):
        from core.orchestrator import SystemOrchestrator

        orch = SystemOrchestrator(api_port=8000, proxy_port=8080)

        assert orch.api_port == 8000
        assert orch.proxy_port == 8080
        mock_proxy.assert_called_once()

    @patch('core.orchestrator.SystemProxy')
    def test_initialization_without_proxy(self, mock_proxy):
        from core.orchestrator import SystemOrchestrator

        orch = SystemOrchestrator(api_port=8000, proxy_port=None)

        assert orch.api_port == 8000
        assert orch.proxy_port is None


class TestForceClearSystemProxy:
    """Tests for force_clear_system_proxy method."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    @patch('core.orchestrator.winreg')
    @patch('core.orchestrator.SystemProxy')
    def test_clears_registry_on_windows(self, mock_proxy, mock_winreg):
        from core.orchestrator import SystemOrchestrator

        mock_key = MagicMock()
        mock_winreg.OpenKey.return_value.__enter__ = MagicMock(return_value=mock_key)
        mock_winreg.OpenKey.return_value.__exit__ = MagicMock(return_value=False)

        orch = SystemOrchestrator(api_port=8000, proxy_port=8080)
        orch.force_clear_system_proxy()

        # Should have tried to set ProxyEnable to 0
        mock_winreg.SetValueEx.assert_called()

    @patch('core.orchestrator.SystemProxy')
    def test_handles_non_windows(self, mock_proxy):
        from core.orchestrator import SystemOrchestrator

        with patch('os.name', 'posix'):
            orch = SystemOrchestrator(api_port=8000, proxy_port=8080)
            # Should not raise on non-Windows
            orch.force_clear_system_proxy()


class TestEnableSystemProxy:
    """Tests for enable_system_proxy method."""

    @patch('core.orchestrator.SystemProxy')
    def test_enables_proxy(self, mock_proxy_class):
        from core.orchestrator import SystemOrchestrator

        mock_proxy_instance = MagicMock()
        mock_proxy_class.return_value = mock_proxy_instance

        orch = SystemOrchestrator(api_port=8000, proxy_port=8080)
        orch.enable_system_proxy()

        mock_proxy_instance.set_proxy.assert_called_once_with("127.0.0.1", 8080)

    @patch('core.orchestrator.SystemProxy')
    def test_does_not_enable_without_proxy_port(self, mock_proxy_class):
        from core.orchestrator import SystemOrchestrator

        mock_proxy_instance = MagicMock()
        mock_proxy_class.return_value = mock_proxy_instance

        orch = SystemOrchestrator(api_port=8000, proxy_port=None)
        orch.enable_system_proxy()

        mock_proxy_instance.set_proxy.assert_not_called()


class TestShutdown:
    """Tests for shutdown method."""

    @patch('core.orchestrator.SystemProxy')
    def test_shutdown_disables_proxy(self, mock_proxy_class):
        from core.orchestrator import SystemOrchestrator

        mock_proxy_instance = MagicMock()
        mock_proxy_class.return_value = mock_proxy_instance

        orch = SystemOrchestrator(api_port=8000, proxy_port=8080)

        with patch.object(orch, 'force_clear_system_proxy') as mock_clear:
            orch.shutdown()

        mock_clear.assert_called_once()
        mock_proxy_instance.disable_proxy.assert_called_once()


class TestRunMitmproxy:
    """Tests for run_mitmproxy method."""

    @pytest.mark.asyncio
    @patch('core.orchestrator.SystemProxy')
    async def test_skips_without_proxy_port(self, mock_proxy):
        from core.orchestrator import SystemOrchestrator

        orch = SystemOrchestrator(api_port=8000, proxy_port=None)

        # Should return immediately without error
        await orch.run_mitmproxy()

    @pytest.mark.asyncio
    @patch('core.orchestrator.DumpMaster')
    @patch('core.orchestrator.options')
    @patch('core.orchestrator.AiPlugsAddon')
    @patch('core.orchestrator.SystemProxy')
    async def test_initializes_mitmproxy(self, mock_proxy, mock_addon, mock_options, mock_master):
        from core.orchestrator import SystemOrchestrator

        mock_master_instance = MagicMock()
        mock_master_instance.run = AsyncMock()
        mock_master.return_value = mock_master_instance

        orch = SystemOrchestrator(api_port=8000, proxy_port=8080)

        await orch.run_mitmproxy()

        mock_options.Options.assert_called_once_with(listen_host='127.0.0.1', listen_port=8080)
        mock_master_instance.run.assert_called_once()


class TestStartApiServer:
    """Tests for start_api_server method."""

    @patch('threading.Thread')
    @patch('core.orchestrator.SystemProxy')
    def test_starts_api_thread(self, mock_proxy, mock_thread):
        from core.orchestrator import SystemOrchestrator

        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        orch = SystemOrchestrator(api_port=8000, proxy_port=8080)
        orch.start_api_server()

        mock_thread.assert_called_once()
        mock_thread_instance.start.assert_called_once()
        assert orch.api_thread is not None
