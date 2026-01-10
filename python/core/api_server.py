import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# Core Modules
# 상호관계: plugin_loader를 통해 플러그인 디렉토리 경로와 메타데이터에 접근합니다.
from core.plugin_loader import plugin_loader
# 상호관계: WebSocket 및 Inference 로직은 별도 라우터 모듈에서 관리하므로 그대로 import합니다.
from core.connection_manager import router as websocket_router
from core.inference_router import router as inference_router

# 로거 설정
logger = logging.getLogger("AiPlugs.API")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    [Lifespan Event]
    앱 시작 및 종료 시 수행할 로직을 정의합니다.
    """
    # 1. Startup: 플러그인 로드 상태 확인 및 로드
    # Orchestrator 스레드에서 서버가 시작될 때 플러그인을 메모리에 적재합니다.
    if not plugin_loader.plugins:
        logger.info("Initializing Plugin Loader during startup...")
        plugin_loader.load_plugins()
    else:
        logger.info("Plugins already loaded.")
    
    yield
    
    # 2. Shutdown: 서버 종료 시 수행할 정리 작업
    logger.info("API Server shutting down...")

# FastAPI 인스턴스 생성 (Lifespan 적용)
app = FastAPI(lifespan=lifespan, title="AiPlugs Local Core")

# CORS 미들웨어 설정
# 로컬 환경 및 확장 프로그램에서의 접근을 허용합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# [Modified] Smart Plugin Serving Logic
# 기존 StaticFiles 마운트를 대체하여, 스크립트 격리(Sandboxing)와 보안 검사를 수행합니다.
# -------------------------------------------------------------------------

@app.get("/plugins/{plugin_id}/{file_path:path}")
async def serve_plugin_file(plugin_id: str, file_path: str):
    """
    플러그인 리소스를 제공하는 스마트 라우터입니다.
    
    기능:
    1. 보안: Path Traversal 공격 방지 (플러그인 폴더 이탈 방지)
    2. 격리: JS 파일 요청 시 자동으로 IIFE(즉시실행함수)로 감싸 전역 스코프 오염 방지
    3. 디버깅: Source URL 주석을 추가하여 브라우저 개발자 도구에서 원본 파일명 표시 지원
    """
    
    # 1. 기본 경로 확인 (python/core/plugin_loader.py에 정의된 plugins_dir 사용)
    base_dir = os.path.abspath(plugin_loader.plugins_dir)
    
    # 2. 요청된 파일의 절대 경로 구성
    # file_path 앞의 슬래시를 제거하여 os.path.join이 절대경로로 오인하는 것을 방지
    safe_relative_path = file_path.lstrip("/\\")
    target_file = os.path.abspath(os.path.join(base_dir, plugin_id, safe_relative_path))
    
    # 3. [Security] Path Traversal 방어
    # 구성된 경로가 의도한 플러그인 디렉토리 내부에 있는지 확인
    if not target_file.startswith(base_dir):
        logger.warning(f"Blocked Path Traversal attempt: {target_file}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    # 4. 파일 존재 여부 확인
    if not os.path.exists(target_file) or not os.path.isfile(target_file):
        raise HTTPException(status_code=404, detail="File not found")

    # 5. [Core Logic] 자바스크립트 파일 자동 격리 (Auto-Wrapping)
    # 대소문자 무시하고 .js 확장자 체크
    if target_file.lower().endswith(".js"):
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 가상 파일명 생성 (브라우저 디버거용)
            # 예: aiplugs://my-plugin/content.js
            virtual_filename = f"aiplugs://{plugin_id}/{safe_relative_path}"
            
            # IIFE 래핑 및 SourceURL 추가
            # - (function(){ ... })(); : 변수 스코프 격리
            # - //# sourceURL=... : 개발자 도구에서 'dynamic_script.js' 대신 원래 파일명으로 보이게 함
            wrapped_content = f"""/* [AiPlugs] Scope Isolated & Managed by Core */
(function() {{
{content}
}})();
//# sourceURL={virtual_filename}
"""
            # MIME 타입을 명시하여 반환
            return Response(content=wrapped_content, media_type="application/javascript")
            
        except Exception as e:
            logger.error(f"Error wrapping JS file ({target_file}): {e}")
            raise HTTPException(status_code=500, detail="Internal Server Error")

    # 6. 그 외 파일 (HTML, CSS, 이미지 등)
    # 일반적인 파일 서빙 처리 (MIME 타입 자동 감지)
    return FileResponse(target_file)

# -------------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------------
# WebSocket 연결 관리 (ConnectionManager)
app.include_router(websocket_router)
# AI 추론 요청 처리 (InferenceRouter)
app.include_router(inference_router)

def run_api_server(port: int):
    """
    Orchestrator에 의해 별도 스레드에서 실행되는 진입점
    """
    logger.info(f"Starting Uvicorn Server on 127.0.0.1:{port}")
    
    # Uvicorn 실행
    # Orchestrator의 데몬 스레드에서 실행되므로 loop="asyncio" 등을 명시할 필요 없이
    # uvicorn.run이 알아서 처리하도록 둡니다.
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=port, 
        log_level="info",
        # API 요청 로그(GET /...)가 콘솔에 남지 않도록 access_log=False 유지
        access_log=False 
    )