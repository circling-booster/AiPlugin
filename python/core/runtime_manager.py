import logging
import os
from core.worker_manager import WorkerManager
from core.plugin_loader import plugin_loader
from core.connection_manager import connection_manager

logger = logging.getLogger("RuntimeManager")

class RuntimeManager:
    def ensure_process_running(self, plugin_id: str):
        ctx = plugin_loader.get_plugin(plugin_id)
        if not ctx:
            raise ValueError(f"Plugin {plugin_id} not found")

        # Check existing
        if connection_manager.check_connection(ctx):
            return

        # Setup
        exec_type = getattr(ctx.manifest.inference, "execution_type", "process")
        entry_file = ctx.manifest.inference.local_entry
        entry_path = os.path.join(ctx.path, entry_file)
        
        # Spawn
        process, conn = WorkerManager.spawn_worker(
            plugin_id, 
            entry_path, 
            env_vars={}, 
            execution_type=exec_type
        )
        
        if process:
            ctx.process = process
            ctx.connection = conn
            if exec_type == "none":
                ctx.mode = "soa"
            else:
                ctx.mode = "local"
            logger.info(f"Runtime ready for {plugin_id} (Mode: {ctx.mode})")
        else:
            raise RuntimeError(f"Failed to start runtime for {plugin_id}")

runtime_manager = RuntimeManager()