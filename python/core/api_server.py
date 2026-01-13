import sys
import os
import argparse
import uvicorn
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_engine import ai_engine
from core.schemas import MatchResponse, MatchRequest, ScriptInjection
from core.plugin_loader import plugin_loader
from core.runtime_manager import runtime_manager

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

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "ai_engine"}

# ------------------------------------------------------------------------------
# [Legacy Match Logic]
# ------------------------------------------------------------------------------
@app.post("/v1/match", response_model=MatchResponse)
async def match_endpoint(request: MatchRequest):
    """
    Returns scripts to inject based on URL.
    """
    try:
        url = request.url
        scripts = []
        
        plugins = plugin_loader.plugins
        
        for pid, ctx in plugins.items():
            for script in ctx.manifest.content_scripts:
                # Basic Wildcard Match
                is_match = False
                for pattern in script.matches:
                    if pattern == "<all_urls>" or pattern in url:
                        is_match = True
                        break
                
                if is_match:
                    for js in script.js:
                        scripts.append(ScriptInjection(
                            url=f"plugins/{pid}/{js}", # Conceptual path
                            run_at=script.run_at
                        ))
        return MatchResponse(scripts=scripts)
    except Exception as e:
        logger.error(f"Match Error: {e}")
        return MatchResponse(scripts=[])

# ------------------------------------------------------------------------------
# [Unified Inference Endpoint]
# ------------------------------------------------------------------------------
@app.post("/v1/inference/{plugin_id}/{function_name}")
async def inference_endpoint(plugin_id: str, function_name: str, request: Request):
    """
    Handles both SOA (Direct AI Engine) and Legacy (Process IPC) requests.
    """
    try:
        payload = await request.json()
        data = payload.get("payload", payload)
        
        ctx = plugin_loader.get_plugin(plugin_id)
        if not ctx:
            raise HTTPException(status_code=404, detail="Plugin not found")

        # Determine Execution Type
        exec_type = getattr(ctx.manifest.inference, "execution_type", "process")
        
        # [SOA Mode] Direct Call to AI Engine
        if exec_type == "none":
            model_id = data.get("model_id", "MODEL_MELON")
            return ai_engine.process_request(model_id, data)
            
        # [Legacy Process Mode] IPC Relay
        else:
            runtime_manager.ensure_process_running(plugin_id)
            conn = ctx.connection
            if not conn:
                raise RuntimeError("Process connection lost")
            
            conn.send(data)
            if conn.poll(10):
                return conn.recv()
            else:
                return {"status": "error", "message": "Timeout from plugin process"}

    except Exception as e:
        logger.error(f"Inference Error: {e}")
        return {"status": "error", "message": str(e)}

def run_api_server(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port)

# ------------------------------------------------------------------------------
# [Process Entry Point]
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    
    port = args.port if args.port > 0 else 8000
    run_api_server(port)