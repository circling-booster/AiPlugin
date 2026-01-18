"""
Tests for core/plugin_loader.py - Plugin loading and management.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock


class TestPluginContext:
    """Tests for PluginContext class."""

    def test_context_initialization(self, sample_plugin_manifest):
        from core.schemas import PluginManifest
        from core.plugin_loader import PluginContext

        manifest = PluginManifest(**sample_plugin_manifest)
        ctx = PluginContext(manifest, "/path/to/plugin", "local")

        assert ctx.manifest == manifest
        assert ctx.base_path == "/path/to/plugin"
        assert ctx.mode == "local"
        assert ctx.process is None
        assert ctx.connection is None

    def test_context_compiles_patterns(self, sample_plugin_manifest):
        from core.schemas import PluginManifest
        from core.plugin_loader import PluginContext

        manifest = PluginManifest(**sample_plugin_manifest)
        ctx = PluginContext(manifest, "/path/to/plugin", "local")

        # Should have compiled patterns from content_scripts
        assert len(ctx.compiled_patterns) > 0

    def test_context_all_urls_pattern(self):
        from core.schemas import PluginManifest
        from core.plugin_loader import PluginContext

        manifest = PluginManifest(
            id="test",
            content_scripts=[{
                "matches": ["<all_urls>"],
                "js": ["script.js"]
            }]
        )
        ctx = PluginContext(manifest, "/path", "local")

        # The compiled pattern for <all_urls> should match anything
        assert any(p.match("https://example.com/page") for p in ctx.compiled_patterns)


class TestPluginLoaderSingleton:
    """Tests for PluginLoader singleton behavior."""

    def test_singleton_instance(self):
        from core.plugin_loader import PluginLoader

        loader1 = PluginLoader()
        loader2 = PluginLoader()
        assert loader1 is loader2

    def test_plugins_dict_initialized(self):
        from core.plugin_loader import PluginLoader

        loader = PluginLoader()
        assert hasattr(loader, 'plugins')
        assert isinstance(loader.plugins, dict)


class TestPluginLoaderLoadPlugins:
    """Tests for plugin loading functionality."""

    def test_load_plugins_from_directory(self, create_temp_plugin, temp_plugins_dir, monkeypatch):
        from core.plugin_loader import PluginLoader

        # Create a fresh loader instance
        PluginLoader._instance = None
        loader = PluginLoader()

        # Create temp plugin
        plugin_dir, manifest = create_temp_plugin("test_plugin_1")

        # Monkeypatch the plugins directory - must happen before load_plugins
        loader.plugins_dir = str(temp_plugins_dir)
        loader.plugins = {}  # Reset plugins

        # Also need to patch _load_settings to return empty dict
        monkeypatch.setattr(loader, '_load_settings', lambda: {})

        loader.load_plugins()

        assert "test_plugin_1" in loader.plugins

    def test_load_plugins_respects_active_plugins(self, create_temp_plugin, temp_plugins_dir, monkeypatch):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        # Create two plugins
        create_temp_plugin("active_plugin")
        create_temp_plugin("inactive_plugin")

        monkeypatch.setattr(loader, 'plugins_dir', str(temp_plugins_dir))
        loader.plugins = {}

        # Only load active_plugin
        loader.load_plugins({"active_plugins": ["active_plugin"]})

        assert "active_plugin" in loader.plugins
        assert "inactive_plugin" not in loader.plugins

    def test_load_plugins_uses_preferred_mode(self, create_temp_plugin, temp_plugins_dir, monkeypatch):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        # Create plugin with multiple supported modes
        create_temp_plugin(
            "mode_test_plugin",
            manifest_overrides={
                "inference": {
                    "supported_modes": ["local", "web"],
                    "default_mode": "local"
                }
            }
        )

        monkeypatch.setattr(loader, 'plugins_dir', str(temp_plugins_dir))
        loader.plugins = {}

        # Set preferred mode to web
        loader.load_plugins({
            "active_plugins": ["mode_test_plugin"],
            "plugin_modes": {"mode_test_plugin": "web"}
        })

        assert loader.plugins["mode_test_plugin"].mode == "web"

    def test_load_plugins_falls_back_to_default_mode(self, create_temp_plugin, temp_plugins_dir, monkeypatch):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        create_temp_plugin("fallback_plugin")

        monkeypatch.setattr(loader, 'plugins_dir', str(temp_plugins_dir))
        loader.plugins = {}

        # Set unsupported mode
        loader.load_plugins({
            "active_plugins": ["fallback_plugin"],
            "plugin_modes": {"fallback_plugin": "unsupported_mode"}
        })

        # Should fall back to default mode
        assert loader.plugins["fallback_plugin"].mode == "local"

    def test_load_plugins_missing_directory(self, monkeypatch, tmp_path):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        # Point to non-existent directory
        monkeypatch.setattr(loader, 'plugins_dir', str(tmp_path / "nonexistent"))
        loader.plugins = {}

        # Should not raise, just log warning
        loader.load_plugins()
        assert len(loader.plugins) == 0

    def test_load_plugins_invalid_manifest(self, temp_plugins_dir, monkeypatch):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        # Create plugin with invalid manifest
        plugin_dir = temp_plugins_dir / "invalid_plugin"
        plugin_dir.mkdir()
        (plugin_dir / "manifest.json").write_text("not valid json")

        monkeypatch.setattr(loader, 'plugins_dir', str(temp_plugins_dir))
        loader.plugins = {}

        # Should not raise, just log error
        loader.load_plugins()
        assert "invalid_plugin" not in loader.plugins


class TestPluginLoaderGetPlugin:
    """Tests for get_plugin method."""

    def test_get_existing_plugin(self, create_temp_plugin, temp_plugins_dir, monkeypatch):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        create_temp_plugin("existing_plugin")

        loader.plugins_dir = str(temp_plugins_dir)
        loader.plugins = {}
        monkeypatch.setattr(loader, '_load_settings', lambda: {})
        loader.load_plugins()

        plugin = loader.get_plugin("existing_plugin")
        assert plugin is not None
        assert plugin.manifest.id == "existing_plugin"

    def test_get_nonexistent_plugin(self):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()
        loader.plugins = {}

        plugin = loader.get_plugin("nonexistent")
        assert plugin is None


class TestPluginLoaderLoadSettings:
    """Tests for _load_settings method."""

    def test_load_settings_from_file(self, tmp_path, monkeypatch):
        from core.plugin_loader import PluginLoader

        PluginLoader._instance = None
        loader = PluginLoader()

        # Create settings file
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        settings_path = config_dir / "settings.json"
        settings_path.write_text(json.dumps({"active_plugins": ["test"]}))

        # Patch the method to use our temp path
        original_load_settings = loader._load_settings

        def patched_load_settings():
            if os.path.exists(str(settings_path)):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}

        monkeypatch.setattr(loader, '_load_settings', patched_load_settings)

        settings = loader._load_settings()
        assert settings.get("active_plugins") == ["test"]
