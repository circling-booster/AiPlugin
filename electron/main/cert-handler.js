const { exec } = require('child_process');
const path = require('path');
const os = require('os');

const CERT_PATH = path.join(os.homedir(), '.mitmproxy', 'mitmproxy-ca-cert.cer');

function installCert() {
  return new Promise((resolve) => {
    // Windows CertUtil: 루트 인증서 저장소에 추가
    const cmd = `certutil -addstore "Root" "${CERT_PATH}"`;
    console.log(`[Cert] Installing: ${CERT_PATH}`);
    
    exec(cmd, (error, stdout, stderr) => {
      if (error) {
        console.error(`[Cert-Err] ${stderr}`);
        resolve({ success: false, message: stderr });
      } else {
        console.log(`[Cert] Output: ${stdout.trim()}`);
        resolve({ success: true, message: "Installed Successfully" });
      }
    });
  });
}

module.exports = { installCert };