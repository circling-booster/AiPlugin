from typing import Dict, List, Literal
from pydantic import BaseModel, Field

# --- Manifest V3 Schema Definition (Pydantic) ---
class InferenceConfig(BaseModel):
    supported_modes: List[str] = Field(default=["local"])
    default_mode: str = Field(default="local")
    local_entry: str = "backend.py"
    web_entry: str = "web_backend.py"

class ContentScript(BaseModel):
    matches: List[str] = ["<all_urls>"]
    js: List[str] = ["content.js"]
    # [변경] Manifest V3 표준에 맞춘 run_at 옵션 및 iframe 지원 여부
    run_at: Literal["document_start", "document_end", "document_idle"] = Field(default="document_end")
    all_frames: bool = Field(default=False)

class PluginManifest(BaseModel):
    manifest_version: int = Field(default=3, description="Must be version 3")
    id: str
    name: str = "Unknown Plugin"
    requirements: Dict[str, List[str]] = Field(default_factory=dict)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    host_permissions: List[str] = Field(default_factory=list)
    content_scripts: List[ContentScript] = Field(default_factory=list)