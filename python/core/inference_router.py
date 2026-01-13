import os
import json
import logging
import httpx
from fastapi import APIRouter, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from dotenv import load_dotenv

# [추가] AI Engine 직접 호출을 위한 임포트
from core.ai_engine import ai_engine 
from core.plugin_loader import plugin_loader
from core.runtime_manager import runtime_manager

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("AiPlugs.Router")

load_dotenv()
router = APIRouter()

def get_cloud_config():
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

def _communicate_ipc(ctx, data):
    """
    동기(Blocking) IPC 통신을 수행하는 헬퍼 함수.
    run_in_threadpool을 통해 비동기 래핑됨.
    """
    try:
        runtime_manager.ensure_process_running(ctx.manifest.id)
        
        conn = ctx.connection
        if not conn:
            raise RuntimeError("Process running but connection lost")

        conn.send(data)

        if conn.poll(10):
            result = conn.recv()
            logger.info(f"[*] Local Inference Result: {str(result)[:100]}...")
            return result
        else:
            logger.error("[*] Local Inference Timeout")
            return {"status": "error", "message": "Inference Timeout (Local Process did not respond)"}
    except Exception as e:
        logger.error(f"[*] IPC Error: {str(e)}")
        raise e

@router.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
    ctx = plugin_loader.get_plugin(plugin_id)
    if not ctx:
        logger.error(f"Plugin not found: {plugin_id}")
        raise HTTPException(status_code=404, detail="Plugin not found")

    payload = await request.json()
    data = payload.get("payload", payload)

    logger.info(f"[*] Inference Request: [{plugin_id}] -> Mode: {ctx.mode}")

    # CASE A: Web Mode (Relay to Cloud)
    if ctx.mode == "web":
        cloud_conf = get_cloud_config()
        base_url = cloud_conf.get('base_url', "http://localhost:8000")
        api_key = cloud_conf.get('system_api_key', "")
        
        target = f"{base_url}/v1/inference/{plugin_id}/{function_name}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        
        logger.info(f"[*] Web Relay Target URL: {target}")

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(target, json=payload, headers=headers, timeout=30.0)
                if resp.status_code != 200:
                    return {"status": "error", "code": resp.status_code, "message": f"Cloud Error: {resp.text}"}
                return resp.json()
            except Exception as e:
                logger.error(f"[*] Web Relay Exception: {str(e)}")
                return {"status": "error", "message": f"Web Relay Failed: {str(e)}"}

    # CASE B: Local Mode
    else:
        try:
            # [보완됨] SOA(Direct) 모드 확인
            exec_type = getattr(ctx.manifest.inference, "execution_type", "process")
            
            if exec_type == "none":
                # AI Engine 직접 호출 (Blocking 함수일 가능성이 높으므로 threadpool 사용 권장)
                logger.info(f"[*] Direct AI Engine Call for {plugin_id}")
                model_id = data.get("model_id", "MODEL_MELON")
                
                # ai_engine.process_request가 동기 함수라면 스레드풀에서 실행
                return await run_in_threadpool(ai_engine.process_request, model_id, data)
            
            else:
                # IPC Process 통신 (기존 로직)
                logger.info(f"[*] Processing Local IPC for {plugin_id}")
                return await run_in_threadpool(_communicate_ipc, ctx, data)

        except Exception as e:
            logger.error(f"[*] Local Inference Failed: {str(e)}")
            return {"status": "error", "message": f"Local Inference Failed: {str(e)}"}