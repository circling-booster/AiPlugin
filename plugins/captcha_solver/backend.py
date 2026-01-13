import os
import sys
import base64
import io
import time
import json
import logging
import traceback
import string

# [Dependency Guard]
try:
    import torch
    import torch.nn as nn
    import numpy as np
    from PIL import Image
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

logger = logging.getLogger("CaptchaBackend")

# ==============================================================================
# [Configuration] 모델 설정 (model_manager.py 기반)
# ==============================================================================

# 알파벳 대문자 (26개)
ALPHABETS = string.ascii_uppercase
NUM_CLASSES = len(ALPHABETS) # 26
BLANK_LABEL = 26             # 0~25는 문자, 26은 Blank
IDX_TO_CHAR = {i: c for i, c in enumerate(ALPHABETS)}

# 지원 모델 및 스펙 (model_manager.py 참조)
# Manifest의 key와 매핑될 내부 설정입니다.
SUPPORTED_MODELS = {
    "MODEL_MELON": {"width": 230, "height": 70}, # [중요] 해상도 230x70
    "MODEL_NOL":   {"width": 210, "height": 70}  # 추후 도입 예정
}

# ==============================================================================
# [Model Architecture] CRNN 클래스 이식 (model_manager.py 원본)
# ==============================================================================

class CRNN(nn.Module):
    """CNN-RNN-CTC 기반 캡차 인식 모델"""

    def __init__(self, img_h, num_classes, rnn_hidden_size=256, rnn_layers=2, rnn_dropout=0.3):
        super().__init__()

        self.cnn = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2, 2),

            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.MaxPool2d((2, 2), (2, 2)), # stride (2,2) 확인
        )

        # CNN 출력 높이 계산: 70 -> 35 -> 17 -> 8 (img_h // 8 근사치)
        # model_manager.py 로직: conv_output_h = img_h // 8
        conv_output_h = img_h // 8
        self.rnn_input_size = 128 * conv_output_h

        self.rnn = nn.LSTM(
            input_size=self.rnn_input_size,
            hidden_size=rnn_hidden_size,
            num_layers=rnn_layers,
            dropout=rnn_dropout,
            bidirectional=True,
            batch_first=True,
        )

        # num_classes + 1 (Blank 포함)
        self.fc = nn.Linear(rnn_hidden_size * 2, num_classes + 1)

    def forward(self, x):
        # x shape: (Batch, Channel, Height, Width)
        x = self.cnn(x)
        b, c, h, w = x.size()
        
        # (Batch, Channel, Height, Width) -> (Batch, Width, Channel, Height) -> (Batch, Width, Features)
        x = x.permute(0, 3, 1, 2)
        x = x.contiguous().view(b, w, c * h)
        
        x, _ = self.rnn(x)
        x = self.fc(x)
        
        # (Batch, Seq, Class) -> (Seq, Batch, Class) 로 변환하여 리턴
        # inference.py의 디코딩 로직이 (Seq, Batch)를 기대하므로 이 순서 중요
        x = x.permute(1, 0, 2)
        return x

# ==============================================================================
# [Core Logic] Model Manager & Inference (inference.py 기반)
# ==============================================================================

class ModelManager:
    _models = {}
    _device = None

    @classmethod
    def get_device(cls):
        if cls._device is None:
            cls._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return cls._device

    @classmethod
    def get_model(cls, model_key):
        """
        Manifest Key(예: MODEL_MELON)를 통해 환경변수 경로를 찾고 모델을 로드
        """
        if not HAS_DEPS:
            raise ImportError("Backend dependencies missing")

        if model_key in cls._models:
            return cls._models[model_key]

        # 1. 환경변수에서 파일 경로 조회
        model_path = os.getenv(model_key)
        
        # [Fallback] 로컬 디버깅용 (환경변수 없을 때)
        if not model_path:
             # 사용자의 파일 경로 구조 추정
             default_path = r"C:\Users\sungb\Documents\GitHub\AiPlugin\models\model_melon.pt"
             if os.path.exists(default_path):
                 logger.warning(f"Env var '{model_key}' missing. Using fallback: {default_path}")
                 model_path = default_path

        if not model_path or not os.path.exists(model_path):
             raise FileNotFoundError(f"Model file not found for key: {model_key}")

        # 2. 모델 설정 조회
        # 만약 정의되지 않은 키라면 기본값(MELON) 사용하거나 에러 처리
        config_key = model_key if model_key in SUPPORTED_MODELS else "MODEL_MELON"
        config = SUPPORTED_MODELS[config_key]
        
        device = cls.get_device()
        logger.info(f"Loading '{model_key}' (Spec: {config}) from {model_path}...")

        try:
            # [핵심] 아키텍처 생성 (높이 70, 클래스 26)
            model = CRNN(img_h=config["height"], num_classes=NUM_CLASSES)
            model.to(device)
            
            # [핵심] 가중치 로드 (state_dict)
            state_dict = torch.load(model_path, map_location=device)
            model.load_state_dict(state_dict)
            model.eval()
            
            cls._models[model_key] = model
            logger.info(f"Model '{model_key}' loaded successfully.")
            return model
            
        except Exception as e:
            logger.error(f"Failed to load model '{model_key}': {e}")
            raise

def preprocess_image(image_bytes, config) -> torch.Tensor:
    """inference.py의 로직 이식"""
    try:
        width = config["width"]
        height = config["height"]

        if isinstance(image_bytes, str):
            # Base64 디코딩 (혹시 문자열로 넘어왔을 경우)
            if "base64," in image_bytes:
                image_bytes = image_bytes.split("base64,")[1]
            image_bytes = base64.b64decode(image_bytes)

        image = Image.open(io.BytesIO(image_bytes)).convert("L")
        
        # [중요] BILINEAR 리사이징
        image = image.resize((width, height), Image.BILINEAR)

        image_np = np.array(image, dtype=np.float32)
        image_np = image_np / 255.0

        # (H, W) -> (1, 1, H, W)
        image_tensor = torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0)
        return image_tensor

    except Exception as e:
        logger.error(f"Preprocessing failed: {e}")
        raise

def ctc_decode(predictions):
    """inference.py의 로직 이식"""
    # predictions: (Seq, Batch, Class) -> Argmax -> (Seq, Batch)
    preds = predictions.argmax(dim=2)
    
    # (Seq, Batch) -> (Batch, Seq) 변환
    preds = preds.cpu().numpy().transpose(1, 0)

    decoded = []
    for p in preds:
        prev = -1
        seq = []
        for idx in p:
            if idx != prev and idx != BLANK_LABEL:
                # 인덱스가 유효한 문자인지 확인 (0~25)
                if idx in IDX_TO_CHAR: 
                    seq.append(idx) # IDX_TO_CHAR가 0-based key면 그대로 사용
                elif idx < len(ALPHABETS): # 만약 딕셔너리 키 문제라면 안전장치
                    seq.append(idx)
            prev = idx
        
        # 인덱스를 문자로 변환
        decoded.append("".join([ALPHABETS[i] for i in seq]))
        
    return decoded

def infer(image_tensor: torch.Tensor, model, device):
    """inference.py의 로직 이식"""
    try:
        image_tensor = image_tensor.to(device)
        with torch.no_grad():
            logits = model(image_tensor)
            predictions = ctc_decode(logits)
        return predictions if predictions else [""]
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise

# ==============================================================================
# [Entry Point]
# ==============================================================================

def run(payload: dict):
    start_time = time.time()
    
    if not HAS_DEPS:
        return {"status": "error", "message": "Dependencies missing (torch/numpy/PIL)"}

    try:
        image_data = payload.get("image")
        # 프론트엔드가 요청한 키 (예: MODEL_MELON)
        model_key = payload.get("model_id", "MODEL_MELON") 

        if not image_data:
            return {"status": "error", "message": "No image data"}

        # 지원 모델 확인 및 Config 로드
        if model_key not in SUPPORTED_MODELS:
            # 알 수 없는 키면 기본값인 MELON으로 Fallback 하거나 에러 리턴
            # 여기서는 안전하게 MELON Config 사용
            logger.warning(f"Unknown model_id '{model_key}'. Using MODEL_MELON config.")
            config = SUPPORTED_MODELS["MODEL_MELON"]
        else:
            config = SUPPORTED_MODELS[model_key]

        # 1. 모델 로드
        model = ModelManager.get_model(model_key)
        device = ModelManager.get_device()
        
        # 2. 전처리
        image_tensor = preprocess_image(image_data, config)

        # 3. 추론
        predicted_texts = infer(image_tensor, model, device)
        predicted_text = predicted_texts[0] if predicted_texts else ""

        # 4. 신뢰도 계산 (Max Probability)
        with torch.no_grad():
            image_tensor_device = image_tensor.to(device)
            logits = model(image_tensor_device)
            # Logits: (Seq, Batch, Class) -> Softmax -> Max over class -> Max over sequence
            # (단순화를 위해 시퀀스 전체 중 가장 높은 확률을 신뢰도로 사용)
            probs = torch.softmax(logits, dim=2)
            confidence = float(probs.max().item())

        processing_time_ms = (time.time() - start_time) * 1000
        
        logger.info(f"[{model_key}] Result: {predicted_text} (Conf: {confidence:.4f})")

        return {
            "status": "success",
            "predicted_text": predicted_text,
            "model_type": model_key,
            "confidence": round(confidence, 4),
            "processing_time_ms": round(processing_time_ms, 1)
        }

    except Exception as e:
        err_msg = f"Runtime Error: {str(e)}\n{traceback.format_exc()}"
        logger.error(err_msg)
        return {"status": "error", "message": str(e)}

# Warm-up
if HAS_DEPS:
    try:
        # 프로세스 시작 시 멜론 모델 로드 시도
        ModelManager.get_model("MODEL_MELON")
    except Exception:
        pass