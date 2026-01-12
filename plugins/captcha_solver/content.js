console.log("[CaptchaSolver] Content Script Loaded (v2.4 - Melon Optimized)");

async function extractImageBase64(imgEl) {
    const src = imgEl.src;
    if (src.startsWith("data:image")) {
        return src;
    }

    try {
        console.log(`[CaptchaSolver] Fetching image from URL: ${src}`);
        const response = await fetch(src);
        if (!response.ok) throw new Error(`Network response was not ok: ${response.status}`);
        
        const blob = await response.blob();
        
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    } catch (e) {
        console.error("[CaptchaSolver] Image fetch failed:", e);
        try {
            const canvas = document.createElement("canvas");
            canvas.width = imgEl.naturalWidth || 200;
            canvas.height = imgEl.naturalHeight || 50;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(imgEl, 0, 0);
            return canvas.toDataURL("image/png");
        } catch (canvasErr) {
            throw new Error("이미지 추출 실패 (CORS 또는 네트워크 오류)");
        }
    }
}

function init() {
    if (document.getElementById("aiplugs-cap-btn")) return;

    const btn = document.createElement("button");
    btn.id = "aiplugs-cap-btn";
    btn.innerText = "🤖 캡차 풀기";
    btn.style.cssText = `
        position: fixed; top: 15px; right: 15px; z-index: 2147483647;
        padding: 8px 16px; background: #00d369; color: #1a1a1a;
        border: none; border-radius: 20px; cursor: pointer;
        font-family: 'Malgun Gothic', sans-serif; font-weight: 800; font-size: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3); transition: transform 0.1s;
    `;
    
    // 호버 효과
    btn.onmouseover = () => btn.style.transform = "scale(1.05)";
    btn.onmouseout = () => btn.style.transform = "scale(1)";

    document.body.appendChild(btn);

    btn.onclick = async () => {
        // 1. 이미지 요소 찾기 (멜론/인터파크 등 대응)
        let imgEl = document.getElementById("captchaImg");
        if (!imgEl) imgEl = document.querySelector("#captcha");
        if (!imgEl) imgEl = document.querySelector("img[src*='captcha']");
        if (!imgEl) imgEl = document.querySelector("img[alt*='captcha']");

        if (!imgEl) {
            alert("❌ 캡차 이미지를 찾을 수 없습니다.");
            return;
        }

        const originText = btn.innerText;
        btn.innerText = "⏳ 계산 중...";
        btn.disabled = true;
        btn.style.background = "#555";
        btn.style.color = "#fff";

        try {
            // 2. 이미지 데이터 추출
            const base64Data = await extractImageBase64(imgEl);

            // 3. 백엔드 요청
            const apiPort = window.AIPLUGS_API_PORT || 5000;
            const endpoint = `http://localhost:${apiPort}/v1/inference/captcha_solver/solve`;

            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    payload: { 
                        image: base64Data,
                        // [중요] 멜론 모델 사용을 명시 (manifest key와 일치)
                        model_id: "MODEL_MELON" 
                    } 
                })
            });

            const json = await response.json();
            console.log("[CaptchaSolver] Result:", json);

            if (json.status === "error") {
                alert(`오류: ${json.message}`);
            } else {
                const resultText = json.predicted_text;
                // [UX] 결과 자동 입력
                const inputEl = document.getElementById("label_text") || 
                                document.querySelector("input[name*='captcha']") ||
                                document.querySelector("input[type='text']");
                
                if (inputEl) {
                    inputEl.value = resultText;
                    inputEl.focus();
                    
                    // 일부 사이트(React/Vue)는 input 이벤트가 발생해야 인식하므로 이벤트 강제 실행
                    inputEl.dispatchEvent(new Event('input', { bubbles: true }));
                    inputEl.dispatchEvent(new Event('change', { bubbles: true }));
                    
                    btn.innerText = `✅ ${resultText}`;
                } else {
                    alert(`결과: ${resultText}`);
                }
                
                // 3초 후 버튼 원복
                setTimeout(() => {
                    btn.innerText = originText;
                    btn.disabled = false;
                    btn.style.background = "#00d369";
                    btn.style.color = "#1a1a1a";
                }, 3000);
            }

        } catch (e) {
            console.error(e);
            alert(`실패: ${e.message}`);
            btn.innerText = "❌ 실패";
            setTimeout(() => {
                btn.innerText = originText;
                btn.disabled = false;
                btn.style.background = "#00d369";
            }, 2000);
        }
    };
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}