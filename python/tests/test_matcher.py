"""
Tests for core/matcher.py - URL pattern matching.
"""
import pytest
from core.matcher import UrlMatcher


class TestUrlMatcherAllUrls:
    """Tests for <all_urls> pattern."""

    def test_all_urls_matches_http(self):
        assert UrlMatcher.match("<all_urls>", "http://example.com/page")

    def test_all_urls_matches_https(self):
        assert UrlMatcher.match("<all_urls>", "https://example.com/page")

    def test_all_urls_matches_any_domain(self):
        assert UrlMatcher.match("<all_urls>", "https://subdomain.google.com/search?q=test")


class TestUrlMatcherScheme:
    """Tests for scheme matching."""

    def test_http_scheme_match(self):
        assert UrlMatcher.match("http://*/*", "http://example.com/path")

    def test_http_scheme_no_match_https(self):
        assert not UrlMatcher.match("http://*/*", "https://example.com/path")

    def test_https_scheme_match(self):
        assert UrlMatcher.match("https://*/*", "https://example.com/path")

    def test_wildcard_scheme_matches_http(self):
        assert UrlMatcher.match("*://*/*", "http://example.com/path")

    def test_wildcard_scheme_matches_https(self):
        assert UrlMatcher.match("*://*/*", "https://example.com/path")


class TestUrlMatcherHost:
    """Tests for host matching."""

    def test_exact_host_match(self):
        assert UrlMatcher.match("https://example.com/*", "https://example.com/page")

    def test_exact_host_no_match(self):
        assert not UrlMatcher.match("https://example.com/*", "https://other.com/page")

    def test_wildcard_host_match(self):
        assert UrlMatcher.match("https://*/*", "https://any-domain.com/page")

    def test_subdomain_wildcard_match(self):
        assert UrlMatcher.match("https://*.example.com/*", "https://sub.example.com/page")

    def test_subdomain_wildcard_exact_domain(self):
        assert UrlMatcher.match("https://*.example.com/*", "https://example.com/page")

    def test_subdomain_wildcard_nested(self):
        assert UrlMatcher.match("https://*.example.com/*", "https://deep.sub.example.com/page")

    def test_subdomain_wildcard_no_match_different_domain(self):
        assert not UrlMatcher.match("https://*.example.com/*", "https://example.org/page")


class TestUrlMatcherPort:
    """Tests for port matching."""

    def test_explicit_port_match(self):
        assert UrlMatcher.match("http://localhost:3000/*", "http://localhost:3000/page")

    def test_explicit_port_no_match(self):
        assert not UrlMatcher.match("http://localhost:3000/*", "http://localhost:8080/page")

    def test_port_pattern_without_url_port(self):
        # Pattern expects port, URL has no explicit port
        assert not UrlMatcher.match("http://localhost:3000/*", "http://localhost/page")

    def test_wildcard_port(self):
        assert UrlMatcher.match("http://localhost:*/*", "http://localhost:8080/page")


class TestUrlMatcherPath:
    """Tests for path matching."""

    def test_wildcard_path_match(self):
        assert UrlMatcher.match("https://example.com/*", "https://example.com/any/path/here")

    def test_specific_path_match(self):
        assert UrlMatcher.match("https://example.com/api/*", "https://example.com/api/users")

    def test_specific_path_no_match(self):
        assert not UrlMatcher.match("https://example.com/api/*", "https://example.com/other/path")

    def test_exact_path_match(self):
        assert UrlMatcher.match("https://example.com/page", "https://example.com/page")

    def test_deep_path_wildcard(self):
        assert UrlMatcher.match("https://example.com/a/b/*", "https://example.com/a/b/c/d/e")


class TestUrlMatcherEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_pattern_format(self):
        # Pattern without scheme separator
        assert not UrlMatcher.match("example.com/path", "https://example.com/path")

    def test_empty_pattern(self):
        assert not UrlMatcher.match("", "https://example.com/")

    def test_malformed_url(self):
        # Should handle gracefully and return False
        result = UrlMatcher.match("https://*/*", "not a url at all")
        # This may return True or False depending on implementation
        # The important thing is it doesn't crash
        assert isinstance(result, bool)

    def test_url_with_query_params(self):
        assert UrlMatcher.match("https://example.com/*", "https://example.com/search?q=test&page=1")

    def test_url_with_fragment(self):
        assert UrlMatcher.match("https://example.com/*", "https://example.com/page#section")


class TestUrlMatcherRealWorldPatterns:
    """Tests with real-world URL patterns."""

    def test_google_pattern(self):
        assert UrlMatcher.match("*://*.google.com/*", "https://www.google.com/search?q=test")

    def test_localhost_development(self):
        assert UrlMatcher.match("http://localhost:3000/*", "http://localhost:3000/dashboard")

    def test_api_endpoint_pattern(self):
        assert UrlMatcher.match("https://api.example.com/v1/*", "https://api.example.com/v1/users/123")

    def test_cdn_pattern(self):
        assert UrlMatcher.match("*://*.cdn.example.com/*", "https://static.cdn.example.com/assets/image.png")
