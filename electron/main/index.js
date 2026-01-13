// electron/main/index.js

const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const fs = require('fs');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');
const { initAppSwitches, setupSessionBypass } = require('./security-bypass');
const TabManager = require('./managers/tab-manager');

let mainWindow;
let tabManager;
let ports = { api: 0, proxy: 0 };
let globalConfig = {}; 

function loadConfigAndApplySwitches() {
    try {
        const configPath = path.join(__dirname, '../../config/config.json');
        if (fs.existsSync(configPath)) {
            globalConfig = JSON.parse(fs.readFileSync(configPath));
            initAppSwitches(globalConfig);
        }
    } catch (e) {
        console.error("[Config] Pre-load failed:", e);
    }
}

loadConfigAndApplySwitches();

// [Inject Logic] TabManager의 이벤트를 받아 실행
async function checkAndInject(webContents, url, frameRoutingId = null) {
  if (!url || url.startsWith('devtools:') || url.startsWith('file:') || !ports.api) return;

  // [수정] Config에서 Host 정보를 가져오거나 기본값 사용 (하드코딩 제거)
  const apiHost = globalConfig?.system_settings?.ai_engine?.host || '127.0.0.1';
  const apiBaseUrl = `http://${apiHost}:${ports.api}`;

  try {
    // [수정] apiBaseUrl 변수 사용
    const response = await fetch(`${apiBaseUrl}/v1/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });

    if (!response.ok) return;
    const data = await response.json();

    if (data.scripts && data.scripts.length > 0) {
      // [수정] 주입 코드에 API_HOST 정보 전달 및 동적 URL 생성 로직 적용
      const injectionCode = `
        (function() {
            window.AIPLUGS_API_PORT = ${ports.api};
            window.AIPLUGS_API_HOST = "${apiHost}";
            
            const scripts = ${JSON.stringify(data.scripts)};
            scripts.forEach(scriptItem => {
                let src = scriptItem.url;
                
                // 상대 경로인 경우 설정된 호스트와 포트를 사용하여 절대 경로로 변환
                if (src && !src.startsWith('http') && !src.startsWith('//')) {
                    src = 'http://' + window.AIPLUGS_API_HOST + ':' + window.AIPLUGS_API_PORT + '/' + src;
                }
                
                const runAt = scriptItem.run_at || 'document_end';
                
                // 변환된 src를 기준으로 중복 주입 방지 체크
                if (document.querySelector(\`script[src="\${src}"]\`)) return;
                
                const inject = () => {
                    const s = document.createElement('script');
                    s.src = src; 
                    s.async = false;
                    (document.head || document.documentElement).appendChild(s);
                };
                
                if (runAt === 'document_start') { inject(); }
                else if (runAt === 'document_end') {
                    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', inject);
                    else inject();
                } else { 
                    if (document.readyState === 'complete') inject();
                    else window.addEventListener('load', inject);
                }
            });
        })();
      `;
      if (frameRoutingId) {
        try { await webContents.executeJavaScript(injectionCode); } catch (e) { }
      } else {
        await webContents.executeJavaScript(injectionCode);
      }
    }
  } catch (e) { 
      // 초기 기동 시 API 서버 미준비 상태 무시
  }
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280, height: 900,
    backgroundColor: '#1e1e1e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });
  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // [중요] TabManager 초기화 시 현재 경로(__dirname) 전달
  tabManager = new TabManager(mainWindow, __dirname);
  
  // 리사이징 위임
  mainWindow.on('resize', () => tabManager.updateViewBounds());
  mainWindow.on('maximize', () => tabManager.updateViewBounds());

  // [이벤트 연결] TabManager가 네비게이션을 알리면 주입 로직 실행
  tabManager.on('did-navigate', ({ view, url }) => {
      checkAndInject(view.webContents, url);
  });

  if (globalConfig.system_settings) {
      setupSessionBypass(session.defaultSession, globalConfig);
  }

  let useProxy = true;
  try {
    const settingsPath = path.join(__dirname, '../../config/settings.json');
    if (fs.existsSync(settingsPath)) {
        const legacySettings = JSON.parse(fs.readFileSync(settingsPath));
        if (legacySettings.system_mode === 'native-only') useProxy = false;
    }
  } catch (e) { }

  try {
    ports.api = await getPort({ port: getPort.makeRange(5000, 5100) });
    ports.proxy = useProxy ? await getPort({ port: getPort.makeRange(8080, 8180) }) : 0;
  } catch (err) {
    console.error("Port allocation failed:", err);
  }

  processManager.startCore(ports.api, ports.proxy, mainWindow);
  
  // 초기 탭 생성
  tabManager.createTab('https://www.google.com');

  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running' }));
  ipcMain.handle('install-cert', () => certHandler.installCert());

  // [IPC 핸들러] TabManager로 위임
  ipcMain.on('tab-create', (e, data = {}) => tabManager.createTab(data.url || 'https://www.google.com'));
  ipcMain.on('tab-switch', (e, data = {}) => tabManager.switchToTab(data.tabId));
  ipcMain.on('tab-close', (e, data = {}) => tabManager.closeTab(data.tabId));
  ipcMain.on('navigate-to', (e, url) => {
      let target = url;
      if (!target.startsWith('http')) target = 'https://' + target;
      if (tabManager.activeTabId) {
          const tab = tabManager.tabs.get(tabManager.activeTabId);
          if (tab) tab.view.webContents.loadURL(target);
      } else {
          tabManager.createTab(target);
      }
  });
  ipcMain.on('browser-control', (e, action) => tabManager.handleBrowserControl(action));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});