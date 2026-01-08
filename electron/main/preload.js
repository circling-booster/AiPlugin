const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  onLog: (callback) => ipcRenderer.on('log', (_event, val) => callback(val)),
  getStatus: () => ipcRenderer.invoke('get-status'),
  installCert: () => ipcRenderer.invoke('install-cert')
});