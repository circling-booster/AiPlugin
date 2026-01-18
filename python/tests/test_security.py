"""
Tests for core/security.py - Security header sanitization.
"""
import pytest
from unittest.mock import MagicMock
from core.security import SecuritySanitizer, CSP_HEADERS_TO_REMOVE


class TestCSPHeadersList:
    """Tests for CSP headers configuration."""

    def test_csp_headers_defined(self):
        assert len(CSP_HEADERS_TO_REMOVE) > 0

    def test_standard_csp_header_included(self):
        assert 'content-security-policy' in CSP_HEADERS_TO_REMOVE

    def test_xframe_options_included(self):
        assert 'x-frame-options' in CSP_HEADERS_TO_REMOVE

    def test_report_only_included(self):
        assert 'content-security-policy-report-only' in CSP_HEADERS_TO_REMOVE


class TestSecuritySanitizer:
    """Tests for SecuritySanitizer class."""

    def test_initialization(self):
        sanitizer = SecuritySanitizer()
        assert sanitizer.headers_to_remove == CSP_HEADERS_TO_REMOVE

    def test_sanitize_removes_csp_header(self):
        sanitizer = SecuritySanitizer()

        # Create mock flow
        flow = MagicMock()
        flow.response.headers = {
            'Content-Type': 'text/html',
            'Content-Security-Policy': "default-src 'self'",
            'Cache-Control': 'no-cache'
        }
        flow.request.url = "https://example.com/page"

        sanitizer.sanitize(flow)

        # CSP should be removed
        assert 'Content-Security-Policy' not in flow.response.headers
        # Other headers should remain
        assert 'Content-Type' in flow.response.headers
        assert 'Cache-Control' in flow.response.headers

    def test_sanitize_removes_multiple_security_headers(self):
        sanitizer = SecuritySanitizer()

        flow = MagicMock()
        flow.response.headers = {
            'Content-Type': 'text/html',
            'Content-Security-Policy': "default-src 'self'",
            'X-Frame-Options': 'DENY',
            'X-Content-Security-Policy': "default-src 'self'"
        }
        flow.request.url = "https://example.com/page"

        sanitizer.sanitize(flow)

        # All security headers should be removed
        assert 'Content-Security-Policy' not in flow.response.headers
        assert 'X-Frame-Options' not in flow.response.headers
        assert 'X-Content-Security-Policy' not in flow.response.headers

    def test_sanitize_case_insensitive(self):
        sanitizer = SecuritySanitizer()

        flow = MagicMock()
        # Headers with different cases
        flow.response.headers = {
            'content-security-policy': "default-src 'self'",  # lowercase
        }
        flow.request.url = "https://example.com/page"

        sanitizer.sanitize(flow)

        # Should be removed regardless of case
        assert 'content-security-policy' not in flow.response.headers

    def test_sanitize_no_security_headers(self):
        sanitizer = SecuritySanitizer()

        flow = MagicMock()
        flow.response.headers = {
            'Content-Type': 'text/html',
            'Server': 'nginx'
        }
        flow.request.url = "https://example.com/page"

        # Should not raise any errors
        sanitizer.sanitize(flow)

        # Original headers should remain
        assert 'Content-Type' in flow.response.headers
        assert 'Server' in flow.response.headers

    def test_sanitize_empty_headers(self):
        sanitizer = SecuritySanitizer()

        flow = MagicMock()
        flow.response.headers = {}
        flow.request.url = "https://example.com/page"

        # Should not raise any errors
        sanitizer.sanitize(flow)

    def test_sanitize_preserves_non_security_headers(self):
        sanitizer = SecuritySanitizer()

        flow = MagicMock()
        original_headers = {
            'Content-Type': 'text/html',
            'Content-Length': '1234',
            'Date': 'Mon, 01 Jan 2024 00:00:00 GMT',
            'Server': 'nginx',
            'Content-Security-Policy': "default-src 'self'"
        }
        flow.response.headers = original_headers.copy()
        flow.request.url = "https://example.com/page"

        sanitizer.sanitize(flow)

        # Verify non-security headers are preserved
        assert flow.response.headers.get('Content-Type') == 'text/html'
        assert flow.response.headers.get('Content-Length') == '1234'
        assert flow.response.headers.get('Server') == 'nginx'
