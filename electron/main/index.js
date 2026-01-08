const { app, BrowserWindow, ipcMain } = require('electron');
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