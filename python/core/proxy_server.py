from mitmproxy import http
from core.plugin_loader import plugin_loader
from core.injector import inject_script
from core.security import SecuritySanitizer

class RequestFilter:
    """
    [Refactored] URL 패턴 매칭 및 타겟 플러그인 선별
    """
    def __init__(self):
        pass 

    def get_matching_plugins(self, url: str) -> list:
        matched_pids = []
        # PluginLoader에 로드된 모든 플러그인을 순회하며 패턴 검사
        for pid, ctx in plugin_loader.plugins.items():
            for pattern in ctx.compiled_patterns:
                if pattern.match(url):
                    matched_pids.append(pid)
                    break # 해당 플러그인의 패턴 중 하나라도 맞으면 추가
        return matched_pids

class AiPlugsAddon:
    def __init__(self, api_port: int):
        self.api_port = api_port
        
        if not plugin_loader.plugins:
            plugin_loader.load_plugins()
            
        self.filter = RequestFilter()
        self.sanitizer = SecuritySanitizer()
        
        print(f"[Proxy] AiPlugsAddon initialized. API Port: {self.api_port}")

    def response(self, flow: http.HTTPFlow):
        # 1. HTML Content-Type 체크
        content_type = flow.response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return

        # 2. URL 필터링
        current_url = flow.request.url
        matched_pids = self.filter.get_matching_plugins(current_url)

        if not matched_pids:
            return

        # 3. 로직 수행
        try:
            # [Fix] 하드코딩 제거: Manifest에 정의된 실제 JS 파일명들을 모두 가져옴
            target_scripts = []
            
            for pid in matched_pids:
                ctx = plugin_loader.get_plugin(pid)
                if not ctx: continue
                
                # manifest.content_scripts 리스트를 순회
                for script_block in ctx.manifest.content_scripts:
                    # 각 블록 내의 js 파일 리스트를 순회
                    for js_file in script_block.js:
                        url = f"http://localhost:{self.api_port}/plugins/{pid}/{js_file}"
                        target_scripts.append(url)
            
            # 주입 대상이 있을 경우에만 실행
            if target_scripts:
                html = flow.response.content
                modified = inject_script(html, self.api_port, target_scripts)
                flow.response.content = modified
                
                # 보안 헤더 제거
                self.sanitizer.sanitize(flow)

                # 로그 출력
                print(f"[Proxy] Injected Plugins {matched_pids} into {current_url[:40]}...")

        except Exception as e:
            print(f"[Proxy] Processing Error: {e}")