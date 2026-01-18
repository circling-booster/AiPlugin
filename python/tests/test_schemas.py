"""
Tests for core/schemas.py - Pydantic schema validation.
"""
import pytest
from pydantic import ValidationError


class TestModelRequirement:
    """Tests for ModelRequirement schema."""

    def test_valid_model_requirement(self):
        from core.schemas import ModelRequirement

        model = ModelRequirement(
            key="YOLO_MODEL",
            filename="yolo_v8.pt",
            source_url="https://example.com/model.pt",
            sha256="abc123",
            description="YOLO model for detection"
        )
        assert model.key == "YOLO_MODEL"
        assert model.filename == "yolo_v8.pt"

    def test_model_requirement_optional_fields(self):
        from core.schemas import ModelRequirement

        model = ModelRequirement(key="TEST_MODEL", filename="test.pt")
        assert model.source_url is None
        assert model.sha256 is None
        assert model.description is None

    def test_model_requirement_missing_required(self):
        from core.schemas import ModelRequirement

        with pytest.raises(ValidationError):
            ModelRequirement(key="TEST")  # missing filename


class TestInferenceConfig:
    """Tests for InferenceConfig schema."""

    def test_default_values(self):
        from core.schemas import InferenceConfig

        config = InferenceConfig()
        assert config.supported_modes == ["local"]
        assert config.default_mode == "local"
        assert config.local_entry == "backend.py"
        assert config.web_entry == "web_backend.py"
        assert config.execution_type == "process"
        assert config.models == []

    def test_custom_values(self):
        from core.schemas import InferenceConfig

        config = InferenceConfig(
            supported_modes=["local", "web"],
            default_mode="web",
            execution_type="none"
        )
        assert "web" in config.supported_modes
        assert config.default_mode == "web"
        assert config.execution_type == "none"


class TestContentScript:
    """Tests for ContentScript schema."""

    def test_default_values(self):
        from core.schemas import ContentScript

        script = ContentScript()
        assert script.matches == ["<all_urls>"]
        assert script.js == ["content.js"]
        assert script.run_at == "document_end"
        assert script.all_frames is False

    def test_custom_values(self):
        from core.schemas import ContentScript

        script = ContentScript(
            matches=["*://*.google.com/*"],
            js=["script1.js", "script2.js"],
            run_at="document_start",
            all_frames=True
        )
        assert "*://*.google.com/*" in script.matches
        assert len(script.js) == 2
        assert script.run_at == "document_start"
        assert script.all_frames is True

    def test_invalid_run_at(self):
        from core.schemas import ContentScript

        with pytest.raises(ValidationError):
            ContentScript(run_at="invalid_value")


class TestRemoteUIConfig:
    """Tests for RemoteUIConfig schema."""

    def test_default_values(self):
        from core.schemas import RemoteUIConfig

        config = RemoteUIConfig()
        assert config.enabled is False
        assert config.entry_point == "web/index.html"
        assert config.title == "Plugin Controller"

    def test_enabled_config(self):
        from core.schemas import RemoteUIConfig

        config = RemoteUIConfig(
            enabled=True,
            entry_point="ui/panel.html",
            title="Custom Controller"
        )
        assert config.enabled is True
        assert config.entry_point == "ui/panel.html"


class TestPluginManifest:
    """Tests for PluginManifest schema."""

    def test_minimal_manifest(self):
        from core.schemas import PluginManifest

        manifest = PluginManifest(id="test_plugin")
        assert manifest.manifest_version == 3
        assert manifest.id == "test_plugin"
        assert manifest.name == "Unknown Plugin"

    def test_full_manifest(self, sample_plugin_manifest):
        from core.schemas import PluginManifest

        manifest = PluginManifest(**sample_plugin_manifest)
        assert manifest.id == "test_plugin"
        assert manifest.name == "Test Plugin"
        assert len(manifest.content_scripts) == 1
        assert manifest.inference.default_mode == "local"


class TestMatchRequest:
    """Tests for MatchRequest schema."""

    def test_valid_request(self):
        from core.schemas import MatchRequest

        req = MatchRequest(url="https://example.com/page")
        assert req.url == "https://example.com/page"

    def test_missing_url(self):
        from core.schemas import MatchRequest

        with pytest.raises(ValidationError):
            MatchRequest()


class TestMatchResponse:
    """Tests for MatchResponse schema."""

    def test_empty_scripts(self):
        from core.schemas import MatchResponse

        resp = MatchResponse(scripts=[])
        assert resp.scripts == []

    def test_with_scripts(self):
        from core.schemas import MatchResponse, ScriptInjection

        scripts = [
            ScriptInjection(url="http://localhost/script.js", run_at="document_end")
        ]
        resp = MatchResponse(scripts=scripts)
        assert len(resp.scripts) == 1


class TestInferenceRequest:
    """Tests for InferenceRequest schema."""

    def test_valid_request(self):
        from core.schemas import InferenceRequest

        req = InferenceRequest(model_id="MODEL_MELON", data={"image": "base64data"})
        assert req.model_id == "MODEL_MELON"
        assert "image" in req.data


class TestInferenceResponse:
    """Tests for InferenceResponse schema."""

    def test_success_response(self):
        from core.schemas import InferenceResponse

        resp = InferenceResponse(
            status="success",
            result={"text": "ABCD"},
            confidence=0.95,
            processing_time_ms=45.2
        )
        assert resp.status == "success"
        assert resp.confidence == 0.95

    def test_error_response(self):
        from core.schemas import InferenceResponse

        resp = InferenceResponse(status="error", message="Model not found")
        assert resp.status == "error"
        assert resp.message == "Model not found"


class TestErrorResponse:
    """Tests for ErrorResponse schema."""

    def test_default_error(self):
        from core.schemas import ErrorResponse

        err = ErrorResponse(message="Something went wrong")
        assert err.status == "error"
        assert err.code == 500

    def test_custom_error(self):
        from core.schemas import ErrorResponse

        err = ErrorResponse(message="Not found", code=404)
        assert err.code == 404
