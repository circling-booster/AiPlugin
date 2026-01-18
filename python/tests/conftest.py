"""
Pytest configuration and shared fixtures for AiPlugs tests.
"""
import os
import sys
import pytest
import tempfile
import json
from unittest.mock import MagicMock, patch

# Add python directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def temp_plugins_dir(tmp_path):
    """Create a temporary plugins directory with a sample plugin."""
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    return plugins_dir


@pytest.fixture
def sample_plugin_manifest():
    """Return a sample plugin manifest dictionary."""
    return {
        "manifest_version": 3,
        "id": "test_plugin",
        "name": "Test Plugin",
        "description": "A test plugin for unit tests",
        "author": "Test Author",
        "requirements": {},
        "inference": {
            "supported_modes": ["local", "web"],
            "default_mode": "local",
            "local_entry": "backend.py",
            "web_entry": "web_backend.py",
            "execution_type": "process",
            "models": []
        },
        "host_permissions": ["*://*.example.com/*"],
        "content_scripts": [
            {
                "matches": ["*://*.example.com/*", "<all_urls>"],
                "js": ["content.js"],
                "run_at": "document_end",
                "all_frames": False
            }
        ],
        "remote_ui": {
            "enabled": False,
            "entry_point": "web/index.html",
            "title": "Test Controller"
        }
    }


@pytest.fixture
def create_temp_plugin(temp_plugins_dir, sample_plugin_manifest):
    """Create a temporary plugin directory with manifest and dummy files."""
    def _create(plugin_id=None, manifest_overrides=None):
        manifest = sample_plugin_manifest.copy()
        if plugin_id:
            manifest["id"] = plugin_id
        if manifest_overrides:
            manifest.update(manifest_overrides)

        plugin_dir = temp_plugins_dir / manifest["id"]
        plugin_dir.mkdir()

        # Write manifest
        with open(plugin_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Create dummy content.js
        (plugin_dir / "content.js").write_text("console.log('test');")

        # Create dummy backend.py
        (plugin_dir / "backend.py").write_text("def run(data): return {'status': 'ok'}")

        return plugin_dir, manifest

    return _create


@pytest.fixture
def mock_mitmproxy_flow():
    """Create a mock mitmproxy flow object."""
    flow = MagicMock()
    flow.request.url = "https://example.com/page"
    flow.request.headers = {
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate"
    }
    flow.response.headers = {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": "default-src 'self'"
    }
    flow.response.text = "<html><head></head><body>Test</body></html>"
    flow.response.content = b"<html><head></head><body>Test</body></html>"
    flow.response.decode = MagicMock()
    return flow


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_settings():
    """Return sample settings dictionary."""
    return {
        "active_plugins": ["test_plugin"],
        "plugin_modes": {
            "test_plugin": "local"
        },
        "system_mode": "dual"
    }


@pytest.fixture
def sample_config():
    """Return sample config dictionary."""
    return {
        "system_settings": {
            "ai_engine": {
                "host": "127.0.0.1",
                "port": 8000
            },
            "cloud_inference": {
                "base_url": "http://cloud.example.com",
                "system_api_key": "test-key"
            }
        }
    }
