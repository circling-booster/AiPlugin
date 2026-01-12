import threading
import asyncio
import logging
import os
# [중요] 비 Windows 환경 호환성을 위해 try-except 처리 필요
try:
    import winreg
except ImportError:
    winreg = None
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import options
from core.api_server import run_api_server
from core.proxy_server import AiPlugsAddon
from utils.system_proxy import SystemProxy

class SystemOrchestrator:
    def __init__(self, api_port: int, proxy_port: int):
        self.api_port = api_port
        self.proxy_port = proxy_port
        self.logger = logging.getLogger("Orchestrator")
        self.system_proxy = SystemProxy()
        self.api_thread = None
        self.mitm_master = None

    # ▼▼▼ [누락된 부분] 아래 함수가 클래스 내부에 포함되어야 합니다 ▼▼▼
    def force_clear_system_proxy(self):
        """
        [Fail-Safe] Windows 레지스트리 강제 정리
        앱이 비정상 종료되었을 때 인터넷이 끊기는 문제를 방지합니다.
        """
        if os.name != 'nt' or winreg is None:
            return

        try:
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
                self.logger.info("[Fail-Safe] System proxy registry force cleared.")
        except Exception as e:
            self.logger.warning(f"[Fail-Safe] Failed to clear registry: {e}")
    # ▲▲▲ [누락된 부분] ▲▲▲

    def start_api_server(self):
        self.api_thread = threading.Thread(
            target=run_api_server, 
            args=(self.api_port,), 
            daemon=True
        )
        self.api_thread.start()
        self.logger.info(f"API Server started on port {self.api_port}")

    def enable_system_proxy(self):
        if self.proxy_port:
            self.system_proxy.set_proxy("127.0.0.1", self.proxy_port)
            self.logger.info(f"Windows Proxy set to 127.0.0.1:{self.proxy_port}")

    async def run_mitmproxy(self):
        # [중요] 프록시 포트가 없으면(Native-Only 모드) 실행하지 않음
        if not self.proxy_port:
            return

        opts = options.Options(listen_host='127.0.0.1', listen_port=self.proxy_port)
        self.mitm_master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        self.mitm_master.addons.add(AiPlugsAddon(self.api_port))
        
        self.logger.info(f"Mitmproxy running on port {self.proxy_port}")
        await self.mitm_master.run()

    def shutdown(self):
        self.logger.info("Shutting down...")
        # 종료 시에도 안전하게 레지스트리 정리 호출
        self.force_clear_system_proxy()
        self.system_proxy.disable_proxy()