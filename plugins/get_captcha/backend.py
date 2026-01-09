import os
import json
import base64
import requests
import io

# 딥러닝 라이브러리 (로컬 모드용, 없어도 클라우드 모드는 동작 가능)
try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
    from PIL import Image
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# ---------------------------------------------------------
# [참조 리소스 내장] 추론 모델 및 전처리 로직
# ---------------------------------------------------------
class CaptchaModel(nn.Module if HAS_TORCH else object):
    def __init__(self, num_classes=36):
        if HAS_TORCH:
            super(CaptchaModel, self).__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 32, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2, 2),
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((1, num_classes))
            )

    def forward(self, x):
        x = self.features(x)
        return x.view(x.size(0), -1)

def preprocess_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        transform = transforms.Compose([
            transforms.Resize((64, 192)),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])
        return transform(image).unsqueeze(0)
    except Exception as e:
        print(f"Preprocessing Error: {e}")
        return None

# ---------------------------------------------------------
# [플러그인 메인] Plugin Loader 호환 클래스
# ---------------------------------------------------------
class Plugin:
    def __init__(self, base_path):
        """
        플러그인 초기화
        :param base_path: 플러그인 디렉토리 경로 (api_server/plugin_loader에서 주입)
        """
        self.base_path = base_path
        self.config = self._load_config()
        self.model = None
        self.device = None
        
        # 클라우드 미사용 시 로컬 모델 로드 시도
        if not self.config.get("use_cloud", False) and HAS_TORCH:
            self._load_local_model()

    def _load_config(self):
        """manifest.json 로드"""
        config_path = os.path.join(self.base_path, "manifest.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("config", {})
        except Exception as e:
            print(f"[GetCaptcha] Config load error: {e}")
            return {}

    def _load_local_model(self):
        """로컬 PyTorch 모델 로드"""
        try:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model = CaptchaModel()
            
            model_path = os.path.join(self.base_path, self.config.get("model_file", "model.pth"))
            if os.path.exists(model_path):
                self.model.load_state_dict(torch.load(model_path, map_location=self.device))
                self.model.to(self.device)
                self.model.eval()
                print("[GetCaptcha] Local model loaded.")
            else:
                print(f"[GetCaptcha] Warning: Model file not found at {model_path}")
        except Exception as e:
            print(f"[GetCaptcha] Model init error: {e}")

    def handle_action(self, action, payload):
        """
        API Server의 동적 라우팅에 의해 호출되는 진입점
        :param action: URL의 {action} 부분 (예: 'solve')
        :param payload: Request Body JSON
        """
        if action == "solve":
            return self._solve_captcha(payload.get("image"))
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def _solve_captcha(self, image_b64):
        if not image_b64:
            return {"status": "error", "message": "No image data"}

        # Base64 헤더 제거 (data:image/png;base64,...)
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]

        # 1. Cloud Mode
        if self.config.get("use_cloud", False):
            return self._infer_cloud(image_b64)
        # 2. Local Mode
        else:
            return self._infer_local(image_b64)

    def _infer_cloud(self, image_b64):
        url = self.config.get("cloud_url", "http://localhost:8001/predict")
        try:
            # 클라우드 서버로 JSON 전송
            resp = requests.post(url, json={"image": image_b64}, timeout=5)
            if resp.status_code == 200:
                return resp.json() 
            else:
                return {"status": "error", "message": f"Cloud Error: {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _infer_local(self, image_b64):
        if not HAS_TORCH:
            return {"status": "error", "message": "PyTorch not installed"}
        if self.model is None:
            return {"status": "error", "message": "Model not loaded"}
        
        try:
            image_bytes = base64.b64decode(image_b64)
            input_tensor = preprocess_image(image_bytes)
            
            if input_tensor is None:
                return {"status": "error", "message": "Preprocessing failed"}
            
            input_tensor = input_tensor.to(self.device)
            
            with torch.no_grad():
                _ = self.model(input_tensor)
                # 실제 디코딩 로직 (여기서는 더미 결과 반환)
                result_text = "TEST_RESULT" 
                
            return {"status": "success", "result": result_text}
        except Exception as e:
            return {"status": "error", "message": f"Inference Error: {str(e)}"}