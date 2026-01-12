const TabManager = {
    tabs: [],
    activeTabId: null,

    init() {
        this.tabList = document.getElementById('tab-list');
        this.bindEvents();
    },

    bindEvents() {
        document.getElementById('btn-new-tab').onclick = () => window.api.control('tab-create');
    },

    render() {
        this.tabList.innerHTML = '';
        this.tabs.forEach(tab => {
            const div = document.createElement('div');
            div.className = `tab ${tab.id === this.activeTabId ? 'active' : ''}`;
            
            div.onclick = (e) => {
                // [UX] 닫기 버튼과 탭 선택 영역 분리
                if(e.target.classList.contains('tab-close')) {
                    this.closeTab(tab.id);
                } else {
                    this.switchTab(tab.id);
                }
            };

            div.innerHTML = `
                <span class="tab-title">${tab.title || 'New Tab'}</span>
                <span class="tab-close">×</span>
            `;
            this.tabList.appendChild(div);
        });
    },

    addTab(id) {
        if (!this.tabs.find(t => t.id === id)) {
            this.tabs.push({ id, title: 'New Tab' });
            this.render();
        }
    },

    switchTab(id) {
        this.activeTabId = id;
        window.api.control('tab-switch', { tabId: id });
        this.render();
    },

    closeTab(id) {
        this.tabs = this.tabs.filter(t => t.id !== id);
        window.api.control('tab-close', { tabId: id });
        this.render();
    },

    updateTitle(id, title) {
        const tab = this.tabs.find(t => t.id === id);
        if (tab) {
            tab.title = title;
            this.render();
        }
    }
};

TabManager.init();

// --- IPC Connection ---
if (window.api) {
    window.api.onLog(msg => document.getElementById('last-log').innerText = msg);
    
    // Tab Events
    window.api.onTabCreated(({ tabId }) => TabManager.addTab(tabId));
    window.api.onTabSwitchConfirm(({ tabId }) => {
        TabManager.activeTabId = tabId;
        TabManager.render();
    });
    window.api.onTabState(({ tabId, title }) => TabManager.updateTitle(tabId, title));
    
    // Active Tab Filter (UI Level)
    window.api.onUpdateUrl(({ tabId, url }) => {
        if (tabId === TabManager.activeTabId) {
            document.getElementById('url-bar').value = url;
        }
    });
    
    window.api.onUpdateNavState((state) => {
        document.getElementById('btn-back').disabled = !state.canGoBack;
        document.getElementById('btn-forward').disabled = !state.canGoForward;
    });
}

// Global Nav Controls
document.getElementById('btn-go').onclick = () => {
    const url = document.getElementById('url-bar').value;
    window.api.navigateTo(url);
};
document.getElementById('url-bar').onkeypress = (e) => {
    if(e.key === 'Enter') window.api.navigateTo(e.target.value);
};
document.getElementById('btn-back').onclick = () => window.api.control('back');
document.getElementById('btn-forward').onclick = () => window.api.control('forward');
document.getElementById('btn-refresh').onclick = () => window.api.control('refresh');