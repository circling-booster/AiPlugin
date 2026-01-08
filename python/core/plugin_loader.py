import os
import json
import logging
import multiprocessing
import importlib.util
import re
import fnmatch
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ValidationError

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("AiPlugs.Loader")

# --- Manifest V3 Schema Definition (Pydantic) ---
class InferenceConfig(BaseModel):
    supported_modes: List[str] = Field(default=["local"])
    default_mode: str = Field(default="local")
    local_entry: str = "backend.py"
    web_entry: str = "web_backend.py"

class ContentScript(BaseModel):
    matches: List[str] = ["<all_urls>"]
    js: List[str] = ["content.js"]
    run_at: str = "document_end"

class PluginManifest(BaseModel):
    manifest_version: int = Field(default=3, description="Must be version 3")
    id: str
    name: str = "Unknown Plugin"
    requirements: Dict[str, List[str]] = Field(default_factory=dict)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    host_permissions: List[str] = Field(default_factory=list)
    content_scripts: List[ContentScript] = Field(default_factory=list)

class PluginContext:
    def __init__(self, manifest: PluginManifest, base_path: str, active_mode: str):
        self.manifest = manifest
        self.base_path = base_path
        self.mode = active_mode  # 'local' or 'web'
        self.process: Optional[multiprocessing.Process] = None
        self.ipc_queue: Optional[multiprocessing.Queue] = None
        
        # [Optimization] Pre-compile Match Patterns for Proxy usage
        self.compiled_patterns = []
        for script in manifest.content_scripts:
            for glob_pat in script.matches:
                if glob_pat == "<all_urls>":
                    self.compiled_patterns.append(re.compile(r".*"))
                else:
                    # fnmatch style glob -> regex
                    regex = fnmatch.translate(glob_pat)
                    self.compiled_patterns.append(re.compile(regex, re.IGNORECASE))

class PluginLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginLoader, cls).__new__(cls)
            cls._instance.plugins: Dict[str, PluginContext] = {}
            # 플러그인 디렉토리 (프로젝트 구조에 맞게 조정)
            cls._instance.plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../plugins"))
        return cls._instance

    def load_plugins(self, user_settings: dict = None):
        """plugins 폴더를 스캔하여 메타데이터만 메모리에 로드 (프로세스 실행 X)"""
        if not user_settings:
            user_settings = {}

        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
            return

        for folder in os.listdir(self.plugins_dir):
            p_path = os.path.join(self.plugins_dir, folder)
            m_path = os.path.join(p_path, "manifest.json")
            
            if os.path.exists(m_path):
                try:
                    with open(m_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # [Task 1] Validation
                    manifest = PluginManifest(**data)

                    # [Optimization] Requirements Check
                    if "python" in manifest.requirements:
                        logger.info(f"[{manifest.id}] Requirements: {manifest.requirements['python']}")

                    # Mode Decision: Settings > Manifest Default
                    pref_mode = user_settings.get("plugin_modes", {}).get(manifest.id)
                    final_mode = pref_mode if pref_mode in manifest.inference.supported_modes else manifest.inference.default_mode

                    self.plugins[manifest.id] = PluginContext(manifest, p_path, final_mode)
                    logger.info(f"Loaded Metadata: {manifest.id} (Mode: {final_mode})")

                except ValidationError as e:
                    logger.error(f"Manifest Invalid {folder}: {e}")
                except Exception as e:
                    logger.error(f"Load Error {folder}: {e}")

    def get_plugin(self, plugin_id: str) -> Optional[PluginContext]:
        return self.plugins.get(plugin_id)

    # [Task 3] Lazy Loading & Process Management
    def ensure_process_running(self, plugin_id: str):
        ctx = self.get_plugin(plugin_id)
        if not ctx:
            raise ValueError(f"Plugin {plugin_id} not found")

        # Web Mode: 로컬 리소스 사용 금지
        if ctx.mode == "web":
            if ctx.process and ctx.process.is_alive():
                logger.warning(f"[{plugin_id}] Terminating local process (Web Mode)")
                ctx.process.terminate()
            return

        # Local Mode: 프로세스가 없으면 스폰 (Lazy Load)
        if ctx.process is None or not ctx.process.is_alive():
            logger.info(f"[{plugin_id}] 🐢 Lazy Loading: Spawning Worker...")
            self._spawn_worker(ctx)

    def _spawn_worker(self, ctx: PluginContext):
        try:
            entry = ctx.manifest.inference.local_entry
            path = os.path.join(ctx.base_path, entry)
            
            if not os.path.exists(path):
                logger.error(f"Entry file missing: {path}")
                return

            ctx.ipc_queue = multiprocessing.Queue()
            
            # [Optimization] Daemon Process: 부모 종료 시 자동 정리
            p = multiprocessing.Process(
                target=self._worker_entry,
                args=(ctx.manifest.id, path, ctx.ipc_queue),
                daemon=True
            )
            p.start()
            ctx.process = p
        except Exception as e:
            logger.error(f"Spawn Failed: {e}")

    @staticmethod
    def _worker_entry(p_id, path, queue):
        """Worker Process Entry Point"""
        import sys
        # 모듈 임포트를 위해 경로 추가
        sys.path.append(os.path.dirname(path))
        
        try:
            spec = importlib.util.spec_from_file_location("backend", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # [Simulation] Keep-alive for Lazy Loading Test
            import time
            while True:
                time.sleep(1)
                # Real implementation: handle queue items
        except Exception as e:
            print(f"[{p_id}] Worker Crash: {e}")

# Singleton
plugin_loader = PluginLoader()