import threading
import asyncio
import logging
import os
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import options
from core.api_server import run_api_server
from core.proxy_server import AiPlugsAddon
from utils.system_proxy import SystemProxy

class SystemOrchestrator:
    """
    [Refactored] 스크립트 수집 역할을 Proxy Server에게 위임하여 구조 단순화
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
        
        # [Fix] 기존의 scripts 리스트 생성 로직 제거
        # 이제 Proxy Addon이 PluginLoader를 통해 직접 판단합니다.
        
        # Addon 등록 (스크립트 리스트 전달 제거)
        self.mitm_master.addons.add(AiPlugsAddon(self.api_port))
        
        self.logger.info(f"Mitmproxy running on port {self.proxy_port}")
        await self.mitm_master.run()

    def shutdown(self):
        """안전한 종료 절차"""
        self.logger.info("Shutting down...")
        self.system_proxy.disable_proxy()