import time
import os

# [Task 3] Verification
# 이 로그와 3초 딜레이는 앱 시작 시점이 아니라, 버튼을 클릭했을 때 발생해야 함.
print(f"[HeavyMath] Initializing PID {os.getpid()}... (Wait 3s)")
time.sleep(3)
print("[HeavyMath] Ready.")

def run(payload):
    return {"result": 42}