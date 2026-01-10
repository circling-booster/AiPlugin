const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');

let mainWindow;
let ports = { api: 0, proxy: 0, cloud: 0 }; // [Fixed] Add cloud port

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

  // [Fixed] Dynamic Port Allocation for ALL components
  ports.api = await getPort({ port: getPort.makeRange(5000, 5100) });
  ports.proxy = await getPort({ port: getPort.makeRange(8080, 8180) });
  ports.cloud = await getPort({ port: getPort.makeRange(8000, 8100) });

  console.log(`[Electron] Allocated Ports - API: ${ports.api}, Proxy: ${ports.proxy}, Cloud: ${ports.cloud}`);

  // [Fixed] Pass cloudPort explicitly to startCore to avoid race condition
  processManager.startCore(ports.api, ports.proxy, ports.cloud, mainWindow);
  processManager.startCloudServer(ports.cloud); 

  // IPC
  ipcMain.handle('install-cert', () => certHandler.installCert());
  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running' }));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});