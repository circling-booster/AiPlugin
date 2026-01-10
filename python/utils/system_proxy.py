import logging
import sys
import subprocess

# Windows 종속 모듈 조건부 임포트
if sys.platform == "win32":
    import winreg
    import ctypes
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
        """
        [Improved] Dynamically detect the primary active network service.
        """
        try:
            cmd = ["networksetup", "-listallnetworkservices"]
            result = subprocess.run(cmd, capture_output=True, text=True).stdout
            services = result.strip().split('\n')
            
            # Filter out inactive/irrelevant lines
            clean_services = [s for s in services if '*' not in s and 'network services' not in s.lower()]
            
            # Priority Check (일반적인 우선순위)
            if "Wi-Fi" in clean_services: return "Wi-Fi"
            if "Ethernet" in clean_services: return "Ethernet"
            if "USB 10/100/1000 LAN" in clean_services: return "USB 10/100/1000 LAN"
            
            # Fallback to the first available service
            return clean_services[0] if clean_services else "Wi-Fi"
        except Exception as e:
            self.logger.warning(f"Failed to detect Mac Service ({e}). Defaulting to Wi-Fi.")
            return "Wi-Fi"

    def _set_mac_proxy(self, ip, port):
        service = self._get_mac_service()
        try:
            subprocess.run(["networksetup", "-setwebproxy", service, ip, str(port)], check=True)
            subprocess.run(["networksetup", "-setsecurewebproxy", service, ip, str(port)], check=True)
            self.logger.info(f"[Mac] Proxy set on {service}")
        except Exception as e:
            self.logger.error(f"[Mac] Failed to set proxy on {service}: {e}")

    def _disable_mac_proxy(self):
        service = self._get_mac_service()
        try:
            subprocess.run(["networksetup", "-setwebproxystate", service, "off"], check=True)
            subprocess.run(["networksetup", "-setsecurewebproxystate", service, "off"], check=True)
            self.logger.info(f"[Mac] Proxy disabled on {service}")
        except Exception as e:
            self.logger.error(f"[Mac] Failed to disable proxy on {service}: {e}")