# python/core/proxy_server.py

from mitmproxy import http
from core.plugin_loader import plugin_loader
from core.proxy_pipeline import (
    ContentTypeFilter, ResourceFilter, Decoder, PluginMatcher, 
    Injector, HeaderNormalizer
)

class AiPlugsAddon:
    def __init__(self, api_port: int):
        self.api_port = api_port
        
        if not plugin_loader.plugins:
            plugin_loader.load_plugins()
            
        # 파이프라인 조립
        self.pipeline = [
            ContentTypeFilter(),
            ResourceFilter(),
            Decoder(),
            PluginMatcher(),
            Injector(self.api_port),
            HeaderNormalizer()
        ]
        
        print(f"[Proxy] AiPlugs Core initialized with Pipeline. API Port: {self.api_port}")

    def response(self, flow: http.HTTPFlow):
        context = {}
        try:
            for handler in self.pipeline:
                should_continue = handler.process(flow, context)
                if not should_continue:
                    break
        except Exception as e:
            print(f"[Proxy] Pipeline Error processing {flow.request.url}: {e}")