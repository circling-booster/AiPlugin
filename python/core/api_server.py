import asyncio
import httpx
import uvicorn
import os
import multiprocessing
import importlib.util
import queue  # For queue.Empty
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any

# Core Module Import
from core.plugin_loader import plugin_loader, PluginLoader

# =============================================================================
# [CRITICAL FIX] Monkey Patching PluginLoader
# 기존 plugin_loader는 모듈을 import만 하고 실행하지 않음.
# Worker Process가 backend.run(queue)를 호출하도록 런타임에 동작을 수정함.
# =============================================================================
def patched_worker_entry(p_id, path, queue):
    """Patched Entry Point to support IPC Queue injection"""
    import sys
    # Add plugin directory to path
    sys.path.append(os.path.dirname(path))
    
    try:
        spec = importlib.util.spec_from_file_location("backend", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # [NEW] Check for 'run' function and execute with queue
        if hasattr(module, 'run') and callable(module.run):
            module.run(queue)
        else:
            # Fallback for legacy plugins
            import time
            while True: time.sleep(1)
            
    except Exception as e:
        print(f"[{p_id}] Worker Crash: {e}")

# Apply Patch
PluginLoader._worker_entry = staticmethod(patched_worker_entry)
# =============================================================================


app = FastAPI()

# [Legacy] CORS Config Preservation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Plugins
plugin_loader.load_plugins()

# Mount Static Files
if os.path.isdir(plugin_loader.plugins_dir):
    app.mount("/plugins", StaticFiles(directory=plugin_loader.plugins_dir), name="plugins")
else:
    print(f"[API] Warning: Plugins directory not found at {plugin_loader.plugins_dir}")

# [IPC] Global Manager for Return Queues
ipc_manager = multiprocessing.Manager()


class ConnectionManager:
    """[Legacy] Preserved Connection Manager"""
    def __init__(self):
        self.active_connections: Dict[tuple, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, plugin_id: str, client_id: str):
        await websocket.accept()
        key = (plugin_id, client_id)
        async with self.lock:
            if key in self.active_connections:
                try:
                    await self.active_connections[key].close(code=1000)
                except: pass
            self.active_connections[key] = websocket

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
            await websocket.send_text(f"Core Echo: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(plugin_id, client_id)


# -----------------------------------------------------------------------------
# [Task 4] Universal Dynamic Routing Implementation
# Path: /api/plugin/{plugin_id}/{action}
# -----------------------------------------------------------------------------
@app.post("/api/plugin/{plugin_id}/{action}")
async def generic_plugin_router(plugin_id: str, action: str, request: Request):
    """
    모든 플러그인에 대한 범용 라우팅 처리.
    Web Mode: 클라우드 릴레이 / Local Mode: IPC 프로세스 통신
    """
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    payload = await request.json()

    # --- CASE A: Web Mode (Relay to Cloud) ---
    if ctx.mode == "web":
        # 실제 환경에선 config.json에서 URL 로드
        CLOUD_URL = "http://localhost:8000" 
        target_url = f"{CLOUD_URL}/predict" # Cloud Spec (/predict)
        
        # Cloud Server가 action 식별이 필요할 수 있으므로 병합
        relay_payload = {**payload, "plugin_id": plugin_id, "action": action}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(target_url, json=relay_payload, timeout=20.0)
                return resp.json()
            except Exception as e:
                return {"status": "error", "message": f"Cloud Relay Failed: {str(e)}"}

    # --- CASE B: Local Mode (Lazy Loading + IPC) ---
    elif ctx.mode == "local":
        try:
            # 1. Ensure Process (Lazy Loading)
            plugin_loader.ensure_process_running(plugin_id)
            
            if not ctx.ipc_queue:
                raise HTTPException(status_code=500, detail="IPC Queue initialization failed")

            # 2. Create Return Queue (One-off)
            return_queue = ipc_manager.Queue()

            # 3. Send Request
            request_packet = {
                "action": action,
                "payload": payload,
                "reply_to": return_queue
            }
            ctx.ipc_queue.put(request_packet)

            # 4. Wait for Result (Non-blocking)
            # asyncio.to_thread를 사용하여 Blocking I/O를 별도 스레드에서 처리
            try:
                result = await asyncio.to_thread(return_queue.get, timeout=15.0)
                return result
            except queue.Empty:
                return {"status": "error", "message": "Plugin process timed out (15s)"}
                
        except Exception as e:
            return {"status": "error", "message": f"Local Inference Error: {str(e)}"}

    else:
        raise HTTPException(status_code=400, detail=f"Invalid plugin mode: {ctx.mode}")

def run_api_server(port: int):
    # Windows Multiprocessing Support
    multiprocessing.freeze_support()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")