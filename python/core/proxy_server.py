from mitmproxy import http
from functools import lru_cache
from core.plugin_loader import plugin_loader
from core.injector import inject_script

class RequestFilter:
    """
    [Task 2] Precision Injection Filter
    URL 패턴 매칭 로직을 담당합니다.
    """
    def __init__(self):
        # 플러그인 로더가 로드된 상태에서 패턴을 가져옵니다.
        # (AiPlugsAddon 초기화 시점에 로드됨을 보장)
        self.patterns = []
        
    def load_patterns(self):
        """플러그인 로더로부터 컴파일된 패턴을 가져옵니다."""
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

class AiPlugsAddon:
    """
    Mitmproxy와 AiPlugs Core를 연결하는 애드온 클래스
    main.py에서 인스턴스화되어 사용됩니다.
    """
    def __init__(self, api_port: int, scripts: list):
        self.api_port = api_port
        self.scripts = scripts
        
        # 1. 플러그인 메타데이터 로드 (여기서 한 번만 수행)
        # 이미 로드되어 있다면 plugin_loader 내부에서 처리하겠지만,
        # 명시적으로 패턴 갱신을 위해 호출
        if not plugin_loader.plugins:
            plugin_loader.load_plugins()
            
        # 2. 필터 초기화
        self.filter_logic = RequestFilter()
        self.filter_logic.load_patterns()
        
        print(f"[Proxy] AiPlugsAddon initialized with API Port: {self.api_port}")

    def response(self, flow: http.HTTPFlow):
        """Mitmproxy Response Hook"""
        
        # 1. Content-Type Check
        content_type = flow.response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return

        # 2. [Task 2] URL Filtering
        if not self.filter_logic.should_inject(flow.request.url):
            return

        # 3. Injection Logic
        try:
            html = flow.response.content
            
            # [Fix] injector.py의 정의에 맞춰 (html, api_port, scripts) 전달
            modified = inject_script(html, self.api_port, self.scripts)
            
            flow.response.content = modified

            # ============================================================
            # [Spec 1.2] CSP 이중 우회 로직 (Mitmproxy Level)
            # 기술 명세서에 따라 flow.response.headers.pop을 사용하여 제거
            # Mitmproxy의 headers는 Case-Insensitive하므로 대소문자 무관하게 동작
            # ============================================================
            flow.response.headers.pop("Content-Security-Policy", None)
            flow.response.headers.pop("Content-Security-Policy-Report-Only", None)
            flow.response.headers.pop("X-Content-Security-Policy", None)

        except Exception as e:
            print(f"[Proxy] Injection Error: {e}")