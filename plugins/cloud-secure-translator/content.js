console.log("[Translator] Script Loaded (Web Mode)");

function init() {
    // 중복 생성 방지
    if (document.getElementById("aiplugs-trans-box")) return;

    const box = document.createElement("div");
    box.id = "aiplugs-trans-box";
    box.style.cssText = "position:fixed; bottom:20px; left:20px; background:white; padding:10px; border:1px solid #ccc; z-index:9999; box-shadow: 0 2px 5px rgba(0,0,0,0.2); border-radius: 8px;";
    
    box.innerHTML = `
        <h4 style="margin:0 0 10px 0;">☁️ Secure Translator</h4>
        <input id="trans-input" type="text" placeholder="Text to translate" value="Hello World" style="padding:5px; width:200px;">
        <button id="trans-btn" style="padding:5px; cursor:pointer;">Translate</button>
        <div id="trans-result" style="margin-top:10px; color:blue; font-weight:bold; min-height:20px;"></div>
    `;
    
    // 안전하게 body에 추가
    document.body.appendChild(box);

    // 이벤트 핸들러 등록
    document.getElementById("trans-btn").onclick = async () => {
        const text = document.getElementById("trans-input").value;
        const resultDiv = document.getElementById("trans-result");
        
        resultDiv.innerText = "Requesting Cloud...";
        
        try {
            // Web Mode 요청 (Local Core -> Cloud Server Relay)
            const res = await fetch("http://localhost:5000/v1/inference/cloud-secure-translator/translate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ payload: { text: text } })
            });
            
            const json = await res.json();
            console.log("[Translator] Response:", json);
            resultDiv.innerText = json.data || json.message;
        } catch (e) {
            console.error("[Translator] Error:", e);
            resultDiv.innerText = "Error (Check Console)";
        }
    };
}

// [핵심 수정] DOM이 준비될 때까지 대기
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}