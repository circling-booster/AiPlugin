import os
import sys
import time
import multiprocessing
import importlib.util
import logging

logger = logging.getLogger("AiPlugs.Worker")

def _worker_entry(p_id: str, path: str, queue: multiprocessing.Queue):
    """
    Worker Process Entry Point
    이 함수는 별도의 자식 프로세스 메모리 공간에서 실행됩니다.
    """
    # 모듈 임포트를 위해 해당 플러그인 디렉토리를 path에 추가
    sys.path.append(os.path.dirname(path))
    
    try:
        # 동적 모듈 로드 (backend.py)
        spec = importlib.util.spec_from_file_location("backend", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {path}")
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        logger.info(f"[{p_id}] Worker Process Started (PID: {os.getpid()})")

        # [Simulation] Keep-alive loop
        # 실제 구현에서는 queue에서 메시지를 꺼내 처리하는 loop가 들어갑니다.
        while True:
            # 예시: queue.get() 로직 등
            time.sleep(1)
            
    except Exception as e:
        # 자식 프로세스의 에러는 표준 출력/에러로 남겨야 부모가 감지 가능
        print(f"[{p_id}] Worker Crash: {e}", file=sys.stderr)

class WorkerManager:
    """프로세스 생성 및 생명주기 관리를 담당하는 헬퍼 클래스"""
    
    @staticmethod
    def spawn_worker(plugin_id: str, entry_path: str):
        if not os.path.exists(entry_path):
            logger.error(f"Entry file missing: {entry_path}")
            return None, None

        ipc_queue = multiprocessing.Queue()
        
        # [Optimization] Daemon Process: 부모(API Server) 종료 시 함께 종료되도록 설정
        p = multiprocessing.Process(
            target=_worker_entry,
            args=(plugin_id, entry_path, ipc_queue),
            daemon=True
        )
        p.start()
        return p, ipc_queue