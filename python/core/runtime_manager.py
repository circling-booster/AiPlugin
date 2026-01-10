import logging
import os
import hashlib
import shutil
import requests
from typing import Optional, Dict
from core.worker_manager import WorkerManager
from core.plugin_loader import plugin_loader, PluginContext

class RuntimeManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RuntimeManager, cls).__new__(cls)
            cls._instance.logger = logging.getLogger("AiPlugs.Runtime")
            
            # [Path Resolution] python/core/runtime_manager.py 기준 상위/상위/models
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cls._instance.models_dir = os.path.abspath(os.path.join(base_dir, "../../models"))
            
            if not os.path.exists(cls._instance.models_dir):
                os.makedirs(cls._instance.models_dir)
                cls._instance.logger.info(f"Created models directory at: {cls._instance.models_dir}")
                
        return cls._instance

    def _download_file(self, url: str, dest_path: str, expected_sha256: Optional[str] = None):
        """[Helper] 파일 다운로드 및 검증 (Atomic Write 적용)"""
        self.logger.info(f"Downloading model from {url}...")
        
        # 임시 파일명 사용 (.part) -> 다운로드 중 프로세스 종료 시 불완전 파일 방지
        temp_path = dest_path + ".part"
        
        try:
            # User-Agent 설정 (일부 호스팅 서버 차단 방지)
            headers = {'User-Agent': 'AiPlugs-Runtime/2.2'}
            
            with requests.get(url, stream=True, headers=headers, timeout=60) as r:
                r.raise_for_status()
                with open(temp_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            self.logger.info("Download complete. Verifying hash...")
            
            # 해시 검증
            if expected_sha256:
                sha256_hash = hashlib.sha256()
                with open(temp_path, "rb") as f:
                    for byte_block in iter(lambda: f.read(4096), b""):
                        sha256_hash.update(byte_block)
                
                calculated = sha256_hash.hexdigest()
                if calculated.lower() != expected_sha256.lower():
                    raise ValueError(f"Hash mismatch! Expected {expected_sha256}, got {calculated}")
                self.logger.info("Hash verification passed.")

            # 안전하게 이름 변경 (Atomic Move)
            shutil.move(temp_path, dest_path)
            self.logger.info(f"Model saved to {dest_path}")

        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path) # 실패 시 임시 파일 삭제
            raise e

    def _prepare_models(self, ctx: PluginContext) -> Dict[str, str]:
        """[Logic] 모델 준비 및 환경변수 딕셔너리 생성"""
        env_vars = {}
        if not ctx.manifest.inference.models:
            return env_vars

        for model_req in ctx.manifest.inference.models:
            file_path = os.path.join(self.models_dir, model_req.filename)
            
            # 파일이 없으면 다운로드 수행
            if not os.path.exists(file_path):
                if model_req.source_url:
                    self.logger.warning(f"Model {model_req.filename} missing. Auto-downloading...")
                    self._download_file(model_req.source_url, file_path, model_req.sha256)
                else:
                    raise FileNotFoundError(f"Model {model_req.filename} not found and no source_url provided.")
            
            # 절대 경로를 환경변수 값으로 매핑
            env_vars[model_req.key] = file_path
            
        return env_vars

    def ensure_process_running(self, plugin_id: str) -> Dict:
        """Lazy Loading 구현체"""
        ctx: PluginContext = plugin_loader.get_plugin(plugin_id)
        if not ctx:
            raise ValueError(f"Plugin {plugin_id} not found")

        # Web Mode (Relay)
        if ctx.mode == "web":
            if ctx.process and ctx.process.is_alive():
                ctx.process.terminate()
            return {"status": "ready", "mode": "web"}

        # Local Mode (Process Spawn)
        if ctx.process is None or not ctx.process.is_alive():
            self.logger.info(f"[{plugin_id}] 🐢 Lazy Loading: Spawning Worker...")
            
            entry = ctx.manifest.inference.local_entry
            full_path = os.path.join(ctx.base_path, entry)
            
            try:
                # [CORE] 모델 프로비저닝 수행 (필요 시 다운로드)
                model_envs = self._prepare_models(ctx)
            except Exception as e:
                self.logger.error(f"[{plugin_id}] Model Provisioning Error: {e}")
                return {"status": "error", "message": f"Model error: {str(e)}"}

            # 환경변수(model_envs)와 함께 워커 실행
            process, queue = WorkerManager.spawn_worker(ctx.manifest.id, full_path, model_envs)
            
            if process:
                ctx.process = process
                ctx.ipc_queue = queue
                self.logger.info(f"[{plugin_id}] Worker spawned (PID: {process.pid})")
            else:
                self.logger.error(f"Failed to spawn worker for {plugin_id}")
                raise RuntimeError("Worker spawn failed")
        
        return {"status": "ready", "mode": "local", "pid": ctx.process.pid}

runtime_manager = RuntimeManager()