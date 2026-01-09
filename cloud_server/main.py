import uvicorn
import base64
import io
import os
import torch
import torch.nn as nn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from torchvision import transforms
from PIL import Image

app = FastAPI()

# --- Model Definition (Same as Local) ---
class CaptchaModel(nn.Module):
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
            nn.Linear(64 * 16 * 64, 128),
            nn.ReLU(),
            nn.Linear(128, num_classes)
        )
    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x

# Global State
MODELS = {}
DEVICE = torch.device("cpu") # Cloud usually runs on CPU or GPU
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

def get_model(model_type):
    if model_type in MODELS:
        return MODELS[model_type]
    
    path = os.path.join(BASE_PATH, "models", f"model_{model_type}.pt")
    if not os.path.exists(path):
        print(f"[Cloud] Warning: {path} not found. Using untrain model for demo.")
        model = CaptchaModel()
    else:
        model = torch.load(path, map_location=DEVICE)
        # Handle state_dict logic if needed
        if isinstance(model, dict):
            net = CaptchaModel()
            net.load_state_dict(model)
            model = net

    model.to(DEVICE)
    model.eval()
    MODELS[model_type] = model
    return model

class InferenceRequest(BaseModel):
    plugin_id: str = "get_captcha"
    action: str = "predict"
    image: str
    model_type: str = "melon"

@app.post("/predict")
async def predict_endpoint(req: InferenceRequest):
    try:
        # 1. Decode Image
        if "," in req.image:
            img_b64 = req.image.split(",")[1]
        else:
            img_b64 = req.image
        
        image_bytes = base64.b64decode(img_b64)
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # 2. Preprocess
        transform = transforms.Compose([
            transforms.Resize((64, 256)),
            transforms.ToTensor()
        ])
        input_tensor = transform(image).unsqueeze(0).to(DEVICE)
        
        # 3. Inference
        model = get_model(req.model_type)
        with torch.no_grad():
            output = model(input_tensor)
            _, predicted = torch.max(output, 1)
            result_text = str(predicted.item())

        return {
            "status": "success",
            "result": result_text,
            "mode": "cloud",
            "server": "cloud-v1"
        }

    except Exception as e:
        return {"status": "error", "message": f"Cloud Error: {str(e)}"}

if __name__ == "__main__":
    # Ensure models dir exists
    if not os.path.exists(os.path.join(BASE_PATH, "models")):
        os.makedirs(os.path.join(BASE_PATH, "models"))
    uvicorn.run(app, host="0.0.0.0", port=8000)