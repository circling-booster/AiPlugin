import json
import os
import uuid
import asyncio
import logging
import websockets
from typing import Optional, Callable, Awaitable

from core.plugin_loader import plugin_loader

logger = logging.getLogger("RemoteManager")

class RemoteManager:
    def __init__(self, relay_host: str = "127.0.0.1", relay_port: int = 9000):
        # 1. 고유 세션 ID 생성
        self.session_id = str(uuid.uuid4())[:8]
        
        # 2. Relay 서버 접속 URL 설정
        self.relay_url = f"ws://{relay_host}:{relay_port}/ws/host/{self.session_id}"
        self.relay_host = relay_host
        self.relay_port = relay_port
        
        # 3. 상태 제어 플래그
        self.running = False
        
        # 4. 명령 수신 시 호출할 콜백 함수 (api_server.py에서 주입)
        self.on_command_received: Optional[Callable[[str, dict], Awaitable[None]]] = None

        self._print_connection_info()

    def _print_connection_info(self):
        print("\n" + "="*60)
        print(f"🚀 [Remote Control] Online")
        print(f"🔗 Relay Server: {self.relay_host}:{self.relay_port}")
        print(f"📱 Access URL : http://{self.relay_host}:{self.relay_port}/remote/{self.session_id}")
        print("="*60 + "\n")

    async def start(self):
        """메인 실행 루프: Relay 서버와 연결 유지"""
        self.running = True
        logger.info(f"Starting RemoteManager (Session: {self.session_id})")

        while self.running:
            try:
                async with websockets.connect(self.relay_url) as ws:
                    logger.info("✅ Connected to Relay Server")
                    
                    # 1. 원격 제어 UI가 있는 플러그인 등록
                    await self._register_plugins(ws)
                    
                    # 2. 메시지 수신 대기 루프
                    async for message in ws:
                        if not self.running:
                            break
                            
                        try:
                            data = json.loads(message)
                            if data.get("type") == "command":
                                await self._handle_command(data)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON received: {message}")
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            
            except (ConnectionRefusedError, websockets.exceptions.ConnectionClosed):
                logger.warning(f"❌ Relay connection lost. Retrying in 5s... (Target: {self.relay_url})")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Critical RemoteManager Error: {e}")
                await asyncio.sleep(5)

    async def _register_plugins(self, ws):
        """로드된 플러그인 중 remote_ui 설정이 있는 항목을 Relay 서버에 등록"""
        if not plugin_loader.plugins:
            logger.warning("No plugins loaded to register.")
            return

        for pid, ctx in plugin_loader.plugins.items():
            if hasattr(ctx.manifest, 'remote_ui') and ctx.manifest.remote_ui.enabled:
                config = ctx.manifest.remote_ui
                
                # [수정] ctx.path -> ctx.base_path (PluginLoader 정의와 일치시킴)
                ui_path = os.path.join(ctx.base_path, config.entry_point)
                
                if os.path.exists(ui_path):
                    try:
                        with open(ui_path, "r", encoding="utf-8") as f:
                            html_content = f.read()
                        
                        payload = {
                            "type": "register_ui",
                            "plugin_id": pid,
                            "html": html_content,
                            "title": config.title
                        }
                        await ws.send(json.dumps(payload))
                        logger.info(f"Registered UI for plugin: {pid}")
                        
                    except Exception as e:
                        logger.error(f"Failed to read/register UI for {pid}: {e}")
                else:
                    logger.warning(f"UI entry point not found for {pid}: {ui_path}")

    async def _handle_command(self, payload: dict):
        plugin_id = payload.get("plugin_id")
        action = payload.get("action", "unknown")
        value = payload.get("value", "N/A")
        
        logger.info(f"🕹️ Command Received [{plugin_id}]: {action} -> {value}")
        
        if self.on_command_received:
            try:
                await self.on_command_received(plugin_id, payload)
            except Exception as e:
                logger.error(f"Callback execution failed: {e}")