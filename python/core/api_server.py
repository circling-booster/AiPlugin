import sys
import os
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# [중요] 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import plugin_loader
from core.schemas import MatchResponse, MatchRequest, ScriptInjection
from core.matcher import UrlMatcher 
# [변경] 라우터 임포트
from core.inference_router import router as inference_router

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("APIServer")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AI Engine API...")
    try:
        plugin_loader.load_plugins()
    except Exception as e:
        logger.error(f"Plugin Load Error: {e}")
    yield
    # Shutdown
    logger.info("Shutting down AI Engine API...")

app = FastAPI(title="AI Engine API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------------------
# [Static Files Mounting] - (복구됨: 이것이 없으면 UI/스크립트 로딩 불가)
# ------------------------------------------------------------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
plugins_dir = os.path.abspath(os.path.join(current_dir, "../../plugins"))

if os.path.exists(plugins_dir):
    app.mount("/plugins", StaticFiles(directory=plugins_dir), name="plugins")
    logger.info(f"Serving plugins from: {plugins_dir}")
else:
    logger.warning(f"Plugins directory not found at: {plugins_dir}")

# ------------------------------------------------------------------------------
# [Router Registration] - (수정됨: 기존 인라인 함수 제거 후 라우터 등록)
# ------------------------------------------------------------------------------
app.include_router(inference_router)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai_engine"}

# ------------------------------------------------------------------------------
# [Unified Match Logic] - (복구됨: 이것이 없으면 스크립트 주입 불가)
# ------------------------------------------------------------------------------
@app.post("/v1/match", response_model=MatchResponse)
async def match_endpoint(request: MatchRequest):
    """
    Returns scripts to inject based on URL, using the robust UrlMatcher.
    """
    try:
        url = request.url
        scripts = []
        
        plugins = plugin_loader.plugins
        
        for pid, ctx in plugins.items():
            for script in ctx.manifest.content_scripts:
                is_match = False
                for pattern in script.matches:
                    if UrlMatcher.match(pattern, url):
                        is_match = True
                        break
                
                if is_match:
                    for js in script.js:
                        scripts.append(ScriptInjection(
                            url=f"plugins/{pid}/{js}",
                            run_at=script.run_at
                        ))
        return MatchResponse(scripts=scripts)
    except Exception as e:
        logger.error(f"Match Error: {e}")
        return MatchResponse(scripts=[])

def run_api_server(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    
    port = args.port if args.port > 0 else 8000
    run_api_server(port)