const logDiv = document.getElementById('logs');
const apiPortEl = document.getElementById('api-port');
const proxyPortEl = document.getElementById('proxy-port');

window.api.getStatus().then(status => {
    apiPortEl.innerText = status.api;
    proxyPortEl.innerText = status.proxy;
});

window.api.onLog(msg => {
    const div = document.createElement('div');
    div.innerText = `[${new Date().toLocaleTimeString()}] ${msg}`;
    if (msg.includes('ERR')) div.className = 'log-err';
    logDiv.appendChild(div);
    logDiv.scrollTop = logDiv.scrollHeight;
});

document.getElementById('cert-btn').addEventListener('click', async () => {
    const res = await window.api.installCert();
    alert(res.message);
});