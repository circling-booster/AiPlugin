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
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, required=True)
    # [Checklist] 호출 규약: proxy-port는 optional이며 기본값 None
    parser.add_argument("--proxy-port", type=int, required=False, default=None)
    parser.add_argument("--no-proxy", action="store_true")
    args = parser.parse_args()

    # 프록시 사용 여부 결정
    use_proxy = not args.no_proxy and args.proxy_port is not None and args.proxy_port > 0

    orchestrator = SystemOrchestrator(
        api_port=args.api_port, 
        proxy_port=args.proxy_port if use_proxy else None
    )

    try:
        # [Fail-Safe] 시작 시 무조건 시스템 프록시 정리 (레지스트리 오염 방지)
        orchestrator.force_clear_system_proxy()

        orchestrator.start_api_server()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        if use_proxy:
            logger.info(f"System Mode: Dual-Pipeline (Proxy Active on {args.proxy_port})")
            orchestrator.enable_system_proxy()
            loop.run_until_complete(orchestrator.run_mitmproxy())
        else:
            logger.info("System Mode: Native-Only (Proxy Disabled)")
            loop.run_forever()

    except KeyboardInterrupt:
        logger.info("User interrupted.")
    except Exception as e:
        logger.error(f"Critical Error: {e}")
    finally:
        orchestrator.shutdown()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()