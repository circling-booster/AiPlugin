const PLUGIN_ID = "spa-connection-tester";
const CLIENT_ID = "client-" + Math.random().toString(36).substr(2, 9);
let socket = null;

function connect() {
    if (socket) socket.close();
    
    // [Fixed] Use Injected Dynamic Port for WebSocket
    const apiPort = window.AIPLUGS_API_PORT || 5000;
    
    socket = new WebSocket(`ws://localhost:${apiPort}/ws/${PLUGIN_ID}/${CLIENT_ID}`);
    socket.onopen = () => console.log(`[SPA] Connected: ${window.location.href}`);
    socket.onclose = () => console.log("[SPA] Disconnected");
}

// 초기 연결
connect();

// [Task 4] SPA Navigation Logic
// AiPlugs Core가 주입하는 표준 이벤트 리스닝
window.addEventListener('aiplugs:navigate', () => {
    console.log("[SPA] Navigation detected! Reconnecting...");
    setTimeout(connect, 500); // DOM 안정화 대기 후 재연결
});