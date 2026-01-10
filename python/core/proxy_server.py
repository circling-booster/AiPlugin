from mitmproxy import http
from core.plugin_loader import plugin_loader
from core.injector import inject_script
from core.security import SecuritySanitizer

class RequestFilter:
    def __init__(self):
        pass 

    def get_matching_plugins(self, url: str) -> list:
        matched_pids = []
        for pid, ctx in plugin_loader.plugins.items():
            for pattern in ctx.compiled_patterns:
                if pattern.match(url):
                    matched_pids.append(pid)
                    break
        return matched_pids

class AiPlugsAddon:
    def __init__(self, api_port: int):
        self.api_port = api_port
        
        if not plugin_loader.plugins:
            plugin_loader.load_plugins()
            
        self.filter = RequestFilter()
        self.sanitizer = SecuritySanitizer()
        
        print(f"[Proxy] AiPlugs Core initialized. API Port: {self.api_port}")

    def response(self, flow: http.HTTPFlow):
        # 1. HTML Content-Type 체크
        content_type = flow.response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return

        # 2. Fetch Metadata 기반 스마트 필터링
        # (불필요한 리소스 요청에 개입하지 않도록 하여 성능 확보)
        request_headers = flow.request.headers
        sec_fetch_dest = request_headers.get("Sec-Fetch-Dest", None)
        sec_fetch_mode = request_headers.get("Sec-Fetch-Mode", None)

        if sec_fetch_dest == "empty": return
        if sec_fetch_mode in ["cors", "websocket", "no-cors"]: return

        # Iframe 여부 판단
        is_iframe = sec_fetch_dest in ["iframe", "frame"]
        
        # Navigate가 아니더라도 Iframe이면 허용 (브라우저 호환성)
        if not is_iframe and sec_fetch_mode and sec_fetch_mode != "navigate":
            return

        current_url = flow.request.url
        matched_pids = self.filter.get_matching_plugins(current_url)

        if not matched_pids:
            return

        try:
            # =================================================================
            # [안정성 핵심] 무조건 디코딩 (Gzip/Chunked 해제)
            # =================================================================
            # 원본을 훼손하지 않으면서 내용을 분석/수정하기 위해 필수입니다.
            flow.response.decode()

            head_scripts = []
            body_scripts = []
            
            for pid in matched_pids:
                ctx = plugin_loader.get_plugin(pid)
                if not ctx: continue
                
                for script_block in ctx.manifest.content_scripts:
                    # [Rule 복구] manifest 설정 엄격 준수
                    if is_iframe and not script_block.all_frames:
                        continue
                    
                    target_list = head_scripts if script_block.run_at == "document_start" else body_scripts
                    for js_file in script_block.js:
                        url = f"http://localhost:{self.api_port}/plugins/{pid}/{js_file}"
                        target_list.append(url)
            
            # 주입할 대상이 있는 경우에만 로직 수행
            if head_scripts or body_scripts:
                html = flow.response.content
                
                # [캐시 무효화] 플러그인 개발/수정 사항 즉시 반영용
                for h in ["Cache-Control", "Expires", "ETag"]:
                    if h in flow.response.headers: del flow.response.headers[h]
                
                # 스크립트 주입
                modified = inject_script(html, self.api_port, head_scripts, body_scripts)
                flow.response.content = modified

                # =================================================================
                # [Plan A 유지] 헤더 정규화 (Protocol Safety)
                # =================================================================
                # 주입으로 인해 Body 길이가 변했으므로, 헤더를 반드시 맞춰주어야 합니다.
                # 이를 통해 향후 어떤 플러그인이 붙더라도 Hanging 문제를 예방합니다.
                
                # (A) 충돌 헤더 삭제
                for h in ["Transfer-Encoding", "Content-Encoding", "Content-Length"]:
                    if h in flow.response.headers: del flow.response.headers[h]

                # (B) 정확한 길이 재계산 및 명시
                new_length = len(flow.response.content)
                flow.response.headers["Content-Length"] = str(new_length)
                
                # (C) 보안 헤더 제거 (CSP 우회)
                self.sanitizer.sanitize(flow)

                frame_tag = "[IFRAME]" if is_iframe else "[TOP]"
                print(f"[Proxy] {frame_tag} Injected {matched_pids} into {current_url[:50]}... (Len: {new_length})")

        except Exception as e:
            print(f"[Proxy] Error processing {current_url}: {e}")