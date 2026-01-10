import uvicorn
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware  # [1] CORS 미들웨어 추가
from core.plugin_loader import plugin_loader

# 분리된 모듈에서 라우터 임포트
from core.connection_manager import router as websocket_router
from core.inference_router import router as inference_router

app = FastAPI()

# [2] CORS 설정 (필수)
# 브라우저(Mitmproxy 주입 스크립트)가 Localhost API(5000번)를 호출할 수 있도록 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 오리진 허용 (보안상 필요시 구체적 도메인 지정 가능)
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, OPTIONS 등 모든 메소드 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# 서버 시작 시 플러그인 메타데이터 로드
plugin_loader.load_plugins()

# 정적 파일 경로 마운트
if os.path.isdir(plugin_loader.plugins_dir):
    app.mount("/plugins", StaticFiles(directory=plugin_loader.plugins_dir), name="plugins")
else:
    print(f"[API] Warning: Plugins directory not found at {plugin_loader.plugins_dir}")

# [Refactor] 분리된 라우터 등록
app.include_router(websocket_router)
app.include_router(inference_router)

def run_api_server(port: int):
    """
    Main Process에서 Thread로 실행되는 함수
    """
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")