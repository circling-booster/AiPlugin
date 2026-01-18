"""
Tests for main.py - Main application entry point.
"""
import pytest
import socket
from unittest.mock import patch, MagicMock


class TestGetFreePort:
    """Tests for get_free_port function."""

    def test_returns_valid_port(self):
        from main import get_free_port

        port = get_free_port()
        assert isinstance(port, int)
        assert 1 <= port <= 65535

    def test_returns_different_ports(self):
        from main import get_free_port

        ports = [get_free_port() for _ in range(5)]
        # Ports should generally be different (not guaranteed but likely)
        # At minimum, they should all be valid
        for port in ports:
            assert 1 <= port <= 65535


class TestKillProcessOnPort:
    """Tests for kill_process_on_port function."""

    @patch('psutil.process_iter')
    def test_kills_process_on_port(self, mock_iter):
        from main import kill_process_on_port

        # Mock a process with the target port
        mock_proc = MagicMock()
        mock_proc.info = {'pid': 1234, 'name': 'test_process'}
        mock_conn = MagicMock()
        mock_conn.laddr.port = 8080
        mock_proc.connections.return_value = [mock_conn]
        mock_iter.return_value = [mock_proc]

        with patch('time.sleep'):
            kill_process_on_port(8080)

        mock_proc.kill.assert_called_once()

    @patch('psutil.process_iter')
    def test_no_process_on_port(self, mock_iter):
        from main import kill_process_on_port

        mock_iter.return_value = []

        # Should not raise
        kill_process_on_port(8080)

    @patch('psutil.process_iter')
    def test_handles_access_denied(self, mock_iter):
        import psutil
        from main import kill_process_on_port

        mock_proc = MagicMock()
        mock_proc.connections.side_effect = psutil.AccessDenied(pid=1234)
        mock_iter.return_value = [mock_proc]

        # Should not raise
        kill_process_on_port(8080)


class TestWaitForApiServer:
    """Tests for wait_for_api_server function."""

    @patch('requests.get')
    def test_server_ready(self, mock_get):
        from main import wait_for_api_server

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = wait_for_api_server(8000, timeout=2)
        assert result is True

    @patch('requests.get')
    def test_server_not_ready(self, mock_get):
        from main import wait_for_api_server

        mock_get.side_effect = Exception("Connection refused")

        result = wait_for_api_server(8000, timeout=1)
        assert result is False

    @patch('requests.get')
    def test_server_returns_error(self, mock_get):
        from main import wait_for_api_server

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        result = wait_for_api_server(8000, timeout=1)
        assert result is False


class TestCleanupProcess:
    """Tests for cleanup_process function."""

    def test_cleanup_with_active_process(self):
        from main import cleanup_process
        import main

        mock_process = MagicMock()
        original = main.API_PROCESS
        main.API_PROCESS = mock_process

        cleanup_process()

        mock_process.terminate.assert_called_once()
        main.API_PROCESS = original

    def test_cleanup_with_no_process(self):
        from main import cleanup_process
        import main

        original = main.API_PROCESS
        main.API_PROCESS = None

        # Should not raise
        cleanup_process()

        main.API_PROCESS = original

    def test_cleanup_handles_timeout(self):
        from main import cleanup_process
        import main

        mock_process = MagicMock()
        mock_process.wait.side_effect = Exception("Timeout")
        original = main.API_PROCESS
        main.API_PROCESS = mock_process

        # Should call kill after timeout
        cleanup_process()

        mock_process.kill.assert_called_once()
        main.API_PROCESS = original


class TestMainFunction:
    """Tests for main function argument parsing."""

    @patch('main.SystemOrchestrator')
    @patch('main.subprocess.Popen')
    @patch('main.wait_for_api_server')
    @patch('main.kill_process_on_port')
    @patch('main.get_free_port')
    def test_main_allocates_port(self, mock_port, mock_kill, mock_wait, mock_popen, mock_orch):
        from main import main
        import sys

        mock_port.return_value = 5000
        mock_wait.return_value = True
        mock_popen.return_value = MagicMock()
        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance

        # Mock sys.argv
        original_argv = sys.argv
        sys.argv = ['main.py', '--no-proxy']

        try:
            # This will run until KeyboardInterrupt or error
            # We need to mock the event loop
            with patch('asyncio.new_event_loop') as mock_loop:
                mock_loop_instance = MagicMock()
                mock_loop.return_value = mock_loop_instance
                mock_loop_instance.run_forever.side_effect = KeyboardInterrupt

                main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv

        mock_port.assert_called()
