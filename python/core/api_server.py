import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# 로거 설정
logger = logging.getLogger("AiPlugs.API")

# [Global] 현재 실행 중인 API 포트 (Electron 주입 URL 생성용)
CURRENT_API_PORT = 5000 

# -------------------------------------------------------------------------
# [Module Imports]
# -------------------------------------------------------------------------
try:
    from core.plugin_loader import plugin_loader
    from core.connection_manager import router as websocket_router
    from core.inference_router import router as inference_router
    from core.schemas import MatchRequest, MatchResponse
except ImportError as e:
    logger.warning(f"Some core modules could not be imported: {e}")
    plugin_loader = None
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    [Lifespan Event] 앱 시작 및 종료 시 수행할 로직
    """
    # plugin_loader가 정상적으로 임포트되었는지 확인 후 초기화
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

# CORS 설정 (Electron 내부 브라우저 접근 허용)
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
    
    # plugin_loader가 사용 가능한 상태인지 확인
    if plugin_loader is not None:
        for pid, ctx in plugin_loader.plugins.items():
            is_matched = False
            # 미리 컴파일된 정규식 패턴 활용
            for pattern in ctx.compiled_patterns:
                if pattern.match(req.url):
                    is_matched = True
                    break
            
            if is_matched:
                for script_block in ctx.manifest.content_scripts:
                    # Electron Native 주입은 타이밍 문제로 document_end가 가장 안정적입니다.
                    for js_file in script_block.js:
                        # 로컬 서버 URL로 변환하여 반환
                        full_url = f"http://localhost:{CURRENT_API_PORT}/plugins/{pid}/{js_file}"
                        matched_scripts.append(full_url)

    return MatchResponse(scripts=matched_scripts)

# -------------------------------------------------------------------------
# [Smart Plugin Serving] - Auto Sandboxing
# -------------------------------------------------------------------------
@app.get("/plugins/{plugin_id}/{file_path:path}")
async def serve_plugin_file(plugin_id: str, file_path: str):
    """
    플러그인 파일을 서빙하되, JS 파일은 IIFE(즉시실행함수)로 감싸서 격리합니다.
    """
    if plugin_loader is None:
        raise HTTPException(status_code=503, detail="Plugin Loader not ready")

    base_dir = os.path.abspath(plugin_loader.plugins_dir)
    # file_path 앞의 슬래시를 제거하여 os.path.join이 절대경로로 오인하는 것을 방지
    safe_relative_path = file_path.lstrip("/\\")
    target_file = os.path.abspath(os.path.join(base_dir, plugin_id, safe_relative_path))
    
    # [Security] Path Traversal 방지
    if not target_file.startswith(base_dir):
        logger.warning(f"Blocked Path Traversal attempt: {target_file}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(target_file) or not os.path.isfile(target_file):
        raise HTTPException(status_code=404, detail="File not found")

    # [Core Logic] JS 자동 격리 (Auto-Wrapping)
    if target_file.lower().endswith(".js"):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 디버깅을 위한 가상 소스 경로 설정
            virtual_filename = f"aiplugs://{plugin_id}/{safe_relative_path}"
            
            # IIFE로 감싸서 전역 스코프 오염 방지 및 sourceURL 추가
            wrapped_content = f"""/* [AiPlugs] Scope Isolated & Managed by Core */
(function() {{
{content}
}})();
//# sourceURL={virtual_filename}
"""
            return Response(content=wrapped_content, media_type="application/javascript")
            
        except Exception as e:
            logger.error(f"Error wrapping JS file ({target_file}): {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    # 그 외 파일 (HTML, CSS, 이미지 등)
    return FileResponse(target_file)

# 라우터 등록
if 'websocket_router' in locals() and websocket_router:
    app.include_router(websocket_router)
if 'inference_router' in locals() and inference_router:
    app.include_router(inference_router)

def run_api_server(port: int):
    """Orchestrator에 의해 실행되는 진입점"""
    global CURRENT_API_PORT
    CURRENT_API_PORT = port
    
    logger.info(f"Starting Uvicorn Server on 127.0.0.1:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info", access_log=False)