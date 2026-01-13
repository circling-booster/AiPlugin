(function() {
    async function solveCaptcha(imageBase64, modelId="MODEL_MELON") {
        const baseUrl = window.__AI_API_BASE_URL__;
        if (!baseUrl) {
            console.error("AI API URL missing");
            return null;
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
    window.solveCaptcha = solveCaptcha;
    console.log("[CaptchaSolver] SOA Client Ready");
})();