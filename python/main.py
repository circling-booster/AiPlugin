import argparse
import sys
import os
import asyncio
import logging
import multiprocessing
from core.orchestrator import SystemOrchestrator

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("Main")

def main():
    # 1. Argument Parsing
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, required=True)
    parser.add_argument("--proxy-port", type=int, required=True)
    args = parser.parse_args()

    # 2. Orchestrator Initialization
    orchestrator = SystemOrchestrator(args.api_port, args.proxy_port)

    try:
        # 3. Start Components
        orchestrator.start_api_server()     # API Thread
        orchestrator.enable_system_proxy()  # System Hook

        # 4. Run Main Loop (Mitmproxy)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(orchestrator.run_mitmproxy())

    except KeyboardInterrupt:
        logger.info("User interrupted.")
    except Exception as e:
        logger.error(f"Critical Error: {e}")
    finally:
        # 5. Safe Shutdown
        orchestrator.shutdown()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()