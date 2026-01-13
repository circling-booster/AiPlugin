import os
import json
import logging
import re
import fnmatch
from typing import Dict, Optional, Any
from multiprocessing import Process
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
        self.connection: Any = None  # [Modified] IPC Connection Object (Pipe)
        
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
    _instance = None
    plugins: Dict[str, PluginContext]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PluginLoader, cls).__new__(cls)
            cls._instance.plugins = {}
            cls._instance.plugins_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../plugins"))
        return cls._instance

    def _load_settings(self) -> dict:
        settings_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../config/settings.json"))
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load settings.json: {e}")
        return {}

    def load_plugins(self, user_settings: dict = None):
        if not user_settings:
            user_settings = self._load_settings()

        active_plugins = user_settings.get("active_plugins") 

        if not os.path.exists(self.plugins_dir):
            logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return

        logger.info("=== Start Loading Plugins (Debug Mode) ===") # [Debug] 시작 알림

        for folder in os.listdir(self.plugins_dir):
            p_path = os.path.join(self.plugins_dir, folder)
            m_path = os.path.join(p_path, "manifest.json")
            
            if os.path.exists(m_path):
                try:
                    with open(m_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    manifest = PluginManifest(**data)

                    # [Debug] manifest ID 확인
                    if manifest.id == "captcha_solver":
                        logger.info(f"[{manifest.id}] Manifest Found at: {m_path}")
                        logger.info(f"[{manifest.id}] Raw Supported Modes in File: {data.get('inference', {}).get('supported_modes')}")
                        logger.info(f"[{manifest.id}] Parsed Supported Modes: {manifest.inference.supported_modes}")
                        logger.info(f"[{manifest.id}] Default Mode: {manifest.inference.default_mode}")

                    if active_plugins is not None and manifest.id not in active_plugins:
                        logger.debug(f"Skipping plugin {manifest.id} (not in active_plugins)")
                        continue

                    pref_mode = user_settings.get("plugin_modes", {}).get(manifest.id)
                    
                    # [Debug] 모드 결정 로직 추적
                    if manifest.id == "captcha_solver":
                        logger.info(f"[{manifest.id}] User Preference from Settings: '{pref_mode}'")
                        is_supported = pref_mode in manifest.inference.supported_modes
                        logger.info(f"[{manifest.id}] Is Preference Supported? {is_supported}")

                    final_mode = pref_mode if pref_mode in manifest.inference.supported_modes else manifest.inference.default_mode

                    if manifest.id == "captcha_solver":
                         logger.info(f"[{manifest.id}] FINAL DECISION: {final_mode}")

                    self.plugins[manifest.id] = PluginContext(manifest, p_path, final_mode)
                    logger.info(f"Loaded Metadata: {manifest.id} (Mode: {final_mode})")

                except Exception as e:
                    logger.error(f"Load Error {folder}: {e}")

    def get_plugin(self, plugin_id: str) -> Optional[PluginContext]:
        return self.plugins.get(plugin_id)

plugin_loader = PluginLoader()