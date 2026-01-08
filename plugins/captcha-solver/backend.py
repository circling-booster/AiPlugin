# Asset Mocking Strategy
try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

class DummyModel:
    def __call__(self, x): return "DUMMY_TEXT"

def run(payload):
    if not HAS_TORCH: return "MOCKED_RESULT_NO_TORCH"
    # 실제 모델 로드 로직 생략 (Dummy 사용)
    model = DummyModel()
    return {"text": model(None)}