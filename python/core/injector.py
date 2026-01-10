import re

# 정규표현식 미리 컴파일 (성능 최적화)
RE_HEAD = re.compile(rb'(?i)(<head[^>]*>)')
RE_HTML = re.compile(rb'(?i)(<html[^>]*>)')
RE_BODY_END = re.compile(rb'(?i)(</body>)')

def get_loader_script(api_port):
    """
    SPA 지원을 위한 History Hook 및 WebSocket 연결 정보 주입
    """
    return f"""
    <script>
    (function() {{
        console.log("[AiPlugs] Core Loader Injected. API: {api_port}");
        window.AIPLUGS_API_PORT = {api_port};
        
        // --- SPA History Hook ---
        const _pushState = history.pushState;
        const _replaceState = history.replaceState;
        
        history.pushState = function(...args) {{
            _pushState.apply(this, args);
            window.dispatchEvent(new Event('aiplugs:navigate'));
        }};
        
        history.replaceState = function(...args) {{
            _replaceState.apply(this, args);
            window.dispatchEvent(new Event('aiplugs:navigate'));
        }};
        
        window.addEventListener('popstate', () => {{
            window.dispatchEvent(new Event('aiplugs:navigate'));
        }});
    }})();
    </script>
    """.encode('utf-8')

def _make_script_tags(urls: list) -> bytes:
    """URL 리스트를 <script> 태그 바이트열로 변환"""
    tags = b""
    for url in urls:
        tags += f'<script src="{url}"></script>'.encode('utf-8')
    return tags

def inject_script(html_content: bytes, api_port: int, head_scripts: list = [], body_scripts: list = []) -> bytes:
    """
    [Refactored] 위치별(Head/Body) 분리 주입
    """
    loader = get_loader_script(api_port)
    
    # 1. Head Injection (Core Loader는 항상 먼저 실행되어야 함)
    # document_start 스크립트들도 여기에 포함
    payload_head = loader + _make_script_tags(head_scripts)
    
    # 2. Body Injection (document_end / document_idle)
    payload_body = _make_script_tags(body_scripts)

    modified_html = html_content

    # --- Apply Head Injection ---
    # <head> 태그 직후에 삽입
    if payload_head:
        if RE_HEAD.search(modified_html):
            modified_html = RE_HEAD.sub(rb'\1' + payload_head, modified_html, count=1)
        elif RE_HTML.search(modified_html): # fallback: html 태그 뒤
             modified_html = RE_HTML.sub(rb'\1' + payload_head, modified_html, count=1)
        else:
             # 정말 아무 태그도 없으면 맨 앞에 붙임
             modified_html = payload_head + modified_html
    
    # --- Apply Body Injection ---
    # </body> 태그 직전에 삽입
    if payload_body:
        if RE_BODY_END.search(modified_html):
            modified_html = RE_BODY_END.sub(payload_body + rb'\1', modified_html, count=1)
        else:
            # Body 닫는 태그가 없으면 맨 뒤에 붙임
            modified_html += payload_body

    return modified_html