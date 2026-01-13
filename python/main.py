import argparse
import sys
import os
import asyncio
import logging
import multiprocessing
import socket
import subprocess
import time
import atexit
import requests
import psutil

from core.orchestrator import SystemOrchestrator

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("Main")

API_PROCESS = None

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def kill_process_on_port(port):
    """
    지정된 포트를 점유 중인 모든 프로세스를 찾아 강제 종료합니다.
    """
    killed = False
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    logger.warning(f"Killing zombie process {proc.info['name']} (PID: {proc.info['pid']}) on port {port}")
                    proc.kill()
                    killed = True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed:
        time.sleep(1) # 프로세스가 완전히 죽을 때까지 잠시 대기

def wait_for_api_server(port, timeout=10):
    url = f"http://127.0.0.1:{port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=1)
            if resp.status_code == 200:
                return True
        except:
            time.sleep(0.5)
    return False

def cleanup_process():
    global API_PROCESS
    if API_PROCESS:
        logger.info("Terminating AI API Server...")
        API_PROCESS.terminate()
        try:
            API_PROCESS.wait(timeout=2)
        except:
            API_PROCESS.kill()

atexit.register(cleanup_process)

def main():
    global API_PROCESS
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-port", type=int, required=False, default=0)
    parser.add_argument("--proxy-port", type=int, required=False, default=None)
    parser.add_argument("--no-proxy", action="store_true")
    args = parser.parse_args()

    # 1. Allocate Dynamic Port
    api_port = args.api_port
    if not api_port or api_port <= 0:
        api_port = get_free_port()
    
    logger.info(f"Allocated AI API Port: {api_port}")

    # [중요] 해당 포트를 사용 중인 좀비 프로세스 정리
    kill_process_on_port(api_port)
    
    # 2. Update Environment for Injector
    # ProxyPipeline 등 다른 모듈에서 참조할 수 있도록 환경변수 설정
    os.environ["AI_ENGINE_PORT"] = str(api_port)
    logger.info(f"[*] Environment 'AI_ENGINE_PORT' set to {api_port}")

    # 3. Launch API Server (Subprocess)
    api_script = os.path.join(os.path.dirname(__file__), 'core', 'api_server.py')
    cmd = [sys.executable, api_script, "--port", str(api_port)]
    logger.info(f"Launching: {' '.join(cmd)}")
    
    # Pass environment with new port
    env = os.environ.copy()
    
    API_PROCESS = subprocess.Popen(
        cmd,
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    # 4. Wait for Startup
    if not wait_for_api_server(api_port):
        logger.error("Failed to start AI API Server")
        cleanup_process()
        sys.exit(1)
        
    logger.info("AI API Server Online")

    # 5. Initialize Orchestrator
    use_proxy = not args.no_proxy and args.proxy_port is not None and args.proxy_port > 0
    
    orchestrator = SystemOrchestrator(
        api_port=api_port, 
        proxy_port=args.proxy_port if use_proxy else None
    )

    try:
        orchestrator.force_clear_system_proxy()
        
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
        cleanup_process()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()