// plugins/get_captcha/content.js

(function() {
    console.log("[AiPlugin] Get Captcha v2 Loaded");

    // 1. UI 컨테이너 생성 (Shadow DOM 사용)
    const container = document.createElement('div');
    container.id = 'ai-plugin-container';
    container.style.position = 'fixed';
    container.style.bottom = '20px';
    container.style.right = '20px';
    container.style.zIndex = '99999';

    const shadow = container.attachShadow({ mode: 'open' });

    // 2. 스타일 및 버튼 생성
    const style = document.createElement('style');
    style.textContent = `
        button {
            padding: 12px 24px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: background-color 0.3s;
        }
        button:hover { background-color: #45a049; }
        button:disabled { background-color: #ccc; cursor: not-allowed; }
    `;

    const button = document.createElement('button');
    button.innerText = 'Send Captcha';
    
    shadow.appendChild(style);
    shadow.appendChild(button);
    document.body.appendChild(container);

    // 3. 이벤트 핸들러
    button.addEventListener('click', async () => {
        const imgElement = document.querySelector('#CaptchaImg');
        
        if (!imgElement) {
            showToast('캡차 이미지를 찾을 수 없습니다.', 'error');
            return;
        }

        const src = imgElement.src;
        if (!src || !src.startsWith('data:image')) {
            showToast('Base64 이미지가 아닙니다.', 'error');
            return;
        }

        // 로딩 상태 표시
        button.innerText = 'Analyzing...';
        button.disabled = true;

        try {
            // [개선된 엔드포인트] 동적 라우팅 경로 호출
            const response = await fetch('http://localhost:8000/api/plugin/get_captcha/solve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: src })
            });

            const data = await response.json();

            if (data.status === 'success') {
                showToast(`결과: ${data.result}`, 'success');
                console.log(`[AiPlugin] Result: ${data.result}`);
                // 필요 시 입력 필드 자동 채우기 로직 추가
                // const input = document.querySelector('#captcha_input');
                // if(input) input.value = data.result;
            } else {
                showToast(`오류: ${data.message}`, 'error');
            }
        } catch (e) {
            console.error(e);
            showToast('서버 통신 실패', 'error');
        } finally {
            button.innerText = 'Send Captcha';
            button.disabled = false;
        }
    });

    // 알림 메시지 (Toast)
    function showToast(message, type) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 20px;
            border-radius: 5px;
            color: #fff;
            z-index: 100000;
            font-size: 14px;
            background-color: ${type === 'error' ? '#f44336' : '#333'};
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        `;

        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }
})();