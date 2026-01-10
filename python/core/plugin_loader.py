import os
import json
import logging
import re
import fnmatch
from typing import Dict, Optional, List
import multiprocessing
from pydantic import ValidationError

# [Refactor] 분리된 모듈 임포트
from core.schemas import PluginManifest
from core.worker_manager import WorkerManager

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("AiPlugs.Loader")

class PluginContext:
    """
    플러그인의 메타데이터와 런타임 상태(프로세스 등)를 함께 보관하는 컨테이너
    """
    def __init__(self, manifest: PluginManifest, base_path: str, active_mode: str):
        self.manifest = manifest
        self.base_path = base_path
        self.mode = active_mode  # 'local' or 'web'
        self.process: Optional[multiprocessing.Process] = None
        self.ipc_queue: Optional[multiprocessing.Queue] = None
        
        # [Optimization] URL 매칭 패턴 미리 컴파일 (Proxy 속도 향상용)
        self.compiled_patterns = []
        for script in manifest.content_scripts:
            for glob_pat in script.matches:
                if glob_pat == "<all_urls>":
                    self.compiled_patterns.append(re.compile(r".*"))
                else:
                    regex = fnmatch.translate(glob_pat)
                    self.compiled_patterns.append(re.compile(regex, re.IGNORECASE))

class PluginLoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginLoader, cls).__new__(cls)
            cls._instance.plugins: Dict[str, PluginContext] = {}
            # 플러그인 디렉토리 경로 계산
            cls._instance.plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../plugins"))
        return cls._instance

    def load_plugins(self, user_settings: dict = None):
        """plugins 폴더를 스캔하여 메타데이터 로드"""
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
                    
                    # [Refactor] 외부 스키마 모듈을 통한 검증
                    manifest = PluginManifest(**data)

                    # Requirements Check
                    if "python" in manifest.requirements:
                        logger.info(f"[{manifest.id}] Python Req: {manifest.requirements['python']}")

                    # Mode Decision
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
            
            # [Refactor] WorkerManager에 위임
            entry = ctx.manifest.inference.local_entry
            full_path = os.path.join(ctx.base_path, entry)
            
            process, queue = WorkerManager.spawn_worker(ctx.manifest.id, full_path)
            
            if process:
                ctx.process = process
                ctx.ipc_queue = queue
            else:
                logger.error(f"Failed to spawn worker for {plugin_id}")

# Singleton Instance
plugin_loader = PluginLoader()