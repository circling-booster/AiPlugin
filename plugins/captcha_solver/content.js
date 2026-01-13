(function () {
    /**
     * AI 엔진에 캡차 해독을 요청하는 함수
     */
    async function solveCaptcha(imageBase64, modelId = "MODEL_MELON") {
        const baseUrl = window.__AI_API_BASE_URL__;
        if (!baseUrl) {
            console.error("AI API URL missing");
            return { status: "error", message: "AI API URL missing" };
        }

        try {
            const res = await fetch(`${baseUrl}/v1/inference/captcha_solver/solve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    payload: {
                        model_id: modelId,
                        image: imageBase64
                    }
                })
            });
            return await res.json();
        } catch (e) {
            console.error("Solver Error:", e);
            return { status: "error", message: e.toString() };
        }
    }

    /**
     * 화면에 컨트롤 버튼과 결과 레이어를 생성하는 함수
     */
    function initOverlayUI() {
        // 이미 UI가 존재하면 생성하지 않음
        if (document.getElementById('captcha-solver-btn')) return;

        // 1. 실행 버튼 생성
        const btn = document.createElement('button');
        btn.id = 'captcha-solver-btn';
        btn.innerText = 'CAPTCHA 풀기';
        btn.style.cssText = `
            position: fixed;
            top: 10px;
            right: 10px;
            z-index: 99999;
            padding: 8px 15px;
            background-color: #00d344;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            font-size: 14px;
        `;

        // 2. 결과 표시 레이어 생성
        const resultLayer = document.createElement('div');
        resultLayer.id = 'captcha-result-layer';
        resultLayer.style.cssText = `
            position: fixed;
            top: 50px;
            right: 10px;
            z-index: 99999;
            padding: 10px;
            background-color: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: none;
            max-width: 300px;
            word-wrap: break-word;
            font-family: monospace;
            font-size: 12px;
            color: #333;
        `;

        // 3. 버튼 클릭 이벤트 핸들러
        btn.onclick = async () => {
            const captchaImg = document.getElementById('CaptchaImg');

            // 결과 레이어 초기화 및 표시
            resultLayer.style.display = 'block';
            resultLayer.innerText = "분석 중...";

            if (!captchaImg) {
                resultLayer.innerText = "오류: #CaptchaImg 요소를 찾을 수 없습니다.";
                return;
            }

            const src = captchaImg.src;
            if (!src) {
                resultLayer.innerText = "오류: 이미지 소스(src)가 비어있습니다.";
                return;
            }

            // 추론 요청
            const result = await solveCaptcha(src);

            // 결과 표시 (JSON 형태를 보기 좋게 출력)
            resultLayer.innerText = JSON.stringify(result, null, 2);
        };

        document.body.appendChild(btn);
        document.body.appendChild(resultLayer);
    }

    // 전역 객체에 함수 등록 (필요 시 외부 호출용)
    window.solveCaptcha = solveCaptcha;

    // 페이지 로드 완료 시 UI 초기화
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initOverlayUI);
    } else {
        initOverlayUI();
    }

    console.log("[CaptchaSolver] SOA Client & UI Ready");
})(); 