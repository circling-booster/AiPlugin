import os
import sys
import io
import time
import base64
import string
import logging
import traceback
import concurrent.futures

# [CPU Optimization]
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

try:
    import torch
    import torch.nn as nn
    import numpy as np
    from PIL import Image
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False
    torch = None
    nn = None
    np = None
    Image = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
logger = logging.getLogger("AIEngine")

# ------------------------------------------------------------------------------
# [Model Configuration]
# ------------------------------------------------------------------------------
ALPHABETS = string.ascii_uppercase
NUM_CLASSES = len(ALPHABETS) # 26
BLANK_LABEL = 26
IDX_TO_CHAR = {i: c for i, c in enumerate(ALPHABETS)}

SUPPORTED_MODELS = {
    "MODEL_MELON": {"width": 230, "height": 70, "filename": "model_melon.pt"},
    "MODEL_NOL":   {"width": 210, "height": 70, "filename": "model_nol.pt"}
}

# ------------------------------------------------------------------------------
# [Model Architecture] (Ported from plugins/captcha_solver/backend.py)
# ------------------------------------------------------------------------------
if HAS_DEPS:
    class CRNN(nn.Module):
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
                nn.MaxPool2d((2, 2), (2, 2)),
            )
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
            self.fc = nn.Linear(rnn_hidden_size * 2, num_classes + 1)

        def forward(self, x):
            x = self.cnn(x)
            b, c, h, w = x.size()
            x = x.permute(0, 3, 1, 2)
            x = x.contiguous().view(b, w, c * h)
            x, _ = self.rnn(x)
            x = self.fc(x)
            x = x.permute(1, 0, 2)
            return x

# ------------------------------------------------------------------------------
# [Worker Process Logic]
# These functions run INSIDE the worker process.
# We use global variables here to CACHE the model within the worker.
# ------------------------------------------------------------------------------
_worker_models = {}
_worker_device = None

def _get_worker_device():
    global _worker_device
    if _worker_device is None and torch:
        _worker_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _worker_device

def _load_model_in_worker(model_key, model_dir):
    global _worker_models
    if model_key in _worker_models:
        return _worker_models[model_key]

    if not HAS_DEPS:
        raise ImportError("Torch dependencies missing in worker process")

    config = SUPPORTED_MODELS.get(model_key, SUPPORTED_MODELS["MODEL_MELON"])
    filename = config["filename"]
    
    # Path Resolution Priority:
    # 1. Environment Variable
    # 2. Provided Model Directory (plugins/captcha_solver)
    # 3. Models Subdirectory
    
    model_path = os.getenv(model_key)
    if not model_path:
        model_path = os.path.join(model_dir, filename)
    
    if not os.path.exists(model_path):
         # Try 'models' subdirectory
        model_path = os.path.join(model_dir, 'models', filename)

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    device = _get_worker_device()
    try:
        model = CRNN(img_h=config["height"], num_classes=NUM_CLASSES)
        model.to(device)
        state_dict = torch.load(model_path, map_location=device)
        model.load_state_dict(state_dict)
        model.eval()
        _worker_models[model_key] = model
        return model
    except Exception as e:
        logger.error(f"Worker Load Failed: {e}")
        raise

def _preprocess_in_worker(image_data, width, height):
    if isinstance(image_data, str):
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        image_data = base64.b64decode(image_data)
    
    image = Image.open(io.BytesIO(image_data)).convert("L")
    image = image.resize((width, height), Image.BILINEAR)
    image_np = np.array(image, dtype=np.float32) / 255.0
    return torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0)

def _inference_task(model_id, image_data, model_dir):
    """
    Entry point for the ProcessPoolExecutor worker.
    """
    start_time = time.time()
    try:
        target_model_key = model_id if model_id in SUPPORTED_MODELS else "MODEL_MELON"
        config = SUPPORTED_MODELS[target_model_key]
        
        # Load (Cached)
        model = _load_model_in_worker(target_model_key, model_dir)
        device = _get_worker_device()
        
        # Preprocess
        img_tensor = _preprocess_in_worker(image_data, config["width"], config["height"])
        img_tensor = img_tensor.to(device)
        
        # Infer
        with torch.no_grad():
            logits = model(img_tensor)
            
            # Decode
            preds = logits.argmax(dim=2).cpu().numpy().transpose(1, 0)
            decoded = []
            for p in preds:
                seq = []
                prev = -1
                for idx in p:
                    if idx != prev and idx != BLANK_LABEL:
                        if idx in IDX_TO_CHAR:
                            seq.append(IDX_TO_CHAR[idx])
                    prev = idx
                decoded.append("".join(seq))
            
            text = decoded[0] if decoded else ""
            
            # Confidence
            probs = torch.softmax(logits, dim=2)
            confidence = float(probs.max().item())

        processing_time = (time.time() - start_time) * 1000
        
        return {
            "status": "success",
            "predicted_text": text,
            "model_type": target_model_key,
            "confidence": round(confidence, 4),
            "processing_time_ms": round(processing_time, 1)
        }

    except Exception as e:
        return {"status": "error", "message": str(e), "trace": traceback.format_exc()}

# ------------------------------------------------------------------------------
# [Main Engine Class]
# ------------------------------------------------------------------------------
class AIEngine:
    def __init__(self):
        # Force 1 worker to prevent OOM
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
        
        # Resource Path Handling
        # python/core/ai_engine.py -> ../../plugins/captcha_solver
        self.PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        self.MODEL_DIR = os.path.join(self.PROJECT_ROOT, 'plugins', 'captcha_solver')

    def process_request(self, model_id, data):
        """
        Submits inference task to the process pool.
        """
        image_data = data.get("image")
        if not image_data:
            return {"status": "error", "message": "No image data"}

        # Submit task
        future = self.executor.submit(_inference_task, model_id, image_data, self.MODEL_DIR)
        
        try:
            return future.result()
        except Exception as e:
            logger.error(f"Process Execution Failed: {e}")
            return {"status": "error", "message": str(e)}

# Singleton
ai_engine = AIEngine()