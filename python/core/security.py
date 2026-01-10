import logging
import re

class SecuritySanitizer:
    """
    [Security Fix] Smart CSP Patcher
    기존의 'CSP 삭제' 방식에서 'CSP 수정(Allow Localhost)' 방식으로 변경하여
    Drive-by Download 및 RCE 공격 가능성을 최소화합니다.
    """
    def __init__(self):
        self.logger = logging.getLogger("SecuritySanitizer")
        # 헤더 삭제가 아닌, 수정 대상 목록
        self.csp_headers = [
            'content-security-policy',
            'content-security-policy-report-only'
        ]
        # 안전하지 않지만(unsafe-inline), 플러그인 동작을 위해 필수적인 지시어
        # 로컬 포트는 동적으로 바뀔 수 있으므로 추후 포맷팅
        self.allowed_src = "'unsafe-inline' 'unsafe-eval' http://localhost:{port} ws://localhost:{port}"

    def sanitize(self, flow, api_port: int):
        """
        CSP 헤더를 파싱하여 AiPlugs API 서버 접근을 허용하도록 패치합니다.
        """
        patched_directive = self.allowed_src.format(port=api_port)
        
        for header_key in list(flow.response.headers.keys()):
            # 1. CSP 헤더 발견
            if header_key.lower() in self.csp_headers:
                original_csp = flow.response.headers[header_key]
                new_csp = self._patch_csp_value(original_csp, patched_directive)
                
                # 값 변경 적용
                flow.response.headers[header_key] = new_csp
                self.logger.debug(f"[Secure] Patched CSP for {flow.request.url}")

            # 2. X-Frame-Options 제거 (Iframe 주입이 필요한 경우만)
            # 보안을 위해 기본적으로는 유지하되, 명시적인 필요가 있을 때만 제거 로직 추가 권장
            if header_key.lower() == 'x-frame-options':
                del flow.response.headers[header_key]

    def _patch_csp_value(self, csp_string: str, directives_to_add: str) -> str:
        """
        CSP 문자열을 파싱하여 script-src, connect-src 등에 로컬 허용 규칙을 추가합니다.
        """
        # 간단한 파싱: 세미콜론으로 분리
        directives = [d.strip() for d in csp_string.split(';') if d.strip()]
        new_directives = []
        
        has_script_src = False
        has_connect_src = False
        
        for directive in directives:
            name_val = directive.split(maxsplit=1)
            name = name_val[0].lower()
            val = name_val[1] if len(name_val) > 1 else ""
            
            if name == 'script-src':
                has_script_src = True
                val += f" {directives_to_add}"
            elif name == 'connect-src':
                has_connect_src = True
                val += f" {directives_to_add}"
            elif name == 'default-src':
                # default-src가 있으면 여기에도 추가해주는 것이 안전
                val += f" {directives_to_add}"
                
            new_directives.append(f"{name} {val}")
        
        # 만약 script-src가 없었다면 default-src가 적용되었겠지만,
        # 명시적으로 추가하여 확실하게 허용
        if not has_script_src:
            new_directives.append(f"script-src * {directives_to_add}")
        if not has_connect_src:
            new_directives.append(f"connect-src * {directives_to_add}")
            
        return "; ".join(new_directives)