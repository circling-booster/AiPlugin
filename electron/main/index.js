const { app, BrowserWindow, BrowserView, ipcMain, session } = require('electron');
const path = require('path');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');

let mainWindow;
let activeView = null; // 현재 활성화된 BrowserView
let ports = { api: 0, proxy: 0 };

// UI 상수
const TOP_BAR_HEIGHT = 80; // 주소창 및 컨트롤러 영역 높이

// ============================================================
// [Core] 스크립트 주입 헬퍼 함수 (Dual-Pipeline)
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
         try {
             await webContents.executeJavaScript(injectionCode); 
         } catch(e) {
             console.warn(`[Electron] Iframe injection warning: ${e.message}`);
         }
      } else {
         await webContents.executeJavaScript(injectionCode);
      }
    }
  } catch (e) {
    // API 서버 준비 전 에러 무시
  }
}

// ============================================================
// [Feature] BrowserView 관리자 (Embedded Browser)
// ============================================================
function createBrowserView(targetUrl) {
  // 기존 뷰 제거 (메모리 관리)
  if (activeView) {
    mainWindow.removeBrowserView(activeView);
    activeView.webContents.destroy(); // 리소스 완전 해제
    activeView = null;
  }

  const view = new BrowserView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false, // 플러그인 호환성을 위해 유지
      allowRunningInsecureContent: true
    }
  });

  mainWindow.setBrowserView(view);
  activeView = view;

  // [Layout] 뷰 위치 잡기 (상단 바 제외한 나머지 영역)
  updateViewBounds();

  // [Dual-Pipeline] 주입 로직 연결
  view.webContents.on('did-navigate', (e, url) => {
    mainWindow.webContents.send('update-url', url); // UI 주소창 업데이트
    checkAndInject(view.webContents, url);
  });

  view.webContents.on('did-navigate-in-page', (e, url) => {
    mainWindow.webContents.send('update-url', url);
    checkAndInject(view.webContents, url);
  });

  view.webContents.on('did-frame-navigate', (event, url, httpResponseCode, httpStatusText, isMainFrame, frameProcessId, frameRoutingId) => {
    if (!isMainFrame) {
      checkAndInject(view.webContents, url, frameRoutingId); 
    }
  });

  // 페이지 타이틀 업데이트
  view.webContents.on('page-title-updated', (e, title) => {
    mainWindow.webContents.send('update-title', title);
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
// [Security] CSP 이중 우회 (Global Session Listener)
// ============================================================
function setupSessionSecurity() {
  // BrowserView와 MainWindow가 공유하는 기본 세션에 적용
  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    const headersToRemove = [
      'content-security-policy',
      'content-security-policy-report-only',
      'x-content-security-policy',
      'x-frame-options'
    ];

    Object.keys(responseHeaders).forEach(header => {
      if (headersToRemove.includes(header.toLowerCase())) {
        delete responseHeaders[header];
      }
    });

    callback({ cancel: false, responseHeaders });
  });
}

async function createWindow() {
  // 1. 보안 설정 (앱 시작 시 1회 적용)
  setupSessionSecurity();

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // ============================================================
  // [Event] Window Resizing 대응
  // ============================================================
  mainWindow.on('resize', () => {
    updateViewBounds();
  });

  mainWindow.on('maximize', () => {
    updateViewBounds();
  });

  // 포트 할당
  try {
    ports.api = await getPort({ port: getPort.makeRange(5000, 5100) });
    ports.proxy = await getPort({ port: getPort.makeRange(8080, 8180) });
    console.log(`[Electron] Allocated Ports - API: ${ports.api}, Proxy: ${ports.proxy}`);
  } catch (err) {
    console.error("Failed to allocate ports:", err);
  }

  // Core 프로세스 시작
  if (processManager && typeof processManager.startCore === 'function') {
      processManager.startCore(ports.api, ports.proxy, mainWindow);
  }

  // ============================================================
  // [IPC] Renderer <-> Main 통신
  // ============================================================
  ipcMain.handle('install-cert', () => certHandler.installCert());
  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running (Embedded Browser Mode)' }));
  
  // 브라우저 네비게이션 IPC
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