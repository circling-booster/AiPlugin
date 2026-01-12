const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  onLog: (callback) => ipcRenderer.on('log', (_event, val) => callback(val)),
  getStatus: () => ipcRenderer.invoke('get-status'),
  installCert: () => ipcRenderer.invoke('install-cert'),
  
  // [New] Browser Control API
  navigateTo: (url) => ipcRenderer.send('navigate-to', url),
  control: (action) => ipcRenderer.send('browser-control', action),
  onUpdateUrl: (callback) => ipcRenderer.on('update-url', (_event, url) => callback(url)),
  onUpdateTitle: (callback) => ipcRenderer.on('update-title', (_event, title) => callback(title))
});