import logging
import os
from typing import Optional, Dict
import multiprocessing
from core.worker_manager import WorkerManager
from core.plugin_loader import plugin_loader, PluginContext

class RuntimeManager:
    """
    [New Module] 플러그인 프로세스의 생명주기(Spawn, Kill)를 전담 관리
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RuntimeManager, cls).__new__(cls)
            cls._instance.logger = logging.getLogger("AiPlugs.Runtime")
        return cls._instance

    def ensure_process_running(self, plugin_id: str) -> Dict:
        """
        Lazy Loading 구현체: 요청 시점에 프로세스가 없으면 생성
        """
        ctx: PluginContext = plugin_loader.get_plugin(plugin_id)
        if not ctx:
            raise ValueError(f"Plugin {plugin_id} not found in loader")

        # Web Mode: 로컬 프로세스 불필요
        if ctx.mode == "web":
            if ctx.process and ctx.process.is_alive():
                self.logger.warning(f"[{plugin_id}] Terminating local process (switched to Web Mode)")
                ctx.process.terminate()
            return {"status": "ready", "mode": "web"}

        # Local Mode: 프로세스 확인 및 생성
        if ctx.process is None or not ctx.process.is_alive():
            self.logger.info(f"[{plugin_id}] 🐢 Lazy Loading: Spawning Worker...")
            
            entry = ctx.manifest.inference.local_entry
            full_path = os.path.join(ctx.base_path, entry)
            
            # WorkerManager를 통해 안전하게 프로세스 생성
            process, queue = WorkerManager.spawn_worker(ctx.manifest.id, full_path)
            
            if process:
                ctx.process = process
                ctx.ipc_queue = queue
                self.logger.info(f"[{plugin_id}] Worker spawned (PID: {process.pid})")
            else:
                self.logger.error(f"Failed to spawn worker for {plugin_id}")
                raise RuntimeError(f"Worker spawn failed for {plugin_id}")
        
        return {
            "status": "ready",
            "mode": "local",
            "pid": ctx.process.pid
        }

# 전역 인스턴스 (API Server 등에서 사용)
runtime_manager = RuntimeManager()