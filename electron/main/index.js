const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');

let mainWindow;
// [Modified] cloud 포트 변수 제거 (외부 서버 사용 시 불필요)
let ports = { api: 0, proxy: 0 }; 

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // ============================================================
  // [Spec 1.2] CSP 이중 우회 로직 (Electron Level)
  // ============================================================
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    const headersToRemove = [
      'content-security-policy',
      'content-security-policy-report-only',
      'x-content-security-policy'
    ];

    Object.keys(responseHeaders).forEach(header => {
      if (headersToRemove.includes(header.toLowerCase())) {
        delete responseHeaders[header];
      }
    });

    callback({ cancel: false, responseHeaders });
  });

  // [Modified] Local Cloud Port 할당 로직 제거
  ports.api = await getPort({ port: getPort.makeRange(5000, 5100) });
  ports.proxy = await getPort({ port: getPort.makeRange(8080, 8180) });
  
  console.log(`[Electron] Allocated Ports - API: ${ports.api}, Proxy: ${ports.proxy} (External Cloud Mode)`);

  // [Modified] startCloudServer 호출 제거 및 cloudPort 인자에 0 전달
  processManager.startCore(ports.api, ports.proxy, 0, mainWindow);
  
  // processManager.startCloudServer(ports.cloud); // <-- 삭제됨: 로컬 클라우드 서버 실행 안 함

  // IPC
  ipcMain.handle('install-cert', () => certHandler.installCert());
  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running (External Cloud)' }));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});