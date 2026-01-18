"""
Tests for core/connection_manager.py - Connection state management.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestConnectionManager:
    """Tests for ConnectionManager class."""

    def test_check_connection_soa_mode(self):
        from core.connection_manager import ConnectionManager

        # Create mock plugin context with SOA mode
        ctx = MagicMock()
        ctx.manifest.inference.execution_type = "none"

        result = ConnectionManager.check_connection(ctx)
        assert result is True

    def test_check_connection_with_alive_process(self):
        from core.connection_manager import ConnectionManager

        # Create mock plugin context with alive process
        ctx = MagicMock()
        ctx.manifest.inference.execution_type = "process"
        ctx.process = MagicMock()
        ctx.process.is_alive.return_value = True

        result = ConnectionManager.check_connection(ctx)
        assert result is True

    def test_check_connection_with_dead_process(self):
        from core.connection_manager import ConnectionManager

        ctx = MagicMock()
        ctx.manifest.inference.execution_type = "process"
        ctx.process = MagicMock()
        ctx.process.is_alive.return_value = False

        result = ConnectionManager.check_connection(ctx)
        assert result is False

    def test_check_connection_no_process(self):
        from core.connection_manager import ConnectionManager

        ctx = MagicMock()
        ctx.manifest.inference.execution_type = "process"
        ctx.process = None

        result = ConnectionManager.check_connection(ctx)
        assert result is False

    def test_check_connection_exception_handling(self):
        from core.connection_manager import ConnectionManager

        ctx = MagicMock()
        ctx.manifest.inference.execution_type = "process"
        ctx.process = MagicMock()
        ctx.process.is_alive.side_effect = Exception("Test error")

        result = ConnectionManager.check_connection(ctx)
        assert result is False

    def test_check_connection_no_inference_attribute(self):
        from core.connection_manager import ConnectionManager

        ctx = MagicMock()
        ctx.manifest.inference = None
        # Also need to set process to None to ensure False is returned
        ctx.process = None

        result = ConnectionManager.check_connection(ctx)
        # Should handle gracefully - returns False when no SOA mode and no process
        assert result is False


class TestConnectionManagerSingleton:
    """Tests for connection_manager singleton instance."""

    def test_singleton_exists(self):
        from core.connection_manager import connection_manager

        assert connection_manager is not None

    def test_singleton_has_check_method(self):
        from core.connection_manager import connection_manager

        assert hasattr(connection_manager, 'check_connection')
        assert callable(connection_manager.check_connection)
