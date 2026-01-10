from mitmproxy import http
from functools import lru_cache
from core.plugin_loader import plugin_loader
from core.injector import inject_script
from core.security import SecuritySanitizer  # [Refactor] 분리된 모듈 임포트

class RequestFilter:
    """
    [Role] URL 패턴 매칭 담당 (변경 없음)
    """
    def __init__(self):
        self.patterns = []
        
    def load_patterns(self):
        self.patterns = []
        # PluginLoader에서 컴파일된 정규식 패턴 참조
        for pid, ctx in plugin_loader.plugins.items():
            for pattern in ctx.compiled_patterns:
                self.patterns.append((pattern, pid))

    @lru_cache(maxsize=2048)
    def should_inject(self, url: str) -> bool:
        for pattern, _ in self.patterns:
            if pattern.match(url):
                return True
        return False

class AiPlugsAddon:
    """
    [Role] Mitmproxy와 시스템을 연결하는 Router 역할에 집중
    """
    def __init__(self, api_port: int, scripts: list):
        self.api_port = api_port
        self.scripts = scripts
        
        # 1. 플러그인 로드 보장
        if not plugin_loader.plugins:
            plugin_loader.load_plugins()
            
        # 2. 컴포넌트 초기화
        self.filter = RequestFilter()
        self.filter.load_patterns()
        self.sanitizer = SecuritySanitizer() # [Refactor] 보안 로직 위임
        
        print(f"[Proxy] AiPlugsAddon initialized with API Port: {self.api_port}")

    def response(self, flow: http.HTTPFlow):
        # 1. HTML Content-Type 체크
        content_type = flow.response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return

        # 2. URL 필터링
        if not self.filter.should_inject(flow.request.url):
            return

        # 3. 로직 수행
        try:
            # [Task 2.1] Script Injection
            html = flow.response.content
            modified = inject_script(html, self.api_port, self.scripts)
            flow.response.content = modified

            # [Task 2.2] Security Sanitize (CSP Bypass)
            # 이제 Addon이 직접 헤더를 건드리지 않고 전문가(Sanitizer)에게 맡김
            self.sanitizer.sanitize(flow)

        except Exception as e:
            print(f"[Proxy] Processing Error: {e}")