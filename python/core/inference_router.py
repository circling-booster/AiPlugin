import httpx
from fastapi import APIRouter, Request, HTTPException
from core.plugin_loader import plugin_loader
# [New] 프로세스 런타임 관리를 위한 매니저 임포트
from core.runtime_manager import runtime_manager

# 라우터 생성
router = APIRouter()

@router.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
    """
    [Refactored] Dynamic Inference Routing with RuntimeManager
    """
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Plugin not found")

    payload = await request.json()

    # CASE A: Web Mode (Relay to Cloud)
    if ctx.mode == "web":
        # 주의: 실제 운영 시 config.json 등에서 Cloud URL 로드 필요
        CLOUD_URL = "http://localhost:8000"
        target = f"{CLOUD_URL}/v1/inference/{plugin_id}/{function_name}"
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(target, json=payload, timeout=15.0)
                return resp.json()
            except Exception as e:
                return {"status": "error", "message": f"Web Relay Failed: {str(e)}"}

    # CASE B: Local Mode (Lazy Loading)
    elif ctx.mode == "local":
        try:
            # [Refactor] PluginLoader 대신 RuntimeManager에게 프로세스 준비 요청
            status = runtime_manager.ensure_process_running(plugin_id)
            
            # 프로세스가 준비되었으므로 IPC 통신 수행 (ctx.ipc_queue 사용)
            # 예: ctx.ipc_queue.put(payload) ...
            
            return {
                "status": "success",
                "mode": "local",
                "message": "Processed by Local Lazy Process",
                "pid": status.get("pid"),
                "debug_info": status
            }
        except Exception as e:
            return {"status": "error", "message": f"Local Inference Failed: {str(e)}"}