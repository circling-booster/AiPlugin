import asyncio
import httpx
import uvicorn
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles  # <--- [1] 추가
from typing import Dict
from core.plugin_loader import plugin_loader

app = FastAPI()

# 서버 시작 시 플러그인 메타데이터 로드
plugin_loader.load_plugins()

# [2] 정적 파일 경로 마운트 (이 부분이 누락되어 404 오류 발생함)
# 플러그인의 content.js 파일을 브라우저가 접근할 수 있도록 허용
if os.path.isdir(plugin_loader.plugins_dir):
    app.mount("/plugins", StaticFiles(directory=plugin_loader.plugins_dir), name="plugins")
else:
    print(f"[API] Warning: Plugins directory not found at {plugin_loader.plugins_dir}")

class ConnectionManager:
    """
    [Task 4] Robust Connection Management
    Prevents zombie connections in SPA environments.
    """
    def __init__(self):
        # Key: (plugin_id, client_id)
        self.active_connections: Dict[tuple, WebSocket] = {}
        self.lock = asyncio.Lock() # [Optimization] Thread-safety

    async def connect(self, websocket: WebSocket, plugin_id: str, client_id: str):
        await websocket.accept()
        key = (plugin_id, client_id)

        async with self.lock:
            # [Zombie Killer] 기존 연결이 있다면 강제 종료
            if key in self.active_connections:
                old_ws = self.active_connections[key]
                try:
                    await old_ws.close(code=1000, reason="New connection replaced old one")
                    print(f"[API] Killed zombie connection: {key}")
                except Exception:
                    pass
            
            self.active_connections[key] = websocket
            print(f"[API] Connected: {key}")

    async def disconnect(self, plugin_id: str, client_id: str):
        key = (plugin_id, client_id)
        async with self.lock:
            if key in self.active_connections:
                del self.active_connections[key]

manager = ConnectionManager()

@app.websocket("/ws/{plugin_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, plugin_id: str, client_id: str):
    await manager.connect(websocket, plugin_id, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # [Echo] 실제로는 Local Process IPC 큐로 전달
            await websocket.send_text(f"Core Echo: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(plugin_id, client_id)

@app.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_router(plugin_id: str, function_name: str, request: Request):
    """
    [Task 3] Dynamic Inference Routing
    """
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Plugin not found")

    payload = await request.json()

    # CASE A: Web Mode (Relay to Cloud)
    if ctx.mode == "web":
        # Config에서 Cloud URL 로드 필요 (여기선 로컬 시뮬레이션 포트 8000)
        CLOUD_URL = "http://localhost:8000"
        target = f"{CLOUD_URL}/v1/inference/{plugin_id}/{function_name}"
        
        async with httpx.AsyncClient() as client:
            try:
                # [Optimization] Timeout 설정
                resp = await client.post(target, json=payload, timeout=15.0)
                return resp.json()
            except Exception as e:
                return {"status": "error", "message": f"Web Relay Failed: {e}"}

    # CASE B: Local Mode (Lazy Loading)
    elif ctx.mode == "local":
        # 1. Trigger Lazy Loading (Process Spawn if needed)
        plugin_loader.ensure_process_running(plugin_id)
        
        # 2. IPC Communication Mock
        # ctx.ipc_queue.put(payload) ...
        return {
            "status": "success",
            "mode": "local",
            "message": "Processed by Local Lazy Process",
            "pid": ctx.process.pid if ctx.process else None
        }

def run_api_server(port: int):
    """
    Main Process에서 Thread로 실행되는 함수
    """
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")