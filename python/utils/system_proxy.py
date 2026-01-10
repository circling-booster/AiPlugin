import logging
import sys
import subprocess

# [수정 1] OS 종속 모듈 조건부 임포트
if sys.platform == "win32":
    import winreg
    import ctypes
    # WinINet Constants
    INTERNET_OPTION_SETTINGS_CHANGED = 39
    INTERNET_OPTION_REFRESH = 37

class SystemProxy:
    def __init__(self):
        self.logger = logging.getLogger("SystemProxy")
        self.os_type = sys.platform

    def set_proxy(self, ip: str, port: int):
        if self.os_type == "win32":
            self._set_windows_proxy(ip, port)
        elif self.os_type == "darwin":
            self._set_mac_proxy(ip, port)

    def disable_proxy(self):
        if self.os_type == "win32":
            self._disable_windows_proxy()
        elif self.os_type == "darwin":
            self._disable_mac_proxy()

    # --- Windows Logic ---
    def _set_windows_proxy(self, ip, port):
        try:
            proxy_server = f"{ip}:{port}"
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            winreg.CloseKey(key)
            self._refresh_windows()
            self.logger.info(f"[Win] Proxy set to {proxy_server}")
        except Exception as e:
            self.logger.error(f"[Win] Error: {e}")

    def _disable_windows_proxy(self):
        try:
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            self._refresh_windows()
            self.logger.info("[Win] Proxy Disabled")
        except Exception as e:
            self.logger.error(f"[Win] Error: {e}")

    def _refresh_windows(self):
        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)

    # --- MacOS Logic ---
    def _get_mac_service(self):
        # 현재 활성화된 네트워크 서비스(Wi-Fi 등) 이름을 자동으로 찾음
        try:
            # networksetup -listallnetworkservices 결과 파싱 필요하지만
            # 간단하게 가장 많이 쓰는 'Wi-Fi'를 기본으로 하고 실패시 로그
            return "Wi-Fi" 
        except:
            return "Wi-Fi"

    def _set_mac_proxy(self, ip, port):
        # networksetup은 일반적으로 sudo 없이 동작할 수 있으나(사용자 설정에 따라 다름),
        # 안전하게 하려면 subprocess 사용
        service = self._get_mac_service()
        try:
            subprocess.run(["networksetup", "-setwebproxy", service, ip, str(port)], check=True)
            subprocess.run(["networksetup", "-setsecurewebproxy", service, ip, str(port)], check=True)
            self.logger.info(f"[Mac] Proxy set on {service}")
        except Exception as e:
            self.logger.error(f"[Mac] Failed to set proxy: {e}")

    def _disable_mac_proxy(self):
        service = self._get_mac_service()
        try:
            subprocess.run(["networksetup", "-setwebproxystate", service, "off"], check=True)
            subprocess.run(["networksetup", "-setsecurewebproxystate", service, "off"], check=True)
            self.logger.info(f"[Mac] Proxy disabled on {service}")
        except Exception as e:
            self.logger.error(f"[Mac] Failed to disable proxy: {e}")