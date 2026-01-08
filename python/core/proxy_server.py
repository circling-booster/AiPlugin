from mitmproxy import http
import logging
from .injector import inject_script

class AiPlugsAddon:
    def __init__(self, api_port, plugin_scripts):
        self.api_port = api_port
        self.plugin_scripts = plugin_scripts
        self.logger = logging.getLogger("ProxyCore")

    def response(self, flow: http.HTTPFlow):
        # 1. CSP 헤더 제거 (스크립트 실행 허용)
        if "content-security-policy" in flow.response.headers:
            del flow.response.headers["content-security-policy"]
            
        # 2. Content-Type 필터링 (HTML만 처리)
        content_type = flow.response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return

        # 3. 스크립트 주입
        if flow.response.content:
            try:
                flow.response.content = inject_script(
                    flow.response.content, 
                    self.api_port, 
                    self.plugin_scripts
                )
            except Exception as e:
                self.logger.error(f"Injection Failed: {e}")