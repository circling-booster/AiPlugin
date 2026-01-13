import logging
import os

logger = logging.getLogger("Injector")

class ScriptInjector:
    @staticmethod
    def inject_script(html_content: bytes, url: str, scripts: list) -> bytes:
        """
        Injects window.__AI_API_BASE_URL__ and content scripts.
        """
        try:
            # Retrieve Dynamic Port from Environment (Set by main.py)
            port = os.environ.get("AI_ENGINE_PORT", "0")
            base_url = f"http://127.0.0.1:{port}"
            
            injection = f"""
            <script>
                window.__AI_API_BASE_URL__ = "{base_url}";
                console.log("[SOA] AI API Base URL:", window.__AI_API_BASE_URL__);
            </script>
            """
            
            # Injection Strategy
            head_tag = b"<head>"
            if head_tag in html_content:
                return html_content.replace(head_tag, head_tag + injection.encode('utf-8'))
            
            return html_content + injection.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Injection Failed: {e}")
            return html_content

injector = ScriptInjector()