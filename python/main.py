import argparse
import sys
import os
import threading
import asyncio
import logging
import multiprocessing

# Mitmproxy Imports
from mitmproxy.tools.dump import DumpMaster
from mitmproxy import options
from mitmproxy.addons import core

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.api_server import run_api_server
from core.proxy_server import AiPlugsAddon
from utils.system_proxy import SystemProxy

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("Main")

async def start_mitmproxy(proxy_port, api_port):
    """Mitmproxy 비동기 실행 (v10+ 대응)"""
    opts = options.Options(listen_host='127.0.0.1', listen_port=proxy_port)
    # [수정] with_dump -> with_dumper 로 변경
    m = DumpMaster(opts, with_termlog=False, with_dumper=False)
    
    # 플러그인 스크립트 목록 생성
    plugins_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'plugins')
    scripts = []
    if os.path.exists(plugins_dir):
        scripts = [f"http://localhost:{api_port}/plugins/{p}/content.js" 
                   for p in os.listdir(plugins_dir) if os.path.exists(os.path.join(plugins_dir, p, "content.js"))]

    # [수정] Core 애드온은 DumpMaster 초기화 시 자동으로 포함되므로 중복 추가 제거
    # m.addons.add(core.Core()) 
    m.addons.add(AiPlugsAddon(api_port, scripts))
    
    logger.info(f"Mitmproxy listening on {proxy_port}")
    await m.run()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, required=True)
    parser.add_argument("--proxy-port", type=int, required=True)
    args = parser.parse_args()

    # 1. API Server (Thread)
    t = threading.Thread(target=run_api_server, args=(args.api_port,), daemon=True)
    t.start()
    logger.info(f"API Server started on {args.api_port}")

    # 2. System Proxy
    proxy = SystemProxy()
    proxy.set_proxy("127.0.0.1", args.proxy_port)

    # 3. Mitmproxy (Asyncio Loop in Main Thread)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(start_mitmproxy(args.proxy_port, args.api_port))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Critical Error: {e}")
    finally:
        proxy.disable_proxy()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()