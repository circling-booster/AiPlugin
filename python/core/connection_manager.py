#기존 api_server 에서 분리된 파일(connection_manger & inference_router)

import asyncio
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 라우터 생성
router = APIRouter()

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

# 전역 매니저 인스턴스
manager = ConnectionManager()

@router.websocket("/ws/{plugin_id}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, plugin_id: str, client_id: str):
    await manager.connect(websocket, plugin_id, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            # [Echo] 실제로는 Local Process IPC 큐로 전달
            await websocket.send_text(f"Core Echo: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(plugin_id, client_id)