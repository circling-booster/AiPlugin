(function () {
  console.log("[GetCaptcha] Content script loaded.");

  // Shadow DOM 컨테이너 생성 (UI 격리)
  const host = document.createElement("div");
  host.id = "ai-plugin-captcha-host";
  host.style.position = "fixed";
  host.style.bottom = "20px";
  host.style.right = "20px";
  host.style.zIndex = "2147483647"; // Max z-index
  document.body.appendChild(host);

  const shadow = host.attachShadow({ mode: "open" });

  // 스타일 정의
  const style = document.createElement("style");
  style.textContent = `
    .panel {
      background: #222;
      color: #fff;
      border: 1px solid #444;
      padding: 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      font-family: 'Segoe UI', sans-serif;
      width: 220px;
    }
    .title {
      font-size: 14px;
      font-weight: bold;
      margin-bottom: 12px;
      display: block;
      border-bottom: 1px solid #444;
      padding-bottom: 6px;
    }
    .row {
      margin-bottom: 10px;
      display: flex;
      align-items: center;
    }
    label {
      font-size: 13px;
      margin-right: 15px;
      cursor: pointer;
      display: flex;
      align-items: center;
    }
    input[type="radio"] {
      margin-right: 5px;
    }
    button {
      background: #007bff;
      color: white;
      border: none;
      padding: 10px;
      border-radius: 4px;
      cursor: pointer;
      width: 100%;
      font-weight: bold;
      transition: background 0.2s;
    }
    button:hover {
      background: #0056b3;
    }
    button:disabled {
      background: #555;
      cursor: not-allowed;
    }
    .status {
      margin-top: 10px;
      font-size: 12px;
      color: #aaa;
      text-align: center;
      min-height: 1.2em;
    }
  `;
  shadow.appendChild(style);

  // UI 렌더링
  const panel = document.createElement("div");
  panel.className = "panel";
  panel.innerHTML = `
    <span class="title">🔐 Captcha Solver v4</span>
    <div class="row">
      <label><input type="radio" name="model" value="melon" checked> Melon</label>
      <label><input type="radio" name="model" value="nol"> Nol</label>
    </div>
    <div class="row">
      <button id="btn-exec">Send Captcha</button>
    </div>
    <div class="status" id="status-text">Ready</div>
  `;
  shadow.appendChild(panel);

  const btnExec = panel.querySelector("#btn-exec");
  const statusText = panel.querySelector("#status-text");

  // 이벤트 핸들러
  btnExec.addEventListener("click", async () => {
    // 1. 이미지 추출
    const imgEl = document.querySelector("img#CaptchaImg");
    if (!imgEl) {
      statusText.textContent = "Error: Img not found";
      statusText.style.color = "#ff4444";
      return;
    }

    const src = imgEl.src;
    if (!src || !src.startsWith("data:image")) {
      statusText.textContent = "Error: Not Base64";
      statusText.style.color = "#ff4444";
      return;
    }

    // Base64 헤더 제거
    const base64Image = src.split(",")[1];

    // 2. 모델 선택
    const modelType = panel.querySelector('input[name="model"]:checked').value;

    // UI 업데이트
    btnExec.disabled = true;
    btnExec.textContent = "Analyzing...";
    statusText.textContent = `Using ${modelType} model...`;
    statusText.style.color = "#aaa";

    try {
      // 3. 백엔드 요청 (범용 라우팅 경로)
      const response = await fetch("http://127.0.0.1:5000/api/plugin/get_captcha/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image: base64Image,
          model_type: modelType
        })
      });

      const data = await response.json();

      if (data.status === "success" || data.result) {
        const result = data.result || data.text;
        statusText.textContent = `Result: ${result}`;
        statusText.style.color = "#00ff00";
        alert(`Captcha Result: ${result}`);
      } else {
        throw new Error(data.message || "Unknown error");
      }
    } catch (err) {
      console.error(err);
      statusText.textContent = "Failed";
      statusText.style.color = "#ff4444";
      alert("Error: " + err.message);
    } finally {
      btnExec.disabled = false;
      btnExec.textContent = "Send Captcha";
    }
  });
})();