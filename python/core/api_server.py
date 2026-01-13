import sys
import os
import uvicorn
import logging
import asyncio
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import plugin_loader
from core.schemas import MatchResponse, MatchRequest, ScriptInjection
from core.matcher import UrlMatcher 
from core.inference_router import router as inference_router

# RemoteManager 임포트
try:
    from core.remote_manager import RemoteManager
except ImportError:
    RemoteManager = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("APIServer")

class PluginConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, plugin_id: str):
        await websocket.accept()
        if plugin_id not in self.active_connections:
            self.active_connections[plugin_id] = []
        self.active_connections[plugin_id].append(websocket)
        logger.info(f"[PluginMgr] Browser connected for plugin: {plugin_id}")

    def disconnect(self, websocket: WebSocket, plugin_id: str):
        if plugin_id in self.active_connections:
            if websocket in self.active_connections[plugin_id]:
                self.active_connections[plugin_id].remove(websocket)

    async def broadcast(self, plugin_id: str, message: dict):
        if plugin_id in self.active_connections:
            for connection in self.active_connections[plugin_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to plugin {plugin_id}: {e}")

plugin_ws_mgr = PluginConnectionManager()
remote_mgr = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global remote_mgr
    logger.info("Starting AI Engine API...")
    try:
        plugin_loader.load_plugins()
    except Exception as e:
        logger.error(f"Plugin Load Error: {e}")

    if RemoteManager:
        relay_host = os.getenv("RELAY_HOST", "127.0.0.1")
        relay_port = int(os.getenv("RELAY_PORT", "9000"))
        
        logger.info(f"Initializing RemoteManager to {relay_host}:{relay_port}")
        remote_mgr = RemoteManager(relay_host=relay_host, relay_port=relay_port)
        remote_mgr.on_command_received = plugin_ws_mgr.broadcast 
        asyncio.create_task(remote_mgr.start())
    yield
    logger.info("Shutting down AI Engine API...")
    if remote_mgr:
        remote_mgr.running = False

app = FastAPI(title="AI Engine API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

current_dir = os.path.dirname(os.path.abspath(__file__))
plugins_dir = os.path.abspath(os.path.join(current_dir, "../../plugins"))
if os.path.exists(plugins_dir):
    app.mount("/plugins", StaticFiles(directory=plugins_dir), name="plugins")

app.include_router(inference_router)

# [중요] 이 엔드포인트가 있어야 Main 프로세스가 서버 시작을 감지할 수 있습니다.
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai_engine"}

@app.websocket("/ws/plugin/connect/{plugin_id}")
async def websocket_plugin_endpoint(websocket: WebSocket, plugin_id: str):
    await plugin_ws_mgr.connect(websocket, plugin_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        plugin_ws_mgr.disconnect(websocket, plugin_id)

@app.post("/v1/match", response_model=MatchResponse)
async def match_endpoint(request: MatchRequest):
    try:
        url = request.url
        scripts = []
        plugins = plugin_loader.plugins
        
        for pid, ctx in plugins.items():
            for script in ctx.manifest.content_scripts:
                is_match = False
                for pattern in script.matches:
                    if UrlMatcher.match(pattern, url):
                        is_match = True
                        break
                if is_match:
                    for js in script.js:
                        scripts.append(ScriptInjection(
                            url=f"plugins/{pid}/{js}",
                            run_at=script.run_at
                        ))
        return MatchResponse(scripts=scripts)
    except Exception as e:
        logger.error(f"Match Error: {e}")
        return MatchResponse(scripts=[])

def run_api_server(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    run_api_server(args.port if args.port > 0 else 8000)