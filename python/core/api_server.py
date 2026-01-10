# python/core/api_server.py (Optional Refactor)

import uvicorn
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.plugin_loader import plugin_loader

# 분리된 모듈에서 라우터 임포트
from core.connection_manager import router as websocket_router
from core.inference_router import router as inference_router

app = FastAPI()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [권장 변경] 모듈 임포트 시점에 로드하는 대신, startup 이벤트나 Orchestrator에 위임
# (기존 코드가 유지되어도 동작에는 문제 없음)
# plugin_loader.load_plugins() 

# 정적 파일 경로 마운트
if os.path.isdir(plugin_loader.plugins_dir):
    app.mount("/plugins", StaticFiles(directory=plugin_loader.plugins_dir), name="plugins")

app.include_router(websocket_router)
app.include_router(inference_router)

def run_api_server(port: int):
    # API 서버 시작 시점에 플러그인이 로드되어 있는지 확인
    if not plugin_loader.plugins:
        plugin_loader.load_plugins()
        
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")