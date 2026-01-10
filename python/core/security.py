import logging

# [Refactor] Define Header List centrally to maintain consistency
# Note: Ensure this list matches logic in Electron/main/index.js if duplications exist.
CSP_HEADERS_TO_REMOVE = [
    'content-security-policy',
    'content-security-policy-report-only',
    'x-content-security-policy',
    'x-frame-options', 
]

class SecuritySanitizer:
    """
    [New Module] HTTP 응답 헤더의 보안 정책(CSP 등)을 정화(Sanitize)하는 역할
    """
    def __init__(self):
        self.logger = logging.getLogger("SecuritySanitizer")
        self.headers_to_remove = CSP_HEADERS_TO_REMOVE

    def sanitize(self, flow):
        """
        Mitmproxy Flow 객체를 받아 보안 헤더를 제거합니다.
        """
        removed_count = 0
        headers = list(flow.response.headers.keys())
        
        for header_key in headers:
            if header_key.lower() in self.headers_to_remove:
                del flow.response.headers[header_key]
                removed_count += 1
        
        if removed_count > 0:
            self.logger.debug(f"Removed {removed_count} security headers from {flow.request.url}")