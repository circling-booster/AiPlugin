import re
from mitmproxy import http
from core.plugin_loader import plugin_loader
from core.security import SecuritySanitizer
from core.matcher import UrlMatcher  # [New] 공용 매처 임포트

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
        # Gzip/Brotli 압축 해제
        flow.response.decode()
        context['decoded'] = True 
        return True

class PluginMatcher(ProxyHandler):
    def process(self, flow: http.HTTPFlow, context: dict) -> bool:
        url = flow.request.url
        matched_pids = []
        
        # [수정] 정규식 컴파일된 패턴 대신 UrlMatcher 사용
        for pid, ctx in plugin_loader.plugins.items():
            for script_block in ctx.manifest.content_scripts:
                matched = False
                for pattern in script_block.matches:
                    if UrlMatcher.match(pattern, url):
                        matched = True
                        break
                if matched:
                    if pid not in matched_pids:
                        matched_pids.append(pid)
                    # 하나의 플러그인에서 하나라도 맞으면 해당 플러그인은 대상
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
        scripts_to_inject = []
        
        for pid in matched_pids:
            ctx = plugin_loader.get_plugin(pid)
            if not ctx: continue
            
            for script_block in ctx.manifest.content_scripts:
                # Iframe 필터링
                if is_iframe and not script_block.all_frames:
                    continue
                
                # 해당 스크립트 블록이 현재 URL과 매칭되는지 다시 확인 (세부 매칭)
                is_block_match = False
                for pattern in script_block.matches:
                    if UrlMatcher.match(pattern, flow.request.url):
                        is_block_match = True
                        break
                
                if is_block_match:
                    for js_file in script_block.js:
                        # API 서버를 통해 서빙되는 URL 생성
                        url = f"http://127.0.0.1:{self.api_port}/plugins/{pid}/{js_file}"
                        scripts_to_inject.append(f'<script src="{url}"></script>')
        
        if scripts_to_inject:
            # 캐시 무효화
            for h in ["Cache-Control", "Expires", "ETag"]:
                if h in flow.response.headers: del flow.response.headers[h]

            # [수정] Robust HTML Injection Logic
            html = flow.response.text # text 속성 사용하여 문자열 처리
            injection_code = "\n".join(scripts_to_inject)
            
            # 대소문자 구분 없이 </body> 태그 찾기
            pattern = re.compile(r'(</body>)', re.IGNORECASE)
            
            if pattern.search(html):
                # </body> 앞에 주입
                flow.response.text = pattern.sub(lambda m: injection_code + m.group(0), html)
            else:
                # 태그가 없으면 맨 뒤에 추가
                flow.response.text = html + injection_code

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

            # Content-Length 갱신
            if flow.response.content:
                new_length = len(flow.response.content)
                flow.response.headers["Content-Length"] = str(new_length)
            
            # 보안 헤더 제거
            if context.get('injected'):
                self.sanitizer.sanitize(flow)
                
        return True