from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from .plugin_loader import PluginManager

app = FastAPI()
plugin_manager = PluginManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 플러그인 리소스 서빙
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")
if os.path.exists(PLUGINS_DIR):
    app.mount("/plugins", StaticFiles(directory=PLUGINS_DIR), name="plugins")

@app.on_event("startup")
def startup():
    plugin_manager.load_plugins()

@app.on_event("shutdown")
def shutdown():
    plugin_manager.shutdown()

@app.post("/v1/execute/{plugin_id}")
async def execute(plugin_id: str, request: Request):
    data = await request.json()
    plugin_manager.dispatch(plugin_id, data)
    return {"status": "dispatched"}

def run_api_server(port):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")