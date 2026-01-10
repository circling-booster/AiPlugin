from typing import Dict, List
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
    run_at: str = "document_end"

class PluginManifest(BaseModel):
    manifest_version: int = Field(default=3, description="Must be version 3")
    id: str
    name: str = "Unknown Plugin"
    requirements: Dict[str, List[str]] = Field(default_factory=dict)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    host_permissions: List[str] = Field(default_factory=list)
    content_scripts: List[ContentScript] = Field(default_factory=list)