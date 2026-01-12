const { app, BrowserWindow, BrowserView, ipcMain, session } = require('electron');
const path = require('path');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');

let mainWindow;
let activeView = null; // 현재 활성화된 BrowserView
let ports = { api: 0, proxy: 0 };

// UI 상수
const TOP_BAR_HEIGHT = 80;

// ============================================================
// [Helper] F12 개발자 도구 토글 기능 (Key Binding)
// ============================================================
function setupDevToolsToggle(webContents) {
  webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.key === 'F12') {
      webContents.toggleDevTools();
      event.preventDefault(); // 기본 동작 방지
    }
  });
}

// ============================================================
// [Core] 스크립트 주입 헬퍼 함수
// ============================================================
async function checkAndInject(webContents, url, frameRoutingId = null) {
  if (!url || url.startsWith('devtools:') || url.startsWith('file:')) return;

  try {
    const response = await fetch(`http://127.0.0.1:${ports.api}/v1/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });
    
    if (!response.ok) return;
    
    const data = await response.json();
    const scripts = data.scripts;

    if (scripts && scripts.length > 0) {
      console.log(`[Electron] Injecting ${scripts.length} scripts into ${url}`);
      
      const injectionCode = `
        (function() {
            // [Config Injection]
            window.AIPLUGS_API_PORT = ${ports.api};
            
            // [Script Injection]
            const scripts = ${JSON.stringify(scripts)};
            scripts.forEach(src => {
                if (document.querySelector(\`script[src="\${src}"]\`)) return;
                const s = document.createElement('script');
                s.src = src;
                s.async = false;
                document.head.appendChild(s);
            });
        })();
      `;

      if (frameRoutingId) {
         try { await webContents.executeJavaScript(injectionCode); } catch(e) {}
      } else {
         await webContents.executeJavaScript(injectionCode);
      }
    }
  } catch (e) {}
}

// ============================================================
// [Feature] BrowserView 관리자
// ============================================================
function createBrowserView(targetUrl) {
  if (activeView) {
    mainWindow.removeBrowserView(activeView);
    try { activeView.webContents.destroy(); } catch(e) {}
    activeView = null;
  }

  const view = new BrowserView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false, 
      allowRunningInsecureContent: true,
      nativeWindowOpen: true
    }
  });

  mainWindow.setBrowserView(view);
  activeView = view;

  // [Fix] 팝업 처리
  view.webContents.setWindowOpenHandler(({ url }) => {
    console.log(`[Popup] Handled: ${url}`);
    return { action: 'allow' };
  });

  // [Fix] F12 키 바인딩 (웹페이지용)
  setupDevToolsToggle(view.webContents);

  updateViewBounds();

  // Navigation Events
  view.webContents.on('did-navigate', (e, url) => {
    if(!mainWindow.isDestroyed()) mainWindow.webContents.send('update-url', url);
    checkAndInject(view.webContents, url);
  });

  view.webContents.on('did-navigate-in-page', (e, url) => {
    if(!mainWindow.isDestroyed()) mainWindow.webContents.send('update-url', url);
    checkAndInject(view.webContents, url);
  });
  
  view.webContents.on('did-frame-navigate', (event, url, httpResponseCode, httpStatusText, isMainFrame, frameProcessId, frameRoutingId) => {
    if (!isMainFrame) checkAndInject(view.webContents, url, frameRoutingId); 
  });

  view.webContents.on('page-title-updated', (e, title) => {
    if(!mainWindow.isDestroyed()) mainWindow.webContents.send('update-title', title);
  });

  view.webContents.loadURL(targetUrl);
}

function updateViewBounds() {
  if (mainWindow && activeView) {
    const bounds = mainWindow.getContentBounds();
    activeView.setBounds({ 
      x: 0, 
      y: TOP_BAR_HEIGHT, 
      width: bounds.width, 
      height: bounds.height - TOP_BAR_HEIGHT 
    });
  }
}

// ============================================================
// [Security] CSP 이중 우회
// ============================================================
function setupSessionSecurity() {
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    const headersToRemove = [
      'content-security-policy',
      'content-security-policy-report-only',
      'x-content-security-policy',
      'x-frame-options'
    ];
    Object.keys(responseHeaders).forEach(header => {
      if (headersToRemove.includes(header.toLowerCase())) delete responseHeaders[header];
    });
    callback({ cancel: false, responseHeaders });
  });
}

async function createWindow() {
  setupSessionSecurity();

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    backgroundColor: '#1e1e1e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // [Fix] F12 키 바인딩 (UI용)
  setupDevToolsToggle(mainWindow.webContents);

  mainWindow.on('resize', updateViewBounds);
  mainWindow.on('maximize', updateViewBounds);
  mainWindow.on('unmaximize', updateViewBounds);

  try {
    ports.api = await getPort({ port: getPort.makeRange(5000, 5100) });
    ports.proxy = await getPort({ port: getPort.makeRange(8080, 8180) });
    console.log(`[Electron] Allocated Ports - API: ${ports.api}, Proxy: ${ports.proxy}`);
  } catch (err) {
    console.error("Failed to allocate ports:", err);
  }

  if (processManager && typeof processManager.startCore === 'function') {
      processManager.startCore(ports.api, ports.proxy, mainWindow);
  }

  ipcMain.handle('install-cert', () => certHandler.installCert());
  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running (Embedded Browser Mode)' }));
  
  ipcMain.on('navigate-to', (event, url) => {
    let target = url;
    if (!target.startsWith('http')) target = 'https://' + target;
    createBrowserView(target);
  });

  ipcMain.on('browser-control', (event, action) => {
    if (!activeView) return;
    switch(action) {
      case 'back': if (activeView.webContents.canGoBack()) activeView.webContents.goBack(); break;
      case 'forward': if (activeView.webContents.canGoForward()) activeView.webContents.goForward(); break;
      case 'refresh': activeView.webContents.reload(); break;
    }
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (processManager) processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});