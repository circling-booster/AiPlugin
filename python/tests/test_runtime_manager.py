"""
Tests for core/runtime_manager.py - Plugin runtime management.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestRuntimeManager:
    """Tests for RuntimeManager class."""

    @patch('core.runtime_manager.plugin_loader')
    @patch('core.runtime_manager.connection_manager')
    def test_ensure_process_running_plugin_not_found(self, mock_conn, mock_loader):
        from core.runtime_manager import RuntimeManager

        mock_loader.get_plugin.return_value = None

        manager = RuntimeManager()

        with pytest.raises(ValueError, match="not found"):
            manager.ensure_process_running("nonexistent_plugin")

    @patch('core.runtime_manager.plugin_loader')
    @patch('core.runtime_manager.connection_manager')
    def test_ensure_process_already_running(self, mock_conn, mock_loader):
        from core.runtime_manager import RuntimeManager

        mock_ctx = MagicMock()
        mock_loader.get_plugin.return_value = mock_ctx
        mock_conn.check_connection.return_value = True

        manager = RuntimeManager()
        manager.ensure_process_running("test_plugin")

        # Should return early without spawning
        mock_conn.check_connection.assert_called_once()

    @patch('core.runtime_manager.plugin_loader')
    @patch('core.runtime_manager.connection_manager')
    @patch('core.runtime_manager.WorkerManager')
    def test_ensure_process_spawns_worker(self, mock_worker, mock_conn, mock_loader):
        from core.runtime_manager import RuntimeManager

        mock_ctx = MagicMock()
        mock_ctx.manifest.id = "test_plugin"
        mock_ctx.manifest.inference.execution_type = "process"
        mock_ctx.manifest.inference.local_entry = "backend.py"
        mock_ctx.path = "/path/to/plugin"
        mock_loader.get_plugin.return_value = mock_ctx
        mock_conn.check_connection.return_value = False

        mock_process = MagicMock()
        mock_connection = MagicMock()
        mock_worker.spawn_worker.return_value = (mock_process, mock_connection)

        manager = RuntimeManager()
        manager.ensure_process_running("test_plugin")

        mock_worker.spawn_worker.assert_called_once()
        assert mock_ctx.process == mock_process
        assert mock_ctx.connection == mock_connection

    @patch('core.runtime_manager.plugin_loader')
    @patch('core.runtime_manager.connection_manager')
    @patch('core.runtime_manager.WorkerManager')
    def test_ensure_process_soa_mode(self, mock_worker, mock_conn, mock_loader):
        from core.runtime_manager import RuntimeManager

        mock_ctx = MagicMock()
        mock_ctx.manifest.id = "test_plugin"
        mock_ctx.manifest.inference.execution_type = "none"
        mock_ctx.manifest.inference.local_entry = "backend.py"
        mock_ctx.path = "/path/to/plugin"
        mock_loader.get_plugin.return_value = mock_ctx
        mock_conn.check_connection.return_value = False

        mock_process = MagicMock()
        mock_worker.spawn_worker.return_value = (mock_process, None)

        manager = RuntimeManager()
        manager.ensure_process_running("test_plugin")

        assert mock_ctx.mode == "soa"

    @patch('core.runtime_manager.plugin_loader')
    @patch('core.runtime_manager.connection_manager')
    @patch('core.runtime_manager.WorkerManager')
    def test_ensure_process_spawn_failure(self, mock_worker, mock_conn, mock_loader):
        from core.runtime_manager import RuntimeManager

        mock_ctx = MagicMock()
        mock_ctx.manifest.id = "test_plugin"
        mock_ctx.manifest.inference.execution_type = "process"
        mock_ctx.manifest.inference.local_entry = "backend.py"
        mock_ctx.path = "/path/to/plugin"
        mock_loader.get_plugin.return_value = mock_ctx
        mock_conn.check_connection.return_value = False

        mock_worker.spawn_worker.return_value = (None, None)

        manager = RuntimeManager()

        with pytest.raises(RuntimeError, match="Failed to start runtime"):
            manager.ensure_process_running("test_plugin")


class TestRuntimeManagerSingleton:
    """Tests for runtime_manager singleton."""

    def test_singleton_exists(self):
        from core.runtime_manager import runtime_manager

        assert runtime_manager is not None

    def test_singleton_has_method(self):
        from core.runtime_manager import runtime_manager

        assert hasattr(runtime_manager, 'ensure_process_running')
