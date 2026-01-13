# python/core/proxy_pipeline.py

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
        
        if not is_iframe and sec_fetch_mode and sec_fetch_mode != "navigate":
            return False
            
        context['is_iframe'] = is_iframe
        return True

class Decoder(ProxyHandler):
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        # [핵심] 디코딩 수행 및 플래그 설정 (헤더 재계산 트리거)
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
        
        if not matched_pids:
            context['matched_pids'] = []
            return True
            
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
                if is_iframe and not script_block.all_frames:
                    continue
                
                target_list = head_scripts if script_block.run_at == "document_start" else body_scripts
                for js_file in script_block.js:
                    url = f"http://localhost:{self.api_port}/plugins/{pid}/{js_file}"
                    target_list.append(url)
        
        if head_scripts or body_scripts:
            for h in ["Cache-Control", "Expires", "ETag"]:
                if h in flow.response.headers: del flow.response.headers[h]

            html = flow.response.content
            # inject_script 함수는 기존 injector.py 사용
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
        # [핵심] 주입되었거나(injected) 혹은 압축이 풀렸다면(decoded) 반드시 헤더 정리
        if context.get('injected') or context.get('decoded'):
            for h in ["Transfer-Encoding", "Content-Encoding"]:
                if h in flow.response.headers: del flow.response.headers[h]

            new_length = len(flow.response.content)
            flow.response.headers["Content-Length"] = str(new_length)
            
            if context.get('injected'):
                self.sanitizer.sanitize(flow)
                
        return True