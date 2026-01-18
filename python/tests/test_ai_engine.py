"""
Tests for core/ai_engine.py - AI inference engine.
Note: These tests use mocking extensively since actual PyTorch inference requires GPU/model files.
"""
import pytest
import os
from unittest.mock import patch, MagicMock


class TestAIEngineConfiguration:
    """Tests for AI Engine configuration constants."""

    def test_supported_models_defined(self):
        from core.ai_engine import SUPPORTED_MODELS

        assert "MODEL_MELON" in SUPPORTED_MODELS
        assert "MODEL_NOL" in SUPPORTED_MODELS

    def test_model_melon_config(self):
        from core.ai_engine import SUPPORTED_MODELS

        melon = SUPPORTED_MODELS["MODEL_MELON"]
        assert melon["width"] == 230
        assert melon["height"] == 70
        assert melon["filename"] == "model_melon.pt"

    def test_model_nol_config(self):
        from core.ai_engine import SUPPORTED_MODELS

        nol = SUPPORTED_MODELS["MODEL_NOL"]
        assert nol["width"] == 210
        assert nol["height"] == 70

    def test_alphabet_configuration(self):
        from core.ai_engine import ALPHABETS, NUM_CLASSES, BLANK_LABEL

        assert ALPHABETS == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        assert NUM_CLASSES == 26
        assert BLANK_LABEL == 26

    def test_idx_to_char_mapping(self):
        from core.ai_engine import IDX_TO_CHAR

        assert IDX_TO_CHAR[0] == 'A'
        assert IDX_TO_CHAR[25] == 'Z'
        assert len(IDX_TO_CHAR) == 26


class TestAIEngineInitialization:
    """Tests for AIEngine class initialization."""

    @patch('concurrent.futures.ProcessPoolExecutor')
    def test_engine_initialization(self, mock_executor):
        from core.ai_engine import AIEngine

        engine = AIEngine()

        assert engine.executor is not None
        mock_executor.assert_called_once_with(max_workers=1)

    @patch('concurrent.futures.ProcessPoolExecutor')
    def test_engine_sets_model_dir(self, mock_executor):
        from core.ai_engine import AIEngine

        engine = AIEngine()

        assert hasattr(engine, 'MODEL_DIR')
        assert 'models' in engine.MODEL_DIR


class TestAIEngineProcessRequest:
    """Tests for AIEngine.process_request method."""

    @patch('concurrent.futures.ProcessPoolExecutor')
    def test_process_request_no_image(self, mock_executor):
        from core.ai_engine import AIEngine

        engine = AIEngine()
        result = engine.process_request("MODEL_MELON", {})

        assert result["status"] == "error"
        assert "No image data" in result["message"]

    @patch('concurrent.futures.ProcessPoolExecutor')
    def test_process_request_with_image(self, mock_executor):
        from core.ai_engine import AIEngine

        # Mock the executor and future
        mock_future = MagicMock()
        mock_future.result.return_value = {
            "status": "success",
            "predicted_text": "ABCD",
            "confidence": 0.95
        }
        mock_executor_instance = MagicMock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        engine = AIEngine()
        result = engine.process_request("MODEL_MELON", {"image": "base64data"})

        assert result["status"] == "success"
        mock_executor_instance.submit.assert_called_once()

    @patch('concurrent.futures.ProcessPoolExecutor')
    def test_process_request_handles_exception(self, mock_executor):
        from core.ai_engine import AIEngine

        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("Process failed")
        mock_executor_instance = MagicMock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor.return_value = mock_executor_instance

        engine = AIEngine()
        result = engine.process_request("MODEL_MELON", {"image": "base64data"})

        assert result["status"] == "error"


class TestWorkerFunctions:
    """Tests for worker process helper functions."""

    def test_get_worker_device_returns_device(self):
        # Skip if torch not available
        pytest.importorskip("torch")
        from core.ai_engine import _get_worker_device

        device = _get_worker_device()
        assert device is not None

    @patch('core.ai_engine.HAS_DEPS', False)
    def test_load_model_no_deps(self, tmp_path):
        from core.ai_engine import _load_model_in_worker

        with pytest.raises(ImportError):
            _load_model_in_worker("MODEL_MELON", str(tmp_path))


class TestCRNNModel:
    """Tests for CRNN model architecture (if torch available)."""

    @pytest.mark.skipif(
        not pytest.importorskip("torch", reason="PyTorch not installed"),
        reason="PyTorch not available"
    )
    def test_crnn_initialization(self):
        try:
            from core.ai_engine import CRNN, NUM_CLASSES

            model = CRNN(img_h=70, num_classes=NUM_CLASSES)
            assert model is not None
        except NameError:
            # CRNN not defined if HAS_DEPS is False
            pytest.skip("CRNN not available (HAS_DEPS=False)")

    @pytest.mark.skipif(
        not pytest.importorskip("torch", reason="PyTorch not installed"),
        reason="PyTorch not available"
    )
    def test_crnn_forward_pass(self):
        try:
            import torch
            from core.ai_engine import CRNN, NUM_CLASSES

            model = CRNN(img_h=70, num_classes=NUM_CLASSES)
            model.eval()

            # Create dummy input (batch=1, channels=1, height=70, width=230)
            dummy_input = torch.randn(1, 1, 70, 230)

            with torch.no_grad():
                output = model(dummy_input)

            # Output should have shape (seq_length, batch, num_classes+1)
            assert output.dim() == 3
        except NameError:
            pytest.skip("CRNN not available (HAS_DEPS=False)")
