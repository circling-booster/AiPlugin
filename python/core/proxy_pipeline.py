from mitmproxy import http
from core.plugin_loader import plugin_loader
from core.injector import inject_script
from core.security import SecuritySanitizer

class ProxyHandler:
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        return True

class ContentTypeFilter(ProxyHandler):
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        content_type = flow.response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return False
        return True

class ResourceFilter(ProxyHandler):
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        request_headers = flow.request.headers
        sec_fetch_dest = request_headers.get("Sec-Fetch-Dest", None)
        sec_fetch_mode = request_headers.get("Sec-Fetch-Mode", None)

        if sec_fetch_dest == "empty": return False
        if sec_fetch_mode in ["cors", "websocket", "no-cors"]: return False

        is_iframe = sec_fetch_dest in ["iframe", "frame"]
        
        # Navigate 모드가 아니면 차단 (AJAX 등 방지)
        if not is_iframe and sec_fetch_mode and sec_fetch_mode != "navigate":
            return False
            
        context['is_iframe'] = is_iframe
        return True

class Decoder(ProxyHandler):
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        # Gzip/Brotli 압축 해제 (필수)
        flow.response.decode()
        context['decoded'] = True 
        return True

class PluginMatcher(ProxyHandler):
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        url = flow.request.url
        matched_pids = []
        for pid, ctx in plugin_loader.plugins.items():
            for pattern in ctx.compiled_patterns:
                if pattern.match(url):
                    matched_pids.append(pid)
                    break
        
        context['matched_pids'] = matched_pids
        return True

class Injector(ProxyHandler):
    def __init__(self, api_port: int):
        self.api_port = api_port

    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        matched_pids = context.get('matched_pids', [])
        if not matched_pids:
            return True

        is_iframe = context.get('is_iframe', False)
        head_scripts = []
        body_scripts = []
        
        for pid in matched_pids:
            ctx = plugin_loader.get_plugin(pid)
            if not ctx: continue
            
            for script_block in ctx.manifest.content_scripts:
                # Iframe 필터링
                if is_iframe and not script_block.all_frames:
                    continue
                
                # 실행 시점에 따라 위치 분류
                target_list = head_scripts if script_block.run_at == "document_start" else body_scripts
                for js_file in script_block.js:
                    # 로컬 API 서버를 통해 서빙되는 스크립트 URL 생성
                    url = f"http://127.0.0.1:{self.api_port}/plugins/{pid}/{js_file}"
                    target_list.append(url)
        
        if head_scripts or body_scripts:
            # 캐시 무효화 (스크립트 갱신 보장)
            for h in ["Cache-Control", "Expires", "ETag"]:
                if h in flow.response.headers: del flow.response.headers[h]

            html = flow.response.content
            
            # [수정됨] 함수형 inject_script 호출
            modified = inject_script(html, self.api_port, head_scripts, body_scripts)
            
            flow.response.content = modified
            context['injected'] = True
            
            frame_tag = "[IFRAME]" if is_iframe else "[TOP]"
            print(f"[Proxy] {frame_tag} Injected {matched_pids} into {flow.request.url[:50]}...")
            
        return True

class HeaderNormalizer(ProxyHandler):
    def __init__(self):
        self.sanitizer = SecuritySanitizer()

    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        if context.get('injected') or context.get('decoded'):
            # Chunked 인코딩 제거 및 Length 재계산
            for h in ["Transfer-Encoding", "Content-Encoding"]:
                if h in flow.response.headers: del flow.response.headers[h]

            new_length = len(flow.response.content)
            flow.response.headers["Content-Length"] = str(new_length)
            
            # 보안 헤더 제거 (CSP 등)
            if context.get('injected'):
                self.sanitizer.sanitize(flow)
                
        return True