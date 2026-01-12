import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# 로거 설정
logger = logging.getLogger("AiPlugs.API")

# [Global] 현재 실행 중인 API 포트
CURRENT_API_PORT = 5000 

# -------------------------------------------------------------------------
# [Module Imports]
# -------------------------------------------------------------------------
try:
    from core.plugin_loader import plugin_loader
    from core.connection_manager import router as websocket_router
    from core.inference_router import router as inference_router
    # [수정] ScriptInjection 명시적 임포트 (타입 안전성 확보)
    from core.schemas import MatchRequest, MatchResponse, ScriptInjection
except ImportError as e:
    logger.warning(f"Some core modules could not be imported: {e}")
    plugin_loader = None
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    if plugin_loader is not None:
        if not plugin_loader.plugins:
            logger.info("Initializing Plugin Loader during startup...")
            plugin_loader.load_plugins()
        else:
            logger.info("Plugins already loaded.")
    else:
        logger.warning("Plugin Loader is not available. Skipping plugin loading.")
    
    yield
    logger.info("API Server shutting down...")

app = FastAPI(lifespan=lifespan, title="AiPlugs Local Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# [New] Dual-Pipeline Matching Endpoint
# -------------------------------------------------------------------------
@app.post("/v1/match", response_model=MatchResponse)
async def match_plugins(req: MatchRequest):
    """
    Electron이 현재 URL에 필요한 스크립트 목록을 질의하는 엔드포인트
    """
    matched_scripts = []
    
    if plugin_loader is not None:
        for pid, ctx in plugin_loader.plugins.items():
            is_matched = False
            for pattern in ctx.compiled_patterns:
                if pattern.match(req.url):
                    is_matched = True
                    break
            
            if is_matched:
                for script_block in ctx.manifest.content_scripts:
                    current_run_at = script_block.run_at
                    for js_file in script_block.js:
                        full_url = f"http://localhost:{CURRENT_API_PORT}/plugins/{pid}/{js_file}"
                        # [수정] Pydantic 모델 객체로 생성하여 타입 안전성 확보
                        matched_scripts.append(ScriptInjection(
                            url=full_url,
                            run_at=current_run_at
                        ))

    return MatchResponse(scripts=matched_scripts)

# -------------------------------------------------------------------------
# [Smart Plugin Serving] - Auto Sandboxing
# -------------------------------------------------------------------------
@app.get("/plugins/{plugin_id}/{file_path:path}")
async def serve_plugin_file(plugin_id: str, file_path: str):
    if plugin_loader is None:
        raise HTTPException(status_code=503, detail="Plugin Loader not ready")

    base_dir = os.path.abspath(plugin_loader.plugins_dir)
    safe_relative_path = file_path.lstrip("/\\")
    target_file = os.path.abspath(os.path.join(base_dir, plugin_id, safe_relative_path))
    
    if not target_file.startswith(base_dir):
        logger.warning(f"Blocked Path Traversal attempt: {target_file}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(target_file) or not os.path.isfile(target_file):
        raise HTTPException(status_code=404, detail="File not found")

    if target_file.lower().endswith(".js"):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            virtual_filename = f"aiplugs://{plugin_id}/{safe_relative_path}"
            
            wrapped_content = f"""/* [AiPlugs] Scope Isolated & Managed by Core */
(function() {{{content}
}})();
//# sourceURL={virtual_filename}
"""
            return Response(content=wrapped_content, media_type="application/javascript")
            
        except Exception as e:
            logger.error(f"Error wrapping JS file ({target_file}): {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    return FileResponse(target_file)

if 'websocket_router' in locals() and websocket_router:
    app.include_router(websocket_router)

if 'inference_router' in locals() and inference_router:
    app.include_router(inference_router)

def run_api_server(port: int):
    global CURRENT_API_PORT
    CURRENT_API_PORT = port
    
    logger.info(f"Starting Uvicorn Server on 127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", access_log=False)