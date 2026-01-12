const apiPortEl = document.getElementById('api-port');
const proxyPortEl = document.getElementById('proxy-port');
const urlBar = document.getElementById('url-bar');
const lastLogEl = document.getElementById('last-log');
const logOverlay = document.getElementById('log-overlay');

// 1. Status Initialization
window.api.getStatus().then(status => {
    apiPortEl.innerText = status.api;
    proxyPortEl.innerText = status.proxy;
});

// 2. Log Handling
window.api.onLog(msg => {
    // 하단 상태바 업데이트
    lastLogEl.innerText = msg;
    if (msg.includes('ERR')) lastLogEl.style.color = '#ff6b6b';
    else lastLogEl.style.color = '#ccc';

    // 상세 로그창에 추가
    const div = document.createElement('div');
    div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
    if (msg.includes('ERR')) div.className = 'log-err';
    logOverlay.appendChild(div);
    logOverlay.scrollTop = logOverlay.scrollHeight;
});

// 3. Browser Controls
document.getElementById('btn-go').addEventListener('click', () => {
    const url = urlBar.value.trim();
    if(url) window.api.navigateTo(url);
});

urlBar.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        const url = urlBar.value.trim();
        if(url) window.api.navigateTo(url);
    }
});

document.getElementById('btn-back').addEventListener('click', () => window.api.control('back'));
document.getElementById('btn-forward').addEventListener('click', () => window.api.control('forward'));
document.getElementById('btn-refresh').addEventListener('click', () => window.api.control('refresh'));

// 4. URL/Title Sync from Main Process
window.api.onUpdateUrl((url) => {
    urlBar.value = url;
});

window.api.onUpdateTitle((title) => {
    document.title = `${title} - AiPlugs Browser`;
});

// 5. Toggle Logs
document.getElementById('btn-toggle-log').addEventListener('click', () => {
    if (logOverlay.style.display === 'block') {
        logOverlay.style.display = 'none';
    } else {
        logOverlay.style.display = 'block';
    }
});