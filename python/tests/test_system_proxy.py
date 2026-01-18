"""
Tests for utils/system_proxy.py - System proxy configuration.
"""
import pytest
import sys
from unittest.mock import patch, MagicMock


class TestSystemProxyInitialization:
    """Tests for SystemProxy initialization."""

    def test_initialization_detects_platform(self):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        assert proxy.os_type == sys.platform


class TestSystemProxySetProxy:
    """Tests for set_proxy method."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    @patch('utils.system_proxy.winreg')
    @patch('utils.system_proxy.ctypes')
    def test_set_proxy_windows(self, mock_ctypes, mock_winreg):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        proxy.set_proxy("127.0.0.1", 8080)

        # Verify registry was opened and values were set
        mock_winreg.OpenKey.assert_called()
        mock_winreg.SetValueEx.assert_called()

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
    @patch('subprocess.run')
    def test_set_proxy_mac(self, mock_run):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        proxy.set_proxy("127.0.0.1", 8080)

        # Verify networksetup commands were called
        assert mock_run.call_count >= 2  # HTTP and HTTPS proxy


class TestSystemProxyDisableProxy:
    """Tests for disable_proxy method."""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only test")
    @patch('utils.system_proxy.winreg')
    @patch('utils.system_proxy.ctypes')
    def test_disable_proxy_windows(self, mock_ctypes, mock_winreg):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        proxy.disable_proxy()

        # Verify ProxyEnable was set to 0
        mock_winreg.SetValueEx.assert_called()

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
    @patch('subprocess.run')
    def test_disable_proxy_mac(self, mock_run):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        proxy.disable_proxy()

        assert mock_run.call_count >= 2


class TestSystemProxyMacServiceDetection:
    """Tests for macOS network service detection."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
    @patch('subprocess.run')
    def test_get_mac_service_wifi(self, mock_run):
        from utils.system_proxy import SystemProxy

        mock_run.return_value = MagicMock(
            stdout="An asterisk (*) denotes...\nWi-Fi\nEthernet"
        )

        proxy = SystemProxy()
        service = proxy._get_mac_service()

        assert service == "Wi-Fi"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
    @patch('subprocess.run')
    def test_get_mac_service_ethernet(self, mock_run):
        from utils.system_proxy import SystemProxy

        mock_run.return_value = MagicMock(
            stdout="An asterisk (*) denotes...\nEthernet"
        )

        proxy = SystemProxy()
        service = proxy._get_mac_service()

        assert service == "Ethernet"

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-only test")
    @patch('subprocess.run')
    def test_get_mac_service_fallback(self, mock_run):
        from utils.system_proxy import SystemProxy

        mock_run.side_effect = Exception("Command failed")

        proxy = SystemProxy()
        service = proxy._get_mac_service()

        assert service == "Wi-Fi"  # Default fallback


class TestSystemProxyPlatformHandling:
    """Tests for cross-platform handling."""

    def test_unsupported_platform_set_proxy(self):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        original_os = proxy.os_type
        proxy.os_type = "linux"

        # Should not raise, just do nothing
        proxy.set_proxy("127.0.0.1", 8080)

        proxy.os_type = original_os

    def test_unsupported_platform_disable_proxy(self):
        from utils.system_proxy import SystemProxy

        proxy = SystemProxy()
        original_os = proxy.os_type
        proxy.os_type = "linux"

        # Should not raise, just do nothing
        proxy.disable_proxy()

        proxy.os_type = original_os
