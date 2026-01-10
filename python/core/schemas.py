from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# [NEW] 모델 의존성 정의 스키마
class ModelRequirement(BaseModel):
    key: str              # 플러그인 프로세스에 주입될 환경변수 키 (예: "MATH_MODEL")
    filename: str         # models/ 폴더에 저장될 파일명
    source_url: Optional[str] = None  # 파일 부재 시 다운로드할 URL
    sha256: Optional[str] = None      # 무결성 검증용 해시
    description: Optional[str] = None

class InferenceConfig(BaseModel):
    supported_modes: List[str] = Field(default=["local"])
    default_mode: str = Field(default="local")
    local_entry: str = "backend.py"
    web_entry: str = "web_backend.py"
    # [NEW] 모델 리스트 필드 추가
    models: List[ModelRequirement] = Field(default_factory=list)

class ContentScript(BaseModel):
    matches: List[str] = ["<all_urls>"]
    js: List[str] = ["content.js"]
    run_at: Literal["document_start", "document_end", "document_idle"] = Field(default="document_end")
    all_frames: bool = Field(default=False)

class PluginManifest(BaseModel):
    manifest_version: int = Field(default=3)
    id: str
    name: str = "Unknown Plugin"
    requirements: Dict[str, List[str]] = Field(default_factory=dict)
    inference: InferenceConfig = Field(default_factory=InferenceConfig)
    host_permissions: List[str] = Field(default_factory=list)
    content_scripts: List[ContentScript] = Field(default_factory=list)