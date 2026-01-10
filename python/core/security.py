import logging

class SecuritySanitizer:
    """
    [New Module] HTTP 응답 헤더의 보안 정책(CSP 등)을 정화(Sanitize)하는 역할
    """
    def __init__(self):
        self.logger = logging.getLogger("SecuritySanitizer")
        # 제거할 헤더 목록 (소문자로 관리)
        self.headers_to_remove = [
            'content-security-policy',
            'content-security-policy-report-only',
            'x-content-security-policy',
            'x-frame-options', # 추가: iFrame 제약 해제 권장
        ]

    def sanitize(self, flow):
        """
        Mitmproxy Flow 객체를 받아 보안 헤더를 제거합니다.
        """
        removed_count = 0
        # 대소문자 구분 없이 헤더 제거를 위해 키 수집
        headers = list(flow.response.headers.keys())
        
        for header in headers:
            if header.lower() in self.headers_to_remove:
                del flow.response.headers[header]
                removed_count += 1
        
        if removed_count > 0:
            # 디버그 레벨로 낮춰 로그 노이즈 감소
            self.logger.debug(f"Removed {removed_count} security headers from {flow.request.url}")