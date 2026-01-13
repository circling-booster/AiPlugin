// electron/main/managers/tab-manager.js

const { BrowserView } = require('electron');
const path = require('path');
const EventEmitter = require('events');

class TabManager extends EventEmitter {
    // appPath를 인자로 받아 경로 의존성 제거
    constructor(mainWindow, appPath, topBarHeight = 70) {
        super();
        this.mainWindow = mainWindow;
        this.appPath = appPath; 
        this.tabs = new Map();
        this.activeTabId = null;
        this.TOP_BAR_HEIGHT = topBarHeight;
    }

    createTab(url) {
        const tabId = Date.now();
        // 절대 경로 사용으로 안전성 확보
        const preloadPath = path.join(this.appPath, 'preload.js');
        
        const view = new BrowserView({
            webPreferences: {
                nodeIntegration: false,
                contextIsolation: true,
                nativeWindowOpen: true,
                preload: preloadPath
            }
        });

        this.setupViewListeners(view, tabId);
        view.webContents.loadURL(url);

        this.tabs.set(tabId, { view, title: 'New Tab', url });
        this.switchToTab(tabId);
        
        if (!this.mainWindow.isDestroyed()) {
            this.mainWindow.webContents.send('tab-created', { tabId });
        }
        return tabId;
    }

    setupViewListeners(view, tabId) {
        view.webContents.on('did-navigate', (e, url) => {
            const tab = this.tabs.get(tabId);
            if (tab) tab.url = url;
            
            // 이벤트를 상위(index.js)로 전달하여 주입 로직 실행
            this.emit('did-navigate', { tabId, view, url });
            
            if (tabId === this.activeTabId) {
                this.mainWindow.webContents.send('update-url', { tabId, url });
                this.updateNavigationState(view);
            }
        });

        view.webContents.on('page-title-updated', (e, title) => {
            const tab = this.tabs.get(tabId);
            if (tab) tab.title = title;
            this.mainWindow.webContents.send('tab-state', { tabId, title });
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

    switchToTab(tabId) {
        const tab = this.tabs.get(tabId);
        if (!tab) return;
        this.activeTabId = tabId;

        this.mainWindow.setBrowserView(tab.view);
        this.updateViewBounds();
        tab.view.webContents.focus();

        this.mainWindow.webContents.send('tab-switch-confirm', { tabId });
        this.mainWindow.webContents.send('update-url', { tabId, url: tab.url });
        this.updateNavigationState(tab.view);
    }

    closeTab(tabId) {
        const tab = this.tabs.get(tabId);
        if (!tab) return;

        if (this.activeTabId === tabId) {
            this.mainWindow.setBrowserView(null);
            this.activeTabId = null;
        }
        try { tab.view.webContents.destroy(); } catch (e) { }
        this.tabs.delete(tabId);

        const keys = Array.from(this.tabs.keys());
        if (keys.length > 0) {
            this.switchToTab(keys[keys.length - 1]);
        } else {
            this.createTab('https://www.google.com');
        }
    }

    updateViewBounds() {
        if (!this.activeTabId) return;
        const tab = this.tabs.get(this.activeTabId);
        if (tab && tab.view && !this.mainWindow.isDestroyed()) {
            const bounds = this.mainWindow.getContentBounds();
            if (bounds.width > 0 && bounds.height > this.TOP_BAR_HEIGHT) {
                tab.view.setBounds({
                    x: 0, y: this.TOP_BAR_HEIGHT,
                    width: bounds.width, height: bounds.height - this.TOP_BAR_HEIGHT
                });
            }
        }
    }
    
    updateNavigationState(view) {
        if (!view?.webContents || view.webContents.isDestroyed()) return;
        this.mainWindow.webContents.send('update-nav-state', {
            canGoBack: view.webContents.canGoBack(),
            canGoForward: view.webContents.canGoForward()
        });
    }

    getActiveWebContents() {
        const tab = this.tabs.get(this.activeTabId);
        return tab?.view?.webContents;
    }

    handleBrowserControl(action) {
        const wc = this.getActiveWebContents();
        if (!wc) return;
        if (action === 'back' && wc.canGoBack()) wc.goBack();
        if (action === 'forward' && wc.canGoForward()) wc.goForward();
        if (action === 'refresh') wc.reload();
    }
}
module.exports = TabManager;