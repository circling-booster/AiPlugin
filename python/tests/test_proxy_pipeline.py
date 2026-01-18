"""
Tests for core/proxy_pipeline.py - HTTP proxy pipeline handlers.
"""
import pytest
from unittest.mock import MagicMock, patch


class TestProxyHandler:
    """Tests for base ProxyHandler class."""

    def test_default_process_returns_true(self):
        from core.proxy_pipeline import ProxyHandler

        handler = ProxyHandler()
        flow = MagicMock()
        context = {}

        result = handler.process(flow, context)
        assert result is True


class TestContentTypeFilter:
    """Tests for ContentTypeFilter handler."""

    def test_allows_html_content(self):
        from core.proxy_pipeline import ContentTypeFilter

        handler = ContentTypeFilter()
        flow = MagicMock()
        flow.response.headers = {"Content-Type": "text/html; charset=utf-8"}
        context = {}

        result = handler.process(flow, context)
        assert result is True

    def test_blocks_json_content(self):
        from core.proxy_pipeline import ContentTypeFilter

        handler = ContentTypeFilter()
        flow = MagicMock()
        flow.response.headers = {"Content-Type": "application/json"}
        context = {}

        result = handler.process(flow, context)
        assert result is False

    def test_blocks_image_content(self):
        from core.proxy_pipeline import ContentTypeFilter

        handler = ContentTypeFilter()
        flow = MagicMock()
        flow.response.headers = {"Content-Type": "image/png"}
        context = {}

        result = handler.process(flow, context)
        assert result is False

    def test_allows_html_with_partial_match(self):
        from core.proxy_pipeline import ContentTypeFilter

        handler = ContentTypeFilter()
        flow = MagicMock()
        flow.response.headers = {"Content-Type": "text/html"}
        context = {}

        result = handler.process(flow, context)
        assert result is True

    def test_handles_missing_content_type(self):
        from core.proxy_pipeline import ContentTypeFilter

        handler = ContentTypeFilter()
        flow = MagicMock()
        flow.response.headers = {}
        context = {}

        result = handler.process(flow, context)
        assert result is False


class TestResourceFilter:
    """Tests for ResourceFilter handler."""

    def test_blocks_empty_fetch_dest(self):
        from core.proxy_pipeline import ResourceFilter

        handler = ResourceFilter()
        flow = MagicMock()
        flow.request.headers = {"Sec-Fetch-Dest": "empty"}
        context = {}

        result = handler.process(flow, context)
        assert result is False

    def test_blocks_cors_mode(self):
        from core.proxy_pipeline import ResourceFilter

        handler = ResourceFilter()
        flow = MagicMock()
        flow.request.headers = {"Sec-Fetch-Mode": "cors"}
        context = {}

        result = handler.process(flow, context)
        assert result is False

    def test_blocks_websocket_mode(self):
        from core.proxy_pipeline import ResourceFilter

        handler = ResourceFilter()
        flow = MagicMock()
        flow.request.headers = {"Sec-Fetch-Mode": "websocket"}
        context = {}

        result = handler.process(flow, context)
        assert result is False

    def test_allows_navigate_mode(self):
        from core.proxy_pipeline import ResourceFilter

        handler = ResourceFilter()
        flow = MagicMock()
        flow.request.headers = {
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate"
        }
        context = {}

        result = handler.process(flow, context)
        assert result is True

    def test_marks_iframe_in_context(self):
        from core.proxy_pipeline import ResourceFilter

        handler = ResourceFilter()
        flow = MagicMock()
        flow.request.headers = {
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate"
        }
        context = {}

        handler.process(flow, context)
        assert context.get('is_iframe') is True

    def test_no_headers_allows_through(self):
        from core.proxy_pipeline import ResourceFilter

        handler = ResourceFilter()
        flow = MagicMock()
        flow.request.headers = {}
        context = {}

        result = handler.process(flow, context)
        assert result is True


class TestDecoder:
    """Tests for Decoder handler."""

    def test_decodes_response(self):
        from core.proxy_pipeline import Decoder

        handler = Decoder()
        flow = MagicMock()
        context = {}

        result = handler.process(flow, context)

        flow.response.decode.assert_called_once()
        assert context['decoded'] is True
        assert result is True


class TestPluginMatcher:
    """Tests for PluginMatcher handler."""

    @patch('core.proxy_pipeline.plugin_loader')
    def test_matches_plugins_to_url(self, mock_loader):
        from core.proxy_pipeline import PluginMatcher

        # Setup mock plugin
        mock_ctx = MagicMock()
        mock_ctx.manifest.content_scripts = [
            MagicMock(matches=["<all_urls>"])
        ]
        mock_loader.plugins = {"test_plugin": mock_ctx}

        handler = PluginMatcher()
        flow = MagicMock()
        flow.request.url = "https://example.com/page"
        context = {}

        with patch('core.proxy_pipeline.UrlMatcher') as mock_matcher:
            mock_matcher.match.return_value = True
            result = handler.process(flow, context)

        assert result is True
        assert "test_plugin" in context.get('matched_pids', [])

    @patch('core.proxy_pipeline.plugin_loader')
    def test_no_matching_plugins(self, mock_loader):
        from core.proxy_pipeline import PluginMatcher

        mock_ctx = MagicMock()
        mock_ctx.manifest.content_scripts = [
            MagicMock(matches=["https://specific.com/*"])
        ]
        mock_loader.plugins = {"test_plugin": mock_ctx}

        handler = PluginMatcher()
        flow = MagicMock()
        flow.request.url = "https://other.com/page"
        context = {}

        with patch('core.proxy_pipeline.UrlMatcher') as mock_matcher:
            mock_matcher.match.return_value = False
            result = handler.process(flow, context)

        assert result is True
        assert context.get('matched_pids', []) == []


class TestInjector:
    """Tests for Injector handler."""

    def test_initialization(self):
        from core.proxy_pipeline import Injector

        handler = Injector(api_port=8000)
        assert handler.api_port == 8000

    @patch('core.proxy_pipeline.plugin_loader')
    @patch('core.proxy_pipeline.get_loader_script')
    def test_injects_scripts_for_matched_plugins(self, mock_loader_script, mock_loader):
        from core.proxy_pipeline import Injector

        mock_loader_script.return_value = b"<script>loader</script>"

        mock_ctx = MagicMock()
        mock_ctx.manifest.content_scripts = [
            MagicMock(
                matches=["<all_urls>"],
                js=["content.js"],
                all_frames=False
            )
        ]
        mock_loader.get_plugin.return_value = mock_ctx

        handler = Injector(api_port=8000)
        flow = MagicMock()
        flow.request.url = "https://example.com/page"
        flow.response.text = "<html><body>Content</body></html>"
        flow.response.headers = {"Cache-Control": "max-age=3600"}
        context = {'matched_pids': ['test_plugin']}

        with patch('core.proxy_pipeline.UrlMatcher') as mock_matcher:
            mock_matcher.match.return_value = True
            result = handler.process(flow, context)

        assert result is True
        assert context.get('injected') is True

    def test_no_injection_without_matches(self):
        from core.proxy_pipeline import Injector

        handler = Injector(api_port=8000)
        flow = MagicMock()
        flow.request.url = "https://example.com/page"
        context = {'matched_pids': []}

        result = handler.process(flow, context)

        assert result is True
        assert context.get('injected') is None


class TestHeaderNormalizer:
    """Tests for HeaderNormalizer handler."""

    def test_removes_transfer_encoding_after_injection(self):
        from core.proxy_pipeline import HeaderNormalizer

        handler = HeaderNormalizer()
        flow = MagicMock()
        flow.response.headers = {
            "Transfer-Encoding": "chunked",
            "Content-Encoding": "gzip"
        }
        flow.response.content = b"test content"
        context = {'injected': True}

        handler.process(flow, context)

        assert "Transfer-Encoding" not in flow.response.headers
        assert "Content-Encoding" not in flow.response.headers

    def test_updates_content_length(self):
        from core.proxy_pipeline import HeaderNormalizer

        handler = HeaderNormalizer()
        flow = MagicMock()
        flow.response.headers = {}
        flow.response.content = b"test content"  # 12 bytes
        context = {'decoded': True}

        handler.process(flow, context)

        assert flow.response.headers["Content-Length"] == "12"

    def test_sanitizes_security_headers_on_injection(self):
        from core.proxy_pipeline import HeaderNormalizer

        handler = HeaderNormalizer()
        flow = MagicMock()
        flow.response.headers = {
            "Content-Security-Policy": "default-src 'self'"
        }
        flow.response.content = b"test"
        flow.request.url = "https://example.com"
        context = {'injected': True}

        # The sanitizer mock should be called
        with patch.object(handler.sanitizer, 'sanitize') as mock_sanitize:
            handler.process(flow, context)
            mock_sanitize.assert_called_once()

    def test_no_changes_without_injection_or_decode(self):
        from core.proxy_pipeline import HeaderNormalizer

        handler = HeaderNormalizer()
        flow = MagicMock()
        flow.response.headers = {"Content-Type": "text/html"}
        flow.response.content = b"test"
        context = {}

        result = handler.process(flow, context)

        assert result is True
