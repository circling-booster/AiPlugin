import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
from core.plugin_loader import plugin_loader
from core.runtime_manager import runtime_manager

# .env 로드
load_dotenv()

# 라우터 생성
router = APIRouter()

def get_cloud_config():
    """
    config.json에서 설정을 로드하되, 환경변수가 있다면 우선시합니다.
    """
    config_data = {}
    try:
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../config/config.json'))
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            config_data = data.get('system_settings', {}).get('cloud_inference', {})
    except Exception as e:
        print(f"[Config] Failed to load cloud config: {e}")
    
    # [Fixed] Override with Environment Variables (Synchronization from Electron)
    env_api_key = os.getenv("SYSTEM_API_KEY")
    if env_api_key:
        config_data['system_api_key'] = env_api_key
        
    env_base_url = os.getenv("CLOUD_BASE_URL")
    if env_base_url:
        config_data['base_url'] = env_base_url
        
    return config_data

@router.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Plugin not found")

    payload = await request.json()

    # CASE A: Web Mode (Relay to Cloud)
    if ctx.mode == "web":
        cloud_conf = get_cloud_config()
        
        base_url = cloud_conf.get('base_url', "http://localhost:8000")
        api_key = cloud_conf.get('system_api_key', "")
        
        target = f"{base_url}/v1/inference/{plugin_id}/{function_name}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(target, json=payload, headers=headers, timeout=30.0)
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
            status = runtime_manager.ensure_process_running(plugin_id)
            return {
                "status": "success",
                "mode": "local",
                "message": "Processed by Local Lazy Process (CPU Optimized)",
                "pid": status.get("pid"),
                "debug_info": status
            }
        except Exception as e:
            return {"status": "error", "message": f"Local Inference Failed: {str(e)}"}