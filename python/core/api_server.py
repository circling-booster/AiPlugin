# python/core/api_server.py

import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Core Modules
from core.plugin_loader import plugin_loader
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

# 정적 파일 경로 마운트 (Plugins Assets)
# 플러그인 별 프론트엔드 파일(js, html 등)을 서빙합니다.
plugins_path = plugin_loader.plugins_dir
if os.path.exists(plugins_path) and os.path.isdir(plugins_path):
    app.mount("/plugins", StaticFiles(directory=plugins_path), name="plugins")
    logger.info(f"Mounted static files at '/plugins' from {plugins_path}")
else:
    logger.warning(f"Plugins directory not found: {plugins_path}")

# 라우터 등록
app.include_router(websocket_router)
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
        # access_log=False로 설정하면 API 요청 로그(GET /...)가 콘솔에 남지 않아 깔끔합니다.
        # 디버깅이 필요하면 True로 변경하십시오.
        access_log=False 
    )