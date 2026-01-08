from mitmproxy import http
from functools import lru_cache
from core.plugin_loader import plugin_loader
# core/injector.py가 있다고 가정 (기존 스펙)
from core.injector import inject_script 

# Proxy Process 시작 시 메타데이터 로드
plugin_loader.load_plugins()

API_PORT = 5000 # Config에서 로드 필요
CORE_LOADER_URL = f"http://localhost:{API_PORT}/static/core-loader.js"

class RequestFilter:
    """
    [Task 2] Precision Injection Filter
    """
    def __init__(self):
        # Flatten all regex patterns with their plugin IDs
        self.patterns = []
        for pid, ctx in plugin_loader.plugins.items():
            for pattern in ctx.compiled_patterns:
                self.patterns.append((pattern, pid))

    @lru_cache(maxsize=2048)
    def should_inject(self, url: str) -> bool:
        """
        [Optimization] Caching matched results for O(1) performance.
        Checks if the URL matches ANY plugin's target pattern.
        """
        for pattern, _ in self.patterns:
            if pattern.match(url):
                return True
        return False

filter_logic = RequestFilter()

def response(flow: http.HTTPFlow):
    """Mitmproxy Response Hook"""
    
    # 1. Content-Type Check
    content_type = flow.response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return

    # 2. [Task 2] URL Filtering
    if not filter_logic.should_inject(flow.request.url):
        return

    # 3. Injection Logic
    try:
        html = flow.response.content
        # Core Loader 주입 (이 스크립트가 다시 구체적인 Plugin JS를 요청함)
        modified = inject_script(html, CORE_LOADER_URL)
        flow.response.content = modified

        # [Optimization] Remove CSP to allow injected scripts execution
        if "Content-Security-Policy" in flow.response.headers:
            del flow.response.headers["Content-Security-Policy"]

    except Exception as e:
        print(f"[Proxy] Injection Error: {e}")