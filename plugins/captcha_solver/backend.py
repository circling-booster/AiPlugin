import os
import sys
import base64
import io

# [Dependency Guard]
try:
    import torch
    import torchvision.transforms as transforms
    from PIL import Image
    HAS_TORCH = True
except ImportError:
    print("[Backend] Warning: Torch/Pillow not found. Running in Dummy Mode.", file=sys.stderr)
    HAS_TORCH = False

MODEL_CONFIGS = {"width": 200, "height": 50}

class ModelManager:
    _model = None
    _device = None

    @classmethod
    def get_model(cls):
        if not HAS_TORCH:
            return None
            
        if cls._model is not None:
            return cls._model

        model_path = os.getenv("MELON_MODEL_PATH")
        # 모델 파일이 없으면 더미 모드로 전환
        if not model_path or not os.path.exists(model_path):
            print(f"[Backend] Model file not found at {model_path}. Using Dummy Mode.")
            return None

        cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"[Backend] Loading model from: {model_path}")
        
        try:
            # 안전 로딩 시도
            loaded = torch.load(model_path, map_location=cls._device)
            # 만약 state_dict라면 Architecture가 필요하지만, 여기서는 전체 모델이라 가정
            if isinstance(loaded, dict):
                raise ValueError("StateDict loaded but Architecture missing")
            
            cls._model = loaded
            cls._model.to(cls._device)
            cls._model.eval()
            print("[Backend] Model loaded successfully.")
        except Exception as e:
            print(f"[Backend] Load Failed: {e}. Fallback to Dummy.")
            cls._model = None
            
        return cls._model

def run(payload: dict):
    """
    Main Entry Point called by WorkerManager
    """
    try:
        image_data = payload.get("image")
        if not image_data:
            return {"status": "error", "message": "No image data"}

        # Base64 Decoding
        if "," in image_data:
            image_data = image_data.split(",")[1]
        
        # --- Logic Branch ---
        model = ModelManager.get_model()

        # A. 실제 모델 추론 (Torch 사용 가능 & 모델 로드 성공 시)
        if HAS_TORCH and model:
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            
            transform = transforms.Compose([
                transforms.Resize((MODEL_CONFIGS['height'], MODEL_CONFIGS['width'])),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
            ])
            
            tensor = transform(image).unsqueeze(0).to(ModelManager._device)
            
            with torch.no_grad():
                outputs = model(tensor)
                # 실제 디코딩 로직 (Argmax 등) 필요. 여기서는 예시.
                pred = str(torch.argmax(outputs, dim=1).item())
                return {"status": "success", "result": pred, "mode": "real"}

        # B. 더미 모드 (Fallback)
        else:
            # 이미지가 들어왔다는 것만 확인하고 임의값 반환
            return {
                "status": "success", 
                "result": "123456 (Dummy)", 
                "message": "Model not loaded, running in simulation mode"
            }

    except Exception as e:
        return {"status": "error", "message": str(e)}

# [Init] Warm-up
print("[Backend] Initializing...")
ModelManager.get_model()