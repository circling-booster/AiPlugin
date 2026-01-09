import os
import sys
import io
import base64
import time
import traceback
import torch
import torch.nn as nn
from torchvision import transforms
from PIL import Image

# ---------------------------------------------------------
# 1. Model & Inference Logic
# ---------------------------------------------------------

class CaptchaModel(nn.Module):
    """
    참조 리소스를 기반으로 한 모델 클래스.
    실제 .pt 파일 구조와 아키텍처가 일치해야 합니다.
    """
    def __init__(self, num_classes=36):
        super(CaptchaModel, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2, 2)
        )
        self.classifier = nn.Sequential(
            nn.Linear(64 * 16 * 64, 128), # Input 크기에 따라 조정 필요
            nn.ReLU(),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

class InferenceEngine:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.models = {}  # Cache for Lazy Loading
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
        # 전처리
        self.transform = transforms.Compose([
            transforms.Resize((64, 256)),
            transforms.ToTensor(),
        ])
        print(f"[Backend] Initialized on {self.device}")

    def load_model(self, model_type):
        """Lazy Loading Implementation"""
        if model_type in self.models:
            return self.models[model_type]

        filename = f"model_{model_type}.pt"
        model_path = os.path.join(self.base_path, "models", filename)

        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")

        print(f"[Backend] Loading model from {model_path}...")
        try:
            # 전체 모델 로드 (weights_only=False는 신뢰할 수 있는 로컬 파일이므로 허용)
            # 만약 state_dict만 저장된 파일이라면 CaptchaModel() 초기화 후 load_state_dict 사용 필요
            model = torch.load(model_path, map_location=self.device)
            
            # (Fallback: 딕셔너리 형태일 경우)
            if isinstance(model, dict):
                net = CaptchaModel()
                net.load_state_dict(model)
                model = net

            model.to(self.device)
            model.eval()
            self.models[model_type] = model
            return model
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {e}")

    def predict(self, image_b64, model_type):
        try:
            # 1. Base64 Decode
            if "," in image_b64:
                image_b64 = image_b64.split(",")[1]
            image_bytes = base64.b64decode(image_b64)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')

            # 2. Get Model (Lazy)
            model = self.load_model(model_type)

            # 3. Preprocess
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            # 4. Inference
            with torch.no_grad():
                output = model(input_tensor)
                # Simple Argmax Decoding (실제로는 CTC나 복잡한 디코딩 필요 가능)
                _, predicted = torch.max(output, 1)
                result_text = str(predicted.item()) # Demo Output

            return result_text
        except Exception as e:
            print(f"[Backend] Inference Error: {e}")
            raise e

# ---------------------------------------------------------
# 2. Worker Process Entry Point
# ---------------------------------------------------------

def run(ipc_queue):
    """
    API Server가 프로세스를 스폰한 후 호출하는 진입점 함수.
    무한 루프를 돌며 요청을 처리합니다.
    """
    print(f"[Backend] Worker Process Started. PID: {os.getpid()}")
    engine = InferenceEngine()

    while True:
        try:
            # 1. Wait for message (Blocking)
            message = ipc_queue.get()
            
            if message is None: # Stop Signal
                break

            # 2. Parse Message
            # Protocol: { 'action': str, 'payload': dict, 'reply_to': queue }
            action = message.get('action')
            payload = message.get('payload', {})
            reply_queue = message.get('reply_to')

            response = {"status": "error", "message": "Unknown action"}

            if action == 'predict':
                try:
                    img_data = payload.get('image')
                    m_type = payload.get('model_type', 'melon')
                    
                    text = engine.predict(img_data, m_type)
                    
                    response = {
                        "status": "success",
                        "result": text,
                        "model": m_type,
                        "mode": "local"
                    }
                except Exception as e:
                    traceback.print_exc()
                    response = {"status": "error", "message": str(e)}

            # 3. Send Result (if reply queue exists)
            if reply_queue:
                reply_queue.put(response)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[Backend] Critical Loop Error: {e}")
            time.sleep(1) # Prevent CPU spin on error