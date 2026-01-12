const { app, BrowserWindow, ipcMain, session } = require('electron');
const path = require('path');
const getPort = require('get-port');
const processManager = require('./process-manager');
const certHandler = require('./cert-handler');

let mainWindow;
let ports = { api: 0, proxy: 0 };

// ============================================================
// [Core] 스크립트 주입 헬퍼 함수 (Dual-Pipeline)
// ============================================================
async function checkAndInject(webContents, url, frameRoutingId = null) {
  if (!url || url.startsWith('devtools:') || url.startsWith('file:')) return;

  try {
    // 1. Python Core에 매칭되는 스크립트 질의
    const response = await fetch(`http://127.0.0.1:${ports.api}/v1/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url })
    });
    
    if (!response.ok) return;
    
    const data = await response.json();
    const scripts = data.scripts;

    if (scripts && scripts.length > 0) {
      console.log(`[Electron] Injecting ${scripts.length} scripts into ${url} (Frame: ${frameRoutingId || 'Main'})`);
      
      // Smart Sandboxing 유지를 위해 src 방식으로 주입
      const injectionCode = `
        (function() {
            const scripts = ${JSON.stringify(scripts)};
            scripts.forEach(src => {
                // 중복 주입 방지
                if (document.querySelector(\`script[src="\${src}"]\`)) return;
                
                const s = document.createElement('script');
                s.src = src;
                s.async = false; // 순차 실행 보장
                document.head.appendChild(s);
            });
        })();
      `;

      // 프레임 ID 존재 여부에 따라 실행 시도
      if (frameRoutingId) {
         try {
             // 주의: executeJavaScript는 기본적으로 메인 프레임을 대상으로 하므로, 
             // 프레임별 제어가 필요할 경우 webFrameMain 등을 고려해야 하나 
             // 현재 구조에서는 간단한 실행을 시도합니다.
             // (필요 시 webContents.mainFrame.frames.find(...) 로직으로 고도화 가능)
             await webContents.executeJavaScript(injectionCode); 
         } catch(e) {
             console.warn(`[Electron] Iframe injection warning: ${e.message}`);
         }
      } else {
         // 메인 프레임 주입
         await webContents.executeJavaScript(injectionCode);
      }
    }
  } catch (e) {
    // 초기 기동 시 API 서버가 준비 안 되었을 수 있음 (무시 가능)
    // console.error(`[Electron] Injection Error (${url}):`, e.message);
  }
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      // [Security Policy for Plugin System] 
      // 로컬 API(HTTP)에서 스크립트를 불러오기 위해 보안 정책을 완화합니다.
      webSecurity: false,
      allowRunningInsecureContent: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

  // ============================================================
  // [Dual-Pipeline] 네비게이션 감지 및 Native 주입 훅
  // ============================================================
  
  // 1. 메인 프레임 이동 감지 (최초 로드, 새로고침 등)
  mainWindow.webContents.on('did-navigate', (event, url) => {
    checkAndInject(mainWindow.webContents, url);
  });

  // 2. SPA 내 페이지 이동 감지 (History API 사용 시)
  mainWindow.webContents.on('did-navigate-in-page', (event, url) => {
    checkAndInject(mainWindow.webContents, url);
  });

  // 3. Iframe 이동 감지
  mainWindow.webContents.on('did-frame-navigate', (event, url, httpResponseCode, httpStatusText, isMainFrame, frameProcessId, frameRoutingId) => {
    if (!isMainFrame) {
      checkAndInject(mainWindow.webContents, url, frameRoutingId); 
    }
  });

  // ============================================================
  // [Security] CSP(Content-Security-Policy) 이중 우회
  // ============================================================
  mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    const headersToRemove = [
      'content-security-policy',
      'content-security-policy-report-only',
      'x-content-security-policy',
      'x-frame-options' // Iframe 허용을 위해 추가 권장
    ];

    Object.keys(responseHeaders).forEach(header => {
      if (headersToRemove.includes(header.toLowerCase())) {
        delete responseHeaders[header];
      }
    });

    callback({ cancel: false, responseHeaders });
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
  } else {
      console.error("Process Manager not loaded correctly.");
  }
  
  // IPC 핸들러 등록
  ipcMain.handle('install-cert', () => certHandler.installCert());
  ipcMain.handle('get-status', () => ({ ...ports, status: 'Running (Dual-Pipeline Mode)' }));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (processManager) processManager.killAll();
  if (process.platform !== 'darwin') app.quit();
});