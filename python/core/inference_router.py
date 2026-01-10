#기존 api_server 에서 분리된 파일(connection_manger & inference_router)

import httpx
from fastapi import APIRouter, Request, HTTPException
from core.plugin_loader import plugin_loader

# 라우터 생성
router = APIRouter()

@router.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
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
        # 주의: 실제 운영 시 localhost 대신 실제 클라우드 주소 사용
        CLOUD_URL = "http://localhost:8000"
        target = f"{CLOUD_URL}/v1/inference/{plugin_id}/{function_name}"
        
        async with httpx.AsyncClient() as client:
            try:
                # [Optimization] Timeout 설정
                resp = await client.post(target, json=payload, timeout=15.0)
                return resp.json()
            except Exception as e:
                # 에러 발생 시 JSON 형태로 반환하여 클라이언트가 처리하기 쉽게 함
                return {"status": "error", "message": f"Web Relay Failed: {str(e)}"}

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