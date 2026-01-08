import os
import multiprocessing
import importlib.util
import logging
import sys

logger = logging.getLogger("PluginLoader")

class PluginWorker(multiprocessing.Process):
    def __init__(self, plugin_id, path, queue):
        super().__init__()
        self.plugin_id = plugin_id
        self.plugin_path = path
        self.queue = queue
        self.daemon = True

    def run(self):
        """격리된 프로세스 환경"""
        try:
            sys.path.append(os.path.dirname(self.plugin_path))
            os.environ['PLUGIN_ID'] = self.plugin_id
            
            # Backend 동적 로딩
            spec = importlib.util.spec_from_file_location("backend", self.plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            logger.info(f"[{self.plugin_id}] Worker Started PID:{os.getpid()}")
            
            while True:
                msg = self.queue.get()
                if msg['type'] == 'EXECUTE' and hasattr(module, 'run'):
                    result = module.run(msg['payload'])
                    # 결과 처리 로직 (여기선 생략)
                    logger.info(f"[{self.plugin_id}] Output: {result}")
                    
        except Exception as e:
            logger.error(f"[{self.plugin_id}] Crash: {e}")

class PluginManager:
    def __init__(self):
        self.plugins_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'plugins')
        self.plugins = {}

    def load_plugins(self):
        if not os.path.exists(self.plugins_dir): return
        
        for pid in os.listdir(self.plugins_dir):
            path = os.path.join(self.plugins_dir, pid, 'backend.py')
            if os.path.exists(path):
                q = multiprocessing.Queue()
                w = PluginWorker(pid, path, q)
                w.start()
                self.plugins[pid] = {'worker': w, 'queue': q}
    
    def dispatch(self, pid, payload):
        if pid in self.plugins:
            self.plugins[pid]['queue'].put({'type': 'EXECUTE', 'payload': payload})
            
    def shutdown(self):
        for p in self.plugins.values():
            p['worker'].terminate()