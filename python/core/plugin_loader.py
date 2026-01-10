import os
import json
import logging
import re
import fnmatch
from typing import Dict, Optional
from multiprocessing import Process, Queue
from pydantic import ValidationError
from core.schemas import PluginManifest

# 로거 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s - %(message)s')
logger = logging.getLogger("AiPlugs.Loader")

class PluginContext:
    """
    플러그인 데이터 모델 (상태 저장소)
    """
    def __init__(self, manifest: PluginManifest, base_path: str, active_mode: str):
        self.manifest = manifest
        self.base_path = base_path
        self.mode = active_mode
        # Runtime 상태 (RuntimeManager가 채워줌)
        self.process: Optional[Process] = None
        self.ipc_queue: Optional[Queue] = None
        
        # URL 매칭 패턴 컴파일
        self.compiled_patterns = []
        for script in manifest.content_scripts:
            for glob_pat in script.matches:
                if glob_pat == "<all_urls>":
                    self.compiled_patterns.append(re.compile(r".*"))
                else:
                    regex = fnmatch.translate(glob_pat)
                    self.compiled_patterns.append(re.compile(regex, re.IGNORECASE))

class PluginLoader:
    """
    [Refactor] 오직 '파일 시스템 스캔'과 '메타데이터 로드'에만 집중 (SRP 준수)
    """
    _instance = None
    plugins: Dict[str, PluginContext]  # 타입 힌트

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginLoader, cls).__new__(cls)
            cls._instance.plugins = {}
            # python/core/plugin_loader.py 기준 -> ../../plugins
            cls._instance.plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../plugins"))
        return cls._instance

    def _load_settings(self) -> dict:
        """[New] config/settings.json 파일 로드"""
        # python/core/plugin_loader.py 기준 -> ../../config/settings.json
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/settings.json"))
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load settings.json: {e}")
        return {}

    def load_plugins(self, user_settings: dict = None):
        """plugins 폴더를 스캔하여 메타데이터 로드"""
        # 1. 설정 로드 (인자값이 없으면 파일에서 읽음)
        if not user_settings:
            user_settings = self._load_settings()

        # active_plugins 키가 존재하면 필터링 모드로 동작 (None이면 모든 플러그인 로드)
        active_plugins = user_settings.get("active_plugins") 

        if not os.path.exists(self.plugins_dir):
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return

        for folder in os.listdir(self.plugins_dir):
            p_path = os.path.join(self.plugins_dir, folder)
            m_path = os.path.join(p_path, "manifest.json")
            
            if os.path.exists(m_path):
                try:
                    with open(m_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    manifest = PluginManifest(**data)

                    # [Improvement] active_plugins 필터링 적용
                    # 리스트가 존재하고, 해당 리스트에 ID가 없다면 로드하지 않음
                    if active_plugins is not None and manifest.id not in active_plugins:
                        logger.debug(f"Skipping plugin {manifest.id} (not in active_plugins)")
                        continue

                    # Mode 결정 (사용자 설정 우선)
                    pref_mode = user_settings.get("plugin_modes", {}).get(manifest.id)
                    final_mode = pref_mode if pref_mode in manifest.inference.supported_modes else manifest.inference.default_mode

                    self.plugins[manifest.id] = PluginContext(manifest, p_path, final_mode)
                    logger.info(f"Loaded Metadata: {manifest.id} (Mode: {final_mode})")

                except Exception as e:
                    logger.error(f"Load Error {folder}: {e}")

    def get_plugin(self, plugin_id: str) -> Optional[PluginContext]:
        return self.plugins.get(plugin_id)

# Singleton Instance
plugin_loader = PluginLoader()