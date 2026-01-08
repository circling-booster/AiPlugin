import ctypes
import logging
import winreg

# WinINet Constants
INTERNET_OPTION_SETTINGS_CHANGED = 39
INTERNET_OPTION_REFRESH = 37

class SystemProxy:
    def __init__(self):
        self.logger = logging.getLogger("SystemProxy")

    def set_proxy(self, ip: str, port: int):
        """
        WinINet과 레지스트리를 활용하여 Windows 시스템 프록시를 강제 설정
        """
        try:
            proxy_server = f"{ip}:{port}"
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, proxy_server)
            winreg.CloseKey(key)
            
            self._refresh_settings()
            self.logger.info(f"System Proxy Enabled: {proxy_server}")
        except Exception as e:
            self.logger.error(f"Failed to set proxy: {e}")

    def disable_proxy(self):
        try:
            path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            
            self._refresh_settings()
            self.logger.info("System Proxy Disabled")
        except Exception as e:
            self.logger.error(f"Failed to disable proxy: {e}")

    def _refresh_settings(self):
        # WinINet API를 호출하여 설정 즉시 반영 (재부팅 불필요)
        internet_set_option = ctypes.windll.Wininet.InternetSetOptionW
        internet_set_option(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)
        internet_set_option(0, INTERNET_OPTION_REFRESH, 0, 0)