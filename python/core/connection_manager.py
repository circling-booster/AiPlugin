import socket
import logging

logger = logging.getLogger("ConnectionManager")

class ConnectionManager:
    @staticmethod
    def check_connection(plugin_context):
        """
        Verifies connectivity.
        """
        try:
            # [SOA Logic] Skip check if execution_type is 'none'
            if hasattr(plugin_context, "manifest") and plugin_context.manifest.inference:
                if plugin_context.manifest.inference.execution_type == "none":
                    return True
            
            # [Legacy Logic] Check TCP/Process
            if hasattr(plugin_context, "process") and plugin_context.process:
                 if plugin_context.process.is_alive():
                     return True
                     
            return False
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False

connection_manager = ConnectionManager()