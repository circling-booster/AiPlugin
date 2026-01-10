import os
import sys
import time
import multiprocessing
import importlib.util
import logging

logger = logging.getLogger("AiPlugs.Worker")

def _worker_entry(p_id: str, path: str, queue: multiprocessing.Queue, env_vars: dict):
    """
    Worker Process Entry Point
    """
    # [Injection] 부모가 전달한 모델 경로 등을 환경변수로 설정
    if env_vars:
        for k, v in env_vars.items():
            os.environ[k] = v

    sys.path.append(os.path.dirname(path))
    
    try:
        spec = importlib.util.spec_from_file_location("backend", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {path}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        logger.info(f"[{p_id}] Worker Process Started (PID: {os.getpid()})")

        while True:
            # 실제 구현에서는 queue.get()을 통해 메인 프로세스의 요청을 처리
            time.sleep(1)
            
    except Exception as e:
        print(f"[{p_id}] Worker Crash: {e}", file=sys.stderr)

class WorkerManager:
    @staticmethod
    def spawn_worker(plugin_id: str, entry_path: str, env_vars: dict = {}):
        if not os.path.exists(entry_path):
            logger.error(f"Entry file missing: {entry_path}")
            return None, None

        ipc_queue = multiprocessing.Queue()
        
        # [Modified] env_vars 전달
        p = multiprocessing.Process(
            target=_worker_entry,
            args=(plugin_id, entry_path, ipc_queue, env_vars),
            daemon=True
        )
        p.start()
        return p, ipc_queue