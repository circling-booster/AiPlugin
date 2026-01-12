from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# -------------------------------------------------------------------------
# [Plugin Manifest Schemas]
# -------------------------------------------------------------------------

class ModelRequirement(BaseModel):
    """플러그인 실행에 필요한 AI 모델 정의"""
    key: str              # 환경변수 키 (예: "YOLO_MODEL")
    filename: str         # models/ 폴더 내 파일명
    source_url: Optional[str] = None
    sha256: Optional[str] = None
    description: Optional[str] = None

class InferenceConfig(BaseModel):
    """추론 설정 (로컬/웹 분기)"""
    supported_modes: List[str] = Field(default=["local"])
    default_mode: str = Field(default="local")
    local_entry: str = "backend.py"
    web_entry: str = "web_backend.py"
    models: List[ModelRequirement] = Field(default_factory=list)

class ContentScript(BaseModel):
    """주입할 스크립트 정보"""
    matches: List[str] = ["<all_urls>"]
    js: List[str] = ["content.js"]
    run_at: Literal["document_start", "document_end", "document_idle"] = Field(default="document_end")
    all_frames: bool = Field(default=False)

class PluginManifest(BaseModel):
    """manifest.json 구조"""
    manifest_version: int = Field(default=3)
    id: str
    name: str = "Unknown Plugin"
    requirements: Dict[str, List[str]] = Field(default_factory=dict)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    host_permissions: List[str] = Field(default_factory=list)
    content_scripts: List[ContentScript] = Field(default_factory=list)

# -------------------------------------------------------------------------
# [Dual-Pipeline Communication Schemas]
# -------------------------------------------------------------------------

class MatchRequest(BaseModel):
    """Electron -> Python: 현재 URL에 맞는 플러그인이 있는지 질의"""
    url: str

class ScriptInjection(BaseModel):
    """[추가] 스크립트 주입 정보 (URL + 실행 시점)"""
    url: str
    run_at: str

class MatchResponse(BaseModel):
    """Python -> Electron: 주입해야 할 스크립트 목록"""
    scripts: List[ScriptInjection]