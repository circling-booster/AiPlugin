import os
import json
import httpx
from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
from core.plugin_loader import plugin_loader
from core.runtime_manager import runtime_manager

load_dotenv()
router = APIRouter()

def get_cloud_config():
    # (기존과 동일)
    config_data = {}
    try:
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../config/config.json'))
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            config_data = data.get('system_settings', {}).get('cloud_inference', {})
    except Exception:
        pass
    
    env_api_key = os.getenv("SYSTEM_API_KEY")
    if env_api_key: config_data['system_api_key'] = env_api_key
    env_base_url = os.getenv("CLOUD_BASE_URL")
    if env_base_url: config_data['base_url'] = env_base_url
        
    return config_data

@router.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        raise HTTPException(status_code=404, detail="Plugin not found")

    payload = await request.json()
    # payload 내부의 실제 데이터 추출 (클라이언트가 payload: { ... } 형태로 보낸다고 가정)
    data = payload.get("payload", payload)

    # CASE A: Web Mode (Relay to Cloud)
    if ctx.mode == "web":
        # (기존 코드와 동일)
        cloud_conf = get_cloud_config()
        base_url = cloud_conf.get('base_url', "http://localhost:8000")
        api_key = cloud_conf.get('system_api_key', "")
        
        target = f"{base_url}/v1/inference/{plugin_id}/{function_name}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(target, json=payload, headers=headers, timeout=30.0)
                if resp.status_code != 200:
                    return {"status": "error", "code": resp.status_code, "message": f"Cloud Error: {resp.text}"}
                return resp.json()
            except Exception as e:
                return {"status": "error", "message": f"Web Relay Failed: {str(e)}"}

    # CASE B: Local Mode (Process Communication)
    elif ctx.mode == "local":
        try:
            # 1. 프로세스 상태 확인 및 실행 (Lazy Load)
            runtime_manager.ensure_process_running(plugin_id)
            
            # 2. 연결 객체 확인
            conn = ctx.connection
            if not conn:
                raise RuntimeError("Process running but connection lost")

            # 3. 데이터 전송 (IPC Send)
            conn.send(data)

            # 4. 결과 대기 (IPC Recv) - Timeout 10초 설정
            if conn.poll(10):
                result = conn.recv()
                return result
            else:
                return {"status": "error", "message": "Inference Timeout (Local Process did not respond)"}

        except Exception as e:
            return {"status": "error", "message": f"Local Inference Failed: {str(e)}"}