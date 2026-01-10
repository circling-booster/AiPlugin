const { exec } = require('child_process');
const path = require('path');
const os = require('os');

const CERT_PATH = path.join(os.homedir(), '.mitmproxy', 'mitmproxy-ca-cert.cer');

function installCert() {
  return new Promise((resolve) => {
    const platform = os.platform();
    let cmd = '';

    if (platform === 'win32') {
      cmd = `certutil -addstore "Root" "${CERT_PATH}"`;
      
      exec(cmd, (error, stdout, stderr) => {
         // (기존 윈도우 로직 유지)
         if (error) resolve({ success: false, message: stderr });
         else resolve({ success: true, message: stdout.trim() });
      });

    } else if (platform === 'darwin') {
      // [핵심] AppleScript를 사용하여 관리자 권한 요청 팝업 띄우기
      const command = `security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "${CERT_PATH}"`;
      const appleScript = `do shell script "${command}" with administrator privileges`;
      
      exec(`osascript -e '${appleScript}'`, (error, stdout, stderr) => {
        if (error) {
          console.error(`[Cert-Err] ${stderr}`);
          // 사용자가 취소했을 경우 등 처리
          resolve({ success: false, message: "Installation Cancelled or Failed" });
        } else {
          console.log(`[Cert] Installed`);
          resolve({ success: true, message: "Installed Successfully (Mac)" });
        }
      });
    }
  });
}

module.exports = { installCert };