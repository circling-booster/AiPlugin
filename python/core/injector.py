import re

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

def inject_script(html_content: bytes, api_port: int, plugin_scripts: list = []) -> bytes:
    """
    정규식 기반 고속 주입 (BeautifulSoup 미사용)
    """
    loader = get_loader_script(api_port)
    scripts = b""
    for url in plugin_scripts:
        scripts += f'<script src="{url}"></script>'.encode('utf-8')
    
    full_payload = loader + scripts

    # 1. <head> 태그 뒤에 주입
    if re.search(rb'(?i)<head[^>]*>', html_content):
        return re.sub(rb'(?i)(<head[^>]*>)', rb'\1' + full_payload, html_content, count=1)
    
    # 2. Fallback: <body> 태그 뒤에 주입
    if re.search(rb'(?i)<body[^>]*>', html_content):
        return re.sub(rb'(?i)(<body[^>]*>)', rb'\1' + full_payload, html_content, count=1)
        
    return full_payload + html_content