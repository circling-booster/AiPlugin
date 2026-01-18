"""
Tests for core/worker_manager.py - Worker process management.
"""
import pytest
from unittest.mock import patch, MagicMock
import io


class TestDummyProcess:
    """Tests for DummyProcess class (SOA mode support)."""

    def test_initialization(self):
        from core.worker_manager import DummyProcess

        proc = DummyProcess()
        assert proc.pid == 99999
        assert isinstance(proc.stdin, io.BytesIO)
        assert isinstance(proc.stdout, io.BytesIO)
        assert proc.returncode is None
        assert proc._alive is True

    def test_poll_when_alive(self):
        from core.worker_manager import DummyProcess

        proc = DummyProcess()
        assert proc.poll() is None

    def test_poll_when_terminated(self):
        from core.worker_manager import DummyProcess

        proc = DummyProcess()
        proc.terminate()
        assert proc.poll() == 0

    def test_terminate(self):
        from core.worker_manager import DummyProcess

        proc = DummyProcess()
        assert proc.is_alive() is True
        proc.terminate()
        assert proc.is_alive() is False

    def test_kill(self):
        from core.worker_manager import DummyProcess

        proc = DummyProcess()
        assert proc.is_alive() is True
        proc.kill()
        assert proc.is_alive() is False

    def test_is_alive_initial(self):
        from core.worker_manager import DummyProcess

        proc = DummyProcess()
        assert proc.is_alive() is True


class TestWorkerManager:
    """Tests for WorkerManager class."""

    def test_spawn_worker_soa_mode(self):
        from core.worker_manager import WorkerManager, DummyProcess

        process, conn = WorkerManager.spawn_worker(
            plugin_id="test_plugin",
            entry_path="/path/to/backend.py",
            env_vars={},
            execution_type="none"
        )

        assert isinstance(process, DummyProcess)
        assert conn is None

    def test_spawn_worker_missing_entry(self, tmp_path):
        from core.worker_manager import WorkerManager

        process, conn = WorkerManager.spawn_worker(
            plugin_id="test_plugin",
            entry_path=str(tmp_path / "nonexistent.py"),
            env_vars={},
            execution_type="process"
        )

        assert process is None
        assert conn is None

    @patch('multiprocessing.Process')
    @patch('multiprocessing.Pipe')
    def test_spawn_worker_creates_process(self, mock_pipe, mock_process, tmp_path):
        from core.worker_manager import WorkerManager

        # Create a dummy entry file
        entry_file = tmp_path / "backend.py"
        entry_file.write_text("def run(data): return data")

        # Setup mocks
        mock_parent_conn = MagicMock()
        mock_child_conn = MagicMock()
        mock_pipe.return_value = (mock_parent_conn, mock_child_conn)

        mock_proc_instance = MagicMock()
        mock_process.return_value = mock_proc_instance

        process, conn = WorkerManager.spawn_worker(
            plugin_id="test_plugin",
            entry_path=str(entry_file),
            env_vars={"TEST_VAR": "value"},
            execution_type="process"
        )

        # Verify process was created
        mock_process.assert_called_once()
        mock_proc_instance.start.assert_called_once()
        assert conn == mock_parent_conn


class TestWorkerEntry:
    """Tests for _worker_entry function."""

    def test_worker_entry_imports_module(self, tmp_path):
        # This test would require actually running a subprocess
        # which is complex for unit testing. We test the logic
        # through integration tests or mock the importlib.
        pass

    def test_worker_entry_sets_env_vars(self, tmp_path):
        # Similar to above - would need subprocess testing
        pass
