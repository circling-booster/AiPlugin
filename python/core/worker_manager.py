import os
import sys
import time
import multiprocessing
import importlib.util
import logging
import traceback

logger = logging.getLogger("AiPlugs.Worker")

def _worker_entry(p_id: str, path: str, conn: multiprocessing.connection.Connection, env_vars: dict):
    """
    Worker Process Entry Point with IPC
    """
    # [Injection] 부모가 전달한 모델 경로 등을 환경변수로 설정
    if env_vars:
        for k, v in env_vars.items():
            os.environ[k] = v

    sys.path.append(os.path.dirname(path))
    
    backend_module = None
    try:
        spec = importlib.util.spec_from_file_location("backend", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {path}")
            
        backend_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend_module)
        
        logger.info(f"[{p_id}] Worker Process Started (PID: {os.getpid()})")

    except Exception as e:
        logger.error(f"[{p_id}] Init Failed: {e}")
        # 초기화 실패 시에도 에러 전송을 위해 대기하거나 종료
        conn.send({"status": "error", "message": f"Init Failed: {str(e)}"})
        return

    # [Main Loop] 요청 대기 및 처리
    while True:
        try:
            # Blocking Call (데이터가 올 때까지 대기)
            if conn.poll(timeout=1):
                payload = conn.recv()
                
                # 종료 신호 처리
                if payload == "STOP":
                    break
                
                # 실제 로직 수행
                if hasattr(backend_module, "run"):
                    result = backend_module.run(payload)
                    conn.send(result)
                else:
                    conn.send({"status": "error", "message": "Backend has no 'run' function"})
            
        except EOFError:
            break
        except Exception as e:
            err_msg = f"Runtime Error: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[{p_id}] {err_msg}")
            try:
                conn.send({"status": "error", "message": str(e)})
            except:
                pass

class WorkerManager:
    @staticmethod
    def spawn_worker(plugin_id: str, entry_path: str, env_vars: dict = {}):
        if not os.path.exists(entry_path):
            logger.error(f"Entry file missing: {entry_path}")
            return None, None

        # [Modified] Use Pipe instead of Queue for Request/Response
        parent_conn, child_conn = multiprocessing.Pipe()
        
        p = multiprocessing.Process(
            target=_worker_entry,
            args=(plugin_id, entry_path, child_conn, env_vars),
            daemon=True
        )
        p.start()
        
        # 부모 프로세스는 parent_conn을 통해 자식과 대화
        return p, parent_conn