import os
import sys
import importlib.util
import argparse
from fastapi import FastAPI, Depends, Header, HTTPException
from dotenv import load_dotenv

# .env 로드 (현 위치 혹은 상위 디렉토리)
load_dotenv()

app = FastAPI()

PLUGINS_DIR = os.path.join(os.path.dirname(__file__), '..', 'plugins')
SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY", "sk-default-key-if-not-set")

async def verify_key(authorization: str = Header(None)):
    # [Fixed] Secure comparison with Environment Variable
    expected = f"Bearer {SYSTEM_API_KEY}"
    if authorization != expected:
        raise HTTPException(403, "Invalid API Key")

def load_routers():
    if not os.path.exists(PLUGINS_DIR): return
    for pid in os.listdir(PLUGINS_DIR):
        path = os.path.join(PLUGINS_DIR, pid, 'web_backend.py')
        if os.path.exists(path):
            try:
                spec = importlib.util.spec_from_file_location(f"plugins.{pid}.web", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, 'router'):
                    app.include_router(mod.router, prefix=f"/v1/inference/{pid}", dependencies=[Depends(verify_key)])
                    print(f"[Cloud] Loaded: {pid}")
            except Exception as e:
                print(f"[Cloud] Error {pid}: {e}")

load_routers()

if __name__ == "__main__":
    import uvicorn
    
    # [Fixed] Parse Port Argument for Dynamic Allocation
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"[Cloud] Starting Simulation on port {args.port}...")
    uvicorn.run(app, host="0.0.0.0", port=args.port)