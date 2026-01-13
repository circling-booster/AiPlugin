import os
import sys
import multiprocessing
import importlib.util
import logging
import traceback
import io

logger = logging.getLogger("AiPlugs.Worker")

# [SOA Support]
class DummyProcess:
    def __init__(self):
        self.pid = 99999
        self.stdin = io.BytesIO()
        self.stdout = io.BytesIO()
        self.returncode = None
        self._alive = True
    
    def poll(self):
        return None if self._alive else 0
    
    def terminate(self):
        self._alive = False
        
    def kill(self):
        self._alive = False
        
    def is_alive(self):
        return self._alive

def _worker_entry(p_id, path, conn, env_vars):
    # (Legacy Worker Logic preserved)
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
        logger.info(f"[{p_id}] Worker Started (PID: {os.getpid()})")
    except Exception as e:
        conn.send({"status": "error", "message": str(e)})
        return

    while True:
        try:
            if conn.poll(1):
                payload = conn.recv()
                if payload == "STOP":
                    break
                if hasattr(backend_module, "run"):
                    conn.send(backend_module.run(payload))
                else:
                    conn.send({"status": "error", "message": "No run method"})
        except Exception:
            break

class WorkerManager:
    @staticmethod
    def spawn_worker(plugin_id: str, entry_path: str, env_vars: dict = {}, execution_type: str = "process"):
        # [SOA Migration]
        if execution_type == "none":
            logger.info(f"[{plugin_id}] Initialized as Client (SOA Mode)")
            return DummyProcess(), None

        if not os.path.exists(entry_path):
            logger.error(f"Entry missing: {entry_path}")
            return None, None

        parent_conn, child_conn = multiprocessing.Pipe()
        p = multiprocessing.Process(
            target=_worker_entry,
            args=(plugin_id, entry_path, child_conn, env_vars),
            daemon=True
        )
        p.start()
        return p, parent_conn