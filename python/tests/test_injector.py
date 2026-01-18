"""
Tests for core/injector.py - HTML injection utilities.
"""
import pytest
from core.injector import get_loader_script, inject_script, _make_script_tags, RE_HEAD, RE_HTML, RE_BODY_END


class TestRegexPatterns:
    """Tests for compiled regex patterns."""

    def test_head_pattern_matches(self):
        html = b"<html><head>content</head></html>"
        assert RE_HEAD.search(html) is not None

    def test_head_pattern_case_insensitive(self):
        html = b"<html><HEAD>content</HEAD></html>"
        assert RE_HEAD.search(html) is not None

    def test_head_pattern_with_attributes(self):
        html = b'<html><head lang="en">content</head></html>'
        assert RE_HEAD.search(html) is not None

    def test_html_pattern_matches(self):
        html = b"<html><body>content</body></html>"
        assert RE_HTML.search(html) is not None

    def test_html_pattern_with_attributes(self):
        html = b'<html lang="en"><body>content</body></html>'
        assert RE_HTML.search(html) is not None

    def test_body_end_pattern_matches(self):
        html = b"<html><body>content</body></html>"
        assert RE_BODY_END.search(html) is not None

    def test_body_end_pattern_case_insensitive(self):
        html = b"<html><body>content</BODY></html>"
        assert RE_BODY_END.search(html) is not None


class TestGetLoaderScript:
    """Tests for get_loader_script function."""

    def test_returns_bytes(self):
        result = get_loader_script(8000)
        assert isinstance(result, bytes)

    def test_contains_api_port(self):
        result = get_loader_script(8000)
        assert b"8000" in result

    def test_contains_script_tag(self):
        result = get_loader_script(8000)
        assert b"<script>" in result
        assert b"</script>" in result

    def test_contains_aiplugs_variables(self):
        result = get_loader_script(8000)
        assert b"AIPLUGS_API_PORT" in result
        assert b"__AI_API_BASE_URL__" in result

    def test_contains_history_hooks(self):
        result = get_loader_script(8000)
        assert b"pushState" in result
        assert b"replaceState" in result
        assert b"popstate" in result

    def test_different_ports(self):
        result_8000 = get_loader_script(8000)
        result_9000 = get_loader_script(9000)
        assert result_8000 != result_9000
        assert b"9000" in result_9000
        assert b"9000" not in result_8000


class TestMakeScriptTags:
    """Tests for _make_script_tags helper function."""

    def test_empty_list(self):
        result = _make_script_tags([])
        assert result == b""

    def test_single_url(self):
        result = _make_script_tags(["http://localhost/script.js"])
        assert result == b'<script src="http://localhost/script.js"></script>'

    def test_multiple_urls(self):
        urls = ["http://localhost/script1.js", "http://localhost/script2.js"]
        result = _make_script_tags(urls)
        assert b"script1.js" in result
        assert b"script2.js" in result
        assert result.count(b"<script") == 2


class TestInjectScript:
    """Tests for inject_script function."""

    def test_basic_injection(self):
        html = b"<html><head></head><body>Content</body></html>"
        result = inject_script(html, 8000)
        assert b"AIPLUGS_API_PORT" in result
        assert b"8000" in result

    def test_head_injection_placement(self):
        html = b"<html><head></head><body>Content</body></html>"
        result = inject_script(html, 8000, head_scripts=["http://localhost/head.js"])
        # Script should be after <head> tag
        head_pos = result.find(b"<head>")
        script_pos = result.find(b"head.js")
        assert script_pos > head_pos

    def test_body_injection_placement(self):
        html = b"<html><head></head><body>Content</body></html>"
        result = inject_script(html, 8000, body_scripts=["http://localhost/body.js"])
        # Script should be before </body> tag
        script_pos = result.find(b"body.js")
        body_end_pos = result.find(b"</body>")
        assert script_pos < body_end_pos

    def test_injection_without_head_tag(self):
        html = b"<html><body>Content</body></html>"
        result = inject_script(html, 8000)
        # Should still inject (fallback to html tag or beginning)
        assert b"AIPLUGS_API_PORT" in result

    def test_injection_without_body_tag(self):
        html = b"<html><head></head>Content</html>"
        result = inject_script(html, 8000, body_scripts=["http://localhost/script.js"])
        # Should append at the end
        assert b"script.js" in result

    def test_injection_minimal_html(self):
        html = b"Hello World"
        result = inject_script(html, 8000)
        # Should prepend loader script
        assert b"AIPLUGS_API_PORT" in result

    def test_injection_preserves_original_content(self):
        original_content = b"<html><head><title>Test</title></head><body><div>Original</div></body></html>"
        result = inject_script(original_content, 8000)
        assert b"<title>Test</title>" in result
        assert b"<div>Original</div>" in result

    def test_multiple_head_and_body_scripts(self):
        html = b"<html><head></head><body>Content</body></html>"
        result = inject_script(
            html, 8000,
            head_scripts=["http://localhost/h1.js", "http://localhost/h2.js"],
            body_scripts=["http://localhost/b1.js", "http://localhost/b2.js"]
        )
        assert b"h1.js" in result
        assert b"h2.js" in result
        assert b"b1.js" in result
        assert b"b2.js" in result


class TestInjectScriptEdgeCases:
    """Edge case tests for inject_script."""

    def test_html_with_uppercase_tags(self):
        html = b"<HTML><HEAD></HEAD><BODY>Content</BODY></HTML>"
        result = inject_script(html, 8000)
        assert b"AIPLUGS_API_PORT" in result

    def test_html_with_mixed_case_tags(self):
        html = b"<Html><Head></Head><Body>Content</Body></Html>"
        result = inject_script(html, 8000)
        assert b"AIPLUGS_API_PORT" in result

    def test_empty_html(self):
        html = b""
        result = inject_script(html, 8000)
        assert b"AIPLUGS_API_PORT" in result

    def test_html_with_existing_scripts(self):
        html = b'<html><head><script src="existing.js"></script></head><body>Content</body></html>'
        result = inject_script(html, 8000, head_scripts=["http://localhost/new.js"])
        assert b"existing.js" in result
        assert b"new.js" in result
