import os
import sys
import importlib.util
from fastapi import FastAPI, Depends, Header, HTTPException

app = FastAPI()

PLUGINS_DIR = os.path.join(os.path.dirname(__file__), '..', 'plugins')

async def verify_key(authorization: str = Header(None)):
    if authorization != "Bearer sk-system-secure-key-12345":
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
    uvicorn.run(app, host="0.0.0.0", port=8000)