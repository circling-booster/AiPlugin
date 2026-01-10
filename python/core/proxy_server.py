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

        current_url = flow.request.url
        
        # [New] iframe 감지 (Sec-Fetch-Dest 헤더 활용)
        # Chrome/Edge 등 최신 브라우저는 iframe 요청 시 이 헤더를 "iframe" 또는 "frame"으로 보냄
        # 헤더가 없는 경우(None) 기본값은 'document'로 간주 (안전한 기본값)
        fetch_dest = flow.request.headers.get("Sec-Fetch-Dest", "document")
        is_iframe = fetch_dest in ["iframe", "frame"]

        matched_pids = self.filter.get_matching_plugins(current_url)

        if not matched_pids:
            return

        # 3. 로직 수행
        try:
            head_scripts = []
            body_scripts = []
            
            for pid in matched_pids:
                ctx = plugin_loader.get_plugin(pid)
                if not ctx: continue
                
                # manifest.content_scripts 리스트를 순회
                for script_block in ctx.manifest.content_scripts:
                    # [Check 1] all_frames 로직 적용
                    # iframe 요청인데 플러그인이 all_frames=false 라면 주입하지 않음
                    if is_iframe and not script_block.all_frames:
                        continue
                    
                    # [Check 2] run_at 로직 적용
                    # document_idle도 Proxy 특성상 document_end(body 끝)와 동일하게 처리
                    target_list = head_scripts if script_block.run_at == "document_start" else body_scripts
                    
                    for js_file in script_block.js:
                        url = f"http://localhost:{self.api_port}/plugins/{pid}/{js_file}"
                        target_list.append(url)
            
            # 주입 대상이 있을 경우에만 실행
            if head_scripts or body_scripts:
                html = flow.response.content
                
                # [New] 캐싱 무효화 (Cache Busting)
                # 브라우저가 주입된 페이지 대신 원본 캐시를 사용하는 것을 방지
                if "Cache-Control" in flow.response.headers:
                    del flow.response.headers["Cache-Control"]
                if "Expires" in flow.response.headers:
                    del flow.response.headers["Expires"]
                if "ETag" in flow.response.headers:
                    del flow.response.headers["ETag"]
                
                # 변경된 inject_script 호출 (Head/Body 분리)
                modified = inject_script(html, self.api_port, head_scripts, body_scripts)
                flow.response.content = modified
                
                # 보안 헤더 제거
                self.sanitizer.sanitize(flow)

                # 로그 출력
                frame_tag = "[IFRAME]" if is_iframe else "[TOP]"
                print(f"[Proxy] {frame_tag} Injected Plugins {matched_pids} into {current_url[:40]}...")

        except Exception as e:
            print(f"[Proxy] Processing Error: {e}")