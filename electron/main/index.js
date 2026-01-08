const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');

let mainWindow;
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
  // 보안 정책 헤더를 브라우저 세션 단계에서 제거합니다.
  // ============================================================
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    // 기존 헤더 복사
    const responseHeaders = { ...details.responseHeaders };
    
    // 제거할 CSP 관련 헤더 목록 (소문자 처리)
    const headersToRemove = [
      'content-security-policy',
      'content-security-policy-report-only',
      'x-content-security-policy'
    ];

    // 헤더 순회하며 CSP 제거
    Object.keys(responseHeaders).forEach(header => {
      if (headersToRemove.includes(header.toLowerCase())) {
        delete responseHeaders[header];
      }
    });

    callback({ cancel: false, responseHeaders });
  });

  // 포트 할당
  ports.api = await getPort({ port: getPort.makeRange(5000, 5100) });
  ports.proxy = await getPort({ port: getPort.makeRange(8080, 8180) });

  // Core & Cloud 실행
  processManager.startCore(ports.api, ports.proxy, mainWindow);
  processManager.startCloudServer();

  // IPC
  ipcMain.handle('install-cert', () => certHandler.installCert());
  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running' }));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});