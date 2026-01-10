import os
import sys

# Core가 자동으로 다운로드하고 경로를 주입해 줍니다.
MODEL_PATH = os.getenv("CAPTCHA_MODEL_PATH")

print(f"[HeavyMath] Initializing...")

if MODEL_PATH and os.path.exists(MODEL_PATH):
    print(f"[HeavyMath] Loading model from: {MODEL_PATH}")
    # model = torch.load(MODEL_PATH)
else:
    # 다운로드가 실패했거나 정의되지 않은 경우
    print("[HeavyMath] CRITICAL: Model path not found!", file=sys.stderr)

def run(payload):
    return {"result": 42}