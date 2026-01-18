"""
Tests for core/inference_router.py - Inference request routing.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestGetCloudConfig:
    """Tests for get_cloud_config function."""

    def test_returns_empty_without_config(self):
        from core.inference_router import get_cloud_config

        with patch('os.path.abspath', return_value="/nonexistent/config.json"):
            with patch('builtins.open', side_effect=FileNotFoundError):
                config = get_cloud_config()

        # Should return empty dict (or dict with env vars if set)
        assert isinstance(config, dict)

    @patch.dict('os.environ', {'SYSTEM_API_KEY': 'test-key', 'CLOUD_BASE_URL': 'http://test.com'})
    def test_uses_env_vars(self):
        from core.inference_router import get_cloud_config

        with patch('builtins.open', side_effect=FileNotFoundError):
            config = get_cloud_config()

        assert config.get('system_api_key') == 'test-key'
        assert config.get('base_url') == 'http://test.com'


class TestCommunicateIPC:
    """Tests for _communicate_ipc helper function."""

    @patch('core.inference_router.runtime_manager')
    def test_communicate_success(self, mock_runtime):
        from core.inference_router import _communicate_ipc

        # Setup mock context
        ctx = MagicMock()
        ctx.manifest.id = "test_plugin"
        ctx.connection = MagicMock()
        ctx.connection.poll.return_value = True
        ctx.connection.recv.return_value = {"status": "success", "result": "data"}

        result = _communicate_ipc(ctx, {"input": "test"})

        assert result["status"] == "success"
        ctx.connection.send.assert_called_once()
        mock_runtime.ensure_process_running.assert_called_once()

    @patch('core.inference_router.runtime_manager')
    def test_communicate_timeout(self, mock_runtime):
        from core.inference_router import _communicate_ipc

        ctx = MagicMock()
        ctx.manifest.id = "test_plugin"
        ctx.connection = MagicMock()
        ctx.connection.poll.return_value = False  # Timeout

        result = _communicate_ipc(ctx, {"input": "test"})

        assert result["status"] == "error"
        assert "Timeout" in result["message"]

    @patch('core.inference_router.runtime_manager')
    def test_communicate_no_connection(self, mock_runtime):
        from core.inference_router import _communicate_ipc

        ctx = MagicMock()
        ctx.manifest.id = "test_plugin"
        ctx.connection = None

        with pytest.raises(RuntimeError):
            _communicate_ipc(ctx, {"input": "test"})


class TestInferenceEndpoint:
    """Tests for /v1/inference endpoint."""

    @pytest.fixture
    def mock_dependencies(self):
        with patch('core.inference_router.plugin_loader') as mock_loader, \
             patch('core.inference_router.runtime_manager') as mock_runtime, \
             patch('core.inference_router.ai_engine') as mock_engine:
            yield {
                'loader': mock_loader,
                'runtime': mock_runtime,
                'engine': mock_engine
            }

    @pytest.mark.asyncio
    async def test_inference_plugin_not_found(self, mock_dependencies):
        from core.inference_router import inference_endpoint
        from fastapi import HTTPException

        mock_dependencies['loader'].get_plugin.return_value = None

        mock_request = AsyncMock()
        mock_request.json.return_value = {"payload": {"data": "test"}}

        with pytest.raises(HTTPException) as exc_info:
            await inference_endpoint("nonexistent", "predict", mock_request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_inference_web_mode(self, mock_dependencies):
        from core.inference_router import inference_endpoint

        # Setup mock plugin in web mode
        mock_ctx = MagicMock()
        mock_ctx.mode = "web"
        mock_dependencies['loader'].get_plugin.return_value = mock_ctx

        mock_request = AsyncMock()
        mock_request.json.return_value = {"payload": {"image": "base64"}}

        with patch('core.inference_router.get_cloud_config') as mock_config, \
             patch('core.inference_router.httpx.AsyncClient') as mock_client:
            mock_config.return_value = {
                'base_url': 'http://cloud.test',
                'system_api_key': 'test-key'
            }

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success"}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance

            result = await inference_endpoint("test_plugin", "predict", mock_request)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_inference_local_soa_mode(self, mock_dependencies):
        from core.inference_router import inference_endpoint
        from fastapi.concurrency import run_in_threadpool

        # Setup mock plugin in local/SOA mode
        mock_ctx = MagicMock()
        mock_ctx.mode = "local"
        mock_ctx.manifest.inference.execution_type = "none"
        mock_dependencies['loader'].get_plugin.return_value = mock_ctx

        mock_dependencies['engine'].process_request.return_value = {
            "status": "success",
            "predicted_text": "TEST"
        }

        mock_request = AsyncMock()
        mock_request.json.return_value = {
            "payload": {"image": "base64", "model_id": "MODEL_MELON"}
        }

        with patch('core.inference_router.run_in_threadpool', new_callable=AsyncMock) as mock_threadpool:
            mock_threadpool.return_value = {"status": "success", "predicted_text": "TEST"}

            result = await inference_endpoint("test_plugin", "predict", mock_request)

            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_inference_local_process_mode(self, mock_dependencies):
        from core.inference_router import inference_endpoint

        mock_ctx = MagicMock()
        mock_ctx.mode = "local"
        mock_ctx.manifest.inference.execution_type = "process"
        mock_dependencies['loader'].get_plugin.return_value = mock_ctx

        mock_request = AsyncMock()
        mock_request.json.return_value = {"payload": {"data": "test"}}

        with patch('core.inference_router.run_in_threadpool', new_callable=AsyncMock) as mock_threadpool:
            mock_threadpool.return_value = {"status": "success"}

            result = await inference_endpoint("test_plugin", "predict", mock_request)

            assert result["status"] == "success"


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_router_exists(self):
        from core.inference_router import router

        assert router is not None

    def test_router_has_inference_route(self):
        from core.inference_router import router

        routes = [r.path for r in router.routes]
        assert any('/inference' in r for r in routes)
