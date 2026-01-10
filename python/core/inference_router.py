import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException
from core.plugin_loader import plugin_loader
# [New] 프로세스 런타임 관리를 위한 매니저 임포트
from core.runtime_manager import runtime_manager

# 라우터 생성
router = APIRouter()

def get_cloud_config():
    """
    config.json에서 클라우드 추론 서버 설정(URL, API Key)을 로드합니다.
    경로: python/core/../../config/config.json
    """
    try:
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../config/config.json'))
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('system_settings', {}).get('cloud_inference', {})
    except Exception as e:
        print(f"[Config] Failed to load cloud config: {e}")
        return {}

@router.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
    """
    [Refactored] Dynamic Inference Routing with RuntimeManager
    - Web Mode: config.json 설정을 기반으로 클라우드 서버로 릴레이 (보안 키 포함)
    - Local Mode: RuntimeManager를 통해 로컬 프로세스(Worker) 제어
    """
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Plugin not found")

    payload = await request.json()

    # CASE A: Web Mode (Relay to Cloud)
    if ctx.mode == "web":
        cloud_conf = get_cloud_config()
        
        # 설정이 없으면 기본값 사용 (개발 편의성)
        base_url = cloud_conf.get('base_url', "http://localhost:8000")
        api_key = cloud_conf.get('system_api_key', "")
        
        target = f"{base_url}/v1/inference/{plugin_id}/{function_name}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                # 무거운 작업을 가정하여 타임아웃을 30초로 넉넉하게 설정
                resp = await client.post(target, json=payload, headers=headers, timeout=30.0)
                
                # 클라우드 측 에러 처리
                if resp.status_code != 200:
                    return {
                        "status": "error", 
                        "code": resp.status_code, 
                        "message": f"Cloud Error: {resp.text}"
                    }
                    
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
            # 현재는 데모용으로 프로세스 PID만 반환
            
            return {
                "status": "success",
                "mode": "local",
                "message": "Processed by Local Lazy Process (CPU Optimized)",
                "pid": status.get("pid"),
                "debug_info": status
            }
        except Exception as e:
            return {"status": "error", "message": f"Local Inference Failed: {str(e)}"}