@echo off
echo [AiPlugs] EMERGENCY RESET: Disabling Windows Proxy...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
echo [AiPlugs] Proxy Disabled.
echo [AiPlugs] Attempting to refresh system settings...
powershell -Command "[Runtime.InteropServices.Marshal]::ReleaseComObject([Runtime.InteropServices.Marshal]::GetActiveObject('InternetExplorer.Application'))" >nul 2>&1
pause