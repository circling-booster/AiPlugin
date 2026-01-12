const { app, BrowserWindow, BrowserView, ipcMain, session } = require('electron'); // [수정] session 추가
const path = require('path');
const fs = require('fs');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');
const { setupSecurityBypass } = require('./security-bypass'); // [추가] 보안 모듈 임포트

let mainWindow;
let ports = { api: 0, proxy: 0 };
const tabs = new Map(); 
let activeTabId = null;
const TOP_BAR_HEIGHT = 70;

async function checkAndInject(webContents, url, frameRoutingId = null) {
  if (!url || url.startsWith('devtools:') || url.startsWith('file:') || !ports.api) return;

  try {
    const response = await fetch(`http://127.0.0.1:${ports.api}/v1/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });

    if (!response.ok) return;
    const data = await response.json();

    if (data.scripts && data.scripts.length > 0) {
      const injectionCode = `
        (function() {
            window.AIPLUGS_API_PORT = ${ports.api};
            const scripts = ${JSON.stringify(data.scripts)};
            scripts.forEach(src => {
                if (document.querySelector(\`script[src="\${src}"]\`)) return;
                const s = document.createElement('script');
                s.src = src; s.async = false;
                document.head.appendChild(s);
            });
        })();
      `;
      if (frameRoutingId) {
        try { await webContents.executeJavaScript(injectionCode); } catch (e) { }
      } else {
        await webContents.executeJavaScript(injectionCode);
      }
    }
  } catch (e) { }
}

function createTab(targetUrl) {
  const tabId = Date.now();
  const view = new BrowserView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      nativeWindowOpen: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  setupViewListeners(view, tabId);
  view.webContents.loadURL(targetUrl);

  tabs.set(tabId, { view, title: 'New Tab', url: targetUrl });
  switchToTab(tabId);

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('tab-created', { tabId });
  }
  return tabId;
}

function setupViewListeners(view, tabId) {
  view.webContents.on('did-navigate', (e, url) => {
    const tab = tabs.get(tabId);
    if (tab) tab.url = url;

    checkAndInject(view.webContents, url);

    if (tabId === activeTabId) {
      mainWindow.webContents.send('update-url', { tabId, url });
      updateNavigationState(view);
    }
  });

  view.webContents.on('page-title-updated', (e, title) => {
    const tab = tabs.get(tabId);
    if (tab) tab.title = title;
    mainWindow.webContents.send('tab-state', { tabId, title });
  });

  view.webContents.setWindowOpenHandler(() => ({ action: 'allow' }));

  view.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.key === 'F12') {
      if (view.webContents.isDevToolsOpened()) {
        view.webContents.closeDevTools();
      } else {
        view.webContents.openDevTools({ mode: 'detach' });
      }
      event.preventDefault();
    }
  });
}

function switchToTab(tabId) {
  const tab = tabs.get(tabId);
  if (!tab) return;
  activeTabId = tabId;

  mainWindow.setBrowserView(tab.view);
  updateViewBounds();
  tab.view.webContents.focus();

  mainWindow.webContents.send('tab-switch-confirm', { tabId });
  mainWindow.webContents.send('update-url', { tabId, url: tab.url });
  updateNavigationState(tab.view);
}

function closeTab(tabId) {
  const tab = tabs.get(tabId);
  if (tab) {
    if (activeTabId === tabId) {
      mainWindow.setBrowserView(null);
      activeTabId = null;
    }
    try { tab.view.webContents.destroy(); } catch (e) { }
    tabs.delete(tabId);

    const keys = Array.from(tabs.keys());
    if (keys.length > 0) switchToTab(keys[keys.length - 1]);
    else createTab('https://www.google.com');
  }
}

function updateViewBounds() {
  if (mainWindow && activeTabId) {
    const tab = tabs.get(activeTabId);
    if (tab && tab.view) {
      const bounds = mainWindow.getContentBounds();
      if (bounds.width > 0 && bounds.height > TOP_BAR_HEIGHT) {
        tab.view.setBounds({
          x: 0, y: TOP_BAR_HEIGHT,
          width: bounds.width, height: bounds.height - TOP_BAR_HEIGHT
        });
      }
    }
  }
}

function updateNavigationState(view) {
  if (!view || !view.webContents || view.webContents.isDestroyed()) return;
  mainWindow.webContents.send('update-nav-state', {
    canGoBack: view.webContents.canGoBack(),
    canGoForward: view.webContents.canGoForward()
  });
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
  mainWindow.on('resize', updateViewBounds);
  mainWindow.on('maximize', updateViewBounds);

  // [추가] 설정 로드 및 보안 우회 적용
  let settings = {};
  try {
    // config.json 로드 (보안 우회 설정 포함)
    const configPath = path.join(__dirname, '../../config/config.json');
    if (fs.existsSync(configPath)) {
        settings = JSON.parse(fs.readFileSync(configPath));
        setupSecurityBypass(session.defaultSession, settings);
    } else {
        console.warn("[Config] config.json not found.");
    }
  } catch (e) { 
    console.error("[Config] Load failed or Bypass setup error:", e);
  }

  // [기존 유지] Native 모드 설정 확인 (settings.json 사용)
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
  createTab('https://www.google.com');

  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running' }));
  ipcMain.handle('install-cert', () => certHandler.installCert());

  ipcMain.on('tab-create', (e, data = {}) => createTab(data.url || 'https://www.google.com'));
  ipcMain.on('tab-switch', (e, data = {}) => switchToTab(data.tabId));
  ipcMain.on('tab-close', (e, data = {}) => closeTab(data.tabId));

  ipcMain.on('browser-control', (e, action) => {
    if (!activeTabId) return;
    const tab = tabs.get(activeTabId);
    if (tab && tab.view && !tab.view.webContents.isDestroyed()) {
      const wc = tab.view.webContents;
      if (action === 'back' && wc.canGoBack()) wc.goBack();
      if (action === 'forward' && wc.canGoForward()) wc.goForward();
      if (action === 'refresh') wc.reload();
    }
  });

  ipcMain.on('navigate-to', (e, url) => {
    let target = url;
    if (!target.startsWith('http')) target = 'https://' + target;
    if (activeTabId) {
      const tab = tabs.get(activeTabId);
      if (tab) tab.view.webContents.loadURL(target);
    } else {
      createTab(target);
    }
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});