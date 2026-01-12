const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  // 로그 및 시스템 상태
  onLog: (callback) => ipcRenderer.on('log', (_event, val) => callback(val)),
  getStatus: () => ipcRenderer.invoke('get-status'),
  installCert: () => ipcRenderer.invoke('install-cert'),
  
  // [Checklist] 호출 규약: 통합 브라우저 컨트롤 인터페이스
  control: (action, data = {}) => {
      // action: 'tab-create', 'tab-switch', 'tab-close', 'back', 'forward', 'refresh'
      if (['tab-create', 'tab-switch', 'tab-close'].includes(action)) {
          ipcRenderer.send(action, data);
      } else {
          ipcRenderer.send('browser-control', action);
      }
  },
  
  navigateTo: (url) => ipcRenderer.send('navigate-to', url),

  // UI 업데이트 리스너 (Events from Main)
  onTabCreated: (callback) => ipcRenderer.on('tab-created', (_event, data) => callback(data)),
  onTabSwitchConfirm: (callback) => ipcRenderer.on('tab-switch-confirm', (_event, data) => callback(data)),
  onTabState: (callback) => ipcRenderer.on('tab-state', (_event, data) => callback(data)),
  onUpdateUrl: (callback) => ipcRenderer.on('update-url', (_event, data) => callback(data)),
  onUpdateNavState: (callback) => ipcRenderer.on('update-nav-state', (_event, data) => callback(data))
});