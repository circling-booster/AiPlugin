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

        # [Improved] 1.5 Fetch Metadata 기반 정밀 필터링 (중복 주입 방지 핵심)
        # 브라우저가 보내는 요청의 목적(Dest)과 모드(Mode)를 확인합니다.
        request_headers = flow.request.headers
        sec_fetch_dest = request_headers.get("Sec-Fetch-Dest", None)
        sec_fetch_mode = request_headers.get("Sec-Fetch-Mode", None)

        # (A) AJAX/Fetch 요청 제외
        # dest가 'empty'이면 fetch/xhr 요청이므로 페이지 이동이 아님 -> 주입 제외
        if sec_fetch_dest == "empty":
            return
        
        # (B) CORS, WebSocket, Font 등 리소스 요청 제외
        if sec_fetch_mode in ["cors", "websocket", "no-cors"]:
            return

        # (C) iframe 판별 로직
        # Dest가 명시적으로 iframe/frame인 경우에만 iframe으로 취급
        is_iframe = sec_fetch_dest in ["iframe", "frame"]

        # (D) 헤더가 모호한 경우(Legacy Browser or Special Request) 방어
        # iframe도 아니고 navigate(페이지 이동)도 아니면 주입하지 않음 (보수적 접근)
        if not is_iframe and sec_fetch_mode and sec_fetch_mode != "navigate":
            return

        current_url = flow.request.url
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
                
                # 변경된 inject_script 호출
                modified = inject_script(html, self.api_port, head_scripts, body_scripts)
                flow.response.content = modified
                
                # 보안 헤더 제거
                self.sanitizer.sanitize(flow)

                # 로그 출력
                frame_tag = "[IFRAME]" if is_iframe else "[TOP]"
                print(f"[Proxy] {frame_tag} Injected Plugins {matched_pids} into {current_url[:50]}...")

        except Exception as e:
            print(f"[Proxy] Processing Error: {e}")