console.log("[CaptchaSolver] Content Script Loaded");

function init() {
    if (document.getElementById("aiplugs-cap-btn")) return;

    const btn = document.createElement("button");
    btn.id = "aiplugs-cap-btn";
    btn.innerText = "🤖 Captcha 추론";
    btn.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 99999;
        padding: 10px 20px; background: #28a745; color: white;
        border: none; border-radius: 5px; cursor: pointer;
        font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    `;
    
    document.body.appendChild(btn);

    btn.onclick = async () => {
        const imgEl = document.getElementById("captchaImg");
        if (!imgEl) {
            alert("❌ 캡차 이미지(#captchaImg)를 찾을 수 없습니다.");
            return;
        }

        const base64Src = imgEl.src;
        if (!base64Src.startsWith("data:image")) {
            alert("⚠️ 이미지가 Base64 형식이 아닙니다. (src 확인 필요)");
            return;
        }

        const originText = btn.innerText;
        btn.innerText = "⏳ 추론 중...";
        btn.disabled = true;

        try {
            // [Core] Injected Dynamic Port
            const apiPort = window.AIPLUGS_API_PORT || 5000;
            const endpoint = `http://localhost:${apiPort}/v1/inference/captcha_solver/solve`;

            console.log(`[CaptchaSolver] Sending request to ${endpoint}`);

            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    payload: { 
                        image: base64Src 
                    } 
                })
            });

            const json = await response.json();
            console.log("[CaptchaSolver] Result:", json);

            if (json.status === "error") {
                alert(`에러 발생: ${json.message}`);
            } else {
                alert(`✅ 추론 결과: ${json.result}`);
            }

        } catch (e) {
            console.error(e);
            alert("통신 오류 발생 (Console 참조)");
        } finally {
            btn.innerText = originText;
            btn.disabled = false;
        }
    };
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}