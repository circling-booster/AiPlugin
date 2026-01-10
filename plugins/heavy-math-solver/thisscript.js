console.log("[HeavyMath] Script Loaded");

function init() {
    // 중복 실행 방지
    if (document.getElementById("heavy-calc-btn")) return;

    const btn = document.createElement("button");
    btn.id = "heavy-calc-btn"; // ID 부여
    btn.innerText = "Heavy Calc";
    btn.style.cssText = "position:fixed; top:10px; right:10px; z-index:9999;";
    
    // 이제 안전하게 body에 접근 가능
    document.body.appendChild(btn);

    btn.onclick = async () => {
        console.log("Requesting Calculation (Triggers Lazy Load)...");
        
        // [Fixed] Use Injected Dynamic Port
        const apiPort = window.AIPLUGS_API_PORT || 5000;
        const baseUrl = `http://localhost:${apiPort}`;

        try {
            const res = await fetch(`${baseUrl}/v1/inference/heavy-math-solver/solve`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ payload: { num: 100 } })
            });
            const json = await res.json();
            console.log(json);
            alert(`Result: ${json.result || json.message}`);
        } catch (e) {
            console.error(e);
            alert("Error connecting to Local Core");
        }
    };
}

// [핵심 수정] DOM이 준비될 때까지 대기
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
} else {
    init();
}