import threading
import asyncio
import logging
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import options
from core.api_server import run_api_server
from core.proxy_server import AiPlugsAddon
from utils.system_proxy import SystemProxy
import os

class SystemOrchestrator:
    """
    [Fixed] Path resolution adjusted for new directory structure
    """
    def __init__(self, api_port: int, proxy_port: int):
        self.api_port = api_port
        self.proxy_port = proxy_port
        self.logger = logging.getLogger("Orchestrator")
        self.system_proxy = SystemProxy()
        self.api_thread = None
        self.mitm_master = None

    def start_api_server(self):
        """API 서버를 별도 스레드로 실행"""
        self.api_thread = threading.Thread(
            target=run_api_server, 
            args=(self.api_port,), 
            daemon=True
        )
        self.api_thread.start()
        self.logger.info(f"API Server started on port {self.api_port}")

    def enable_system_proxy(self):
        """Windows 시스템 프록시 설정"""
        self.system_proxy.set_proxy("127.0.0.1", self.proxy_port)
        self.logger.info(f"Windows Proxy set to 127.0.0.1:{self.proxy_port}")

    async def run_mitmproxy(self):
        """Mitmproxy 실행 (Asyncio Event Loop)"""
        opts = options.Options(listen_host='127.0.0.1', listen_port=self.proxy_port)
        self.mitm_master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        
        # [Fix] 경로 수정: core/ 에서 plugins/ 로 가려면 두 단계 올라가야 함 (../../plugins)
        # 기존: join(..., '..', 'plugins') -> python/plugins (X)
        # 수정: join(..., '../../plugins') -> root/plugins (O)
        plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../plugins'))
        
        scripts = []
        if os.path.exists(plugins_dir):
            scripts = [f"http://localhost:{self.api_port}/plugins/{p}/content.js" 
                       for p in os.listdir(plugins_dir) 
                       if os.path.exists(os.path.join(plugins_dir, p, "content.js"))]
            self.logger.info(f"Injecting Scripts: {len(scripts)} found")
        else:
            self.logger.warning(f"Plugins directory not found: {plugins_dir}")

        # Addon 등록
        self.mitm_master.addons.add(AiPlugsAddon(self.api_port, scripts))
        
        self.logger.info(f"Mitmproxy running on port {self.proxy_port}")
        await self.mitm_master.run()

    def shutdown(self):
        """안전한 종료 절차"""
        self.logger.info("Shutting down...")
        self.system_proxy.disable_proxy()