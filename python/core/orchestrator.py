import threading
import asyncio
import logging
import os
import re
from urllib.parse import urlparse
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import options
from core.api_server import run_api_server
from core.proxy_server import AiPlugsAddon
from utils.system_proxy import SystemProxy
# [New] 플러그인 정보를 읽기 위해 로더 임포트
from core.plugin_loader import plugin_loader

class SystemOrchestrator:
    """
    [Refactored] 스크립트 수집 역할을 Proxy Server에게 위임하여 구조 단순화
    [Updated] allow_hosts 옵션을 통해 타겟 사이트 외에는 간섭하지 않도록 설정
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

    def _generate_allow_hosts_regex(self) -> list:
        """
        로드된 플러그인들의 매치 패턴을 분석하여 mitmproxy의 allow_hosts 정규식을 생성합니다.
        """
        allowed_domains = set()
        has_all_urls = False

        for ctx in plugin_loader.plugins.values():
            for script in ctx.manifest.content_scripts:
                for match_pattern in script.matches:
                    if match_pattern == "<all_urls>":
                        has_all_urls = True
                        break
                    
                    # 간단한 파싱: *://ticket.melon.com/* -> ticket.melon.com 추출
                    # 정교한 파싱을 위해 정규식 사용 또는 urlparse 사용
                    # 여기서는 단순화를 위해 *:// 제거 후 / 전까지를 도메인으로 간주
                    try:
                        # *:// 제거
                        clean_pat = match_pattern.replace("*://", "")
                        # 첫번째 / 앞부분이 도메인 (포트 포함 가능)
                        if "/" in clean_pat:
                            domain = clean_pat.split("/")[0]
                        else:
                            domain = clean_pat
                        
                        # 와일드카드(*)를 정규식 표현(.*)으로 변경
                        regex_domain = domain.replace("*", ".*").replace(".", r"\.")
                        allowed_domains.add(regex_domain)
                    except Exception:
                        pass
            if has_all_urls:
                break
        
        if has_all_urls:
            self.logger.info("[Orchestrator] Plugin with <all_urls> detected. Intercepting ALL traffic.")
            return [] # 빈 리스트면 모든 호스트 허용
        
        if not allowed_domains:
            self.logger.warning("[Orchestrator] No match patterns found. Proxy might pass through everything.")
            return []

        # 정규식 리스트 생성 (mitmproxy allow_hosts는 정규식 리스트를 받음)
        # 도메인 또는 IP가 매칭되면 인터셉트
        final_regex_list = list(allowed_domains)
        self.logger.info(f"[Orchestrator] Allow Hosts Filter Active: {final_regex_list}")
        return final_regex_list

    async def run_mitmproxy(self):
        """Mitmproxy 실행 (Asyncio Event Loop)"""
        # 1. 기본 옵션 설정
        opts = options.Options(listen_host='127.0.0.1', listen_port=self.proxy_port)
        self.mitm_master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        
        # 2. Addon 등록 (이 시점에서 PluginLoader가 내부적으로 load_plugins()를 수행함)
        # AiPlugsAddon 내부 __init__에서 plugin_loader.load_plugins()가 호출됩니다.
        self.mitm_master.addons.add(AiPlugsAddon(self.api_port))
        
        # 3. [Core Logic] 플러그인 로드 후 allow_hosts 옵션 동적 적용
        # 플러그인이 로드된 상태이므로 패턴 추출 가능
        allow_regexs = self._generate_allow_hosts_regex()
        if allow_regexs:
            # mitmproxy 옵션 업데이트
            self.mitm_master.options.allow_hosts = allow_regexs
        
        self.logger.info(f"Mitmproxy running on port {self.proxy_port}")
        await self.mitm_master.run()

    def shutdown(self):
        """안전한 종료 절차"""
        self.logger.info("Shutting down...")
        self.system_proxy.disable_proxy()