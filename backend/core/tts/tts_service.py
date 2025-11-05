"""
TTS (Text-to-Speech) 服务
支持多种TTS提供商：Edge-TTS、gTTS、pyttsx3等
"""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from config.settings import Settings
from .providers import BaseTTSProvider, TTSProviderFactory

class TTSService:
    """TTS服务管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: List[BaseTTSProvider] = []
        self.current_provider: Optional[BaseTTSProvider] = None
        self.queue: Dict[str, List[str]] = {}  # 客户端队列
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化TTS提供商"""
        # 根据扁平配置创建提供商配置
        providers_config = [
            {
                "type": "edge_tts",
                "voice": self.settings.tts_voice,
                "rate": self.settings.tts_rate,
                "pitch": self.settings.tts_pitch
            },
            {
                "type": "gtts",
                "language": "zh-cn"
            },
            {
                "type": "pyttsx3",
                "voice": "default",
                "rate": 200
            },
            {
                "type": "mock",
                "voice": "default",
                "language": "zh-CN",
                "rate": 1.0
            }
        ]
        
        # 使用工厂创建提供商实例
        self.providers = TTSProviderFactory.create_providers(providers_config)
        
        logger.info(f"✅ 初始化了 {len(self.providers)} 个TTS提供商")
    
    async def select_best_provider(self) -> Optional[BaseTTSProvider]:
        """选择最佳可用的提供商"""
        # 按优先级顺序检查提供商
        priority_order = ["EdgeTTSProvider", "GTTSProvider", "Pyttsx3Provider", "MockTTSProvider"]
        
        # 首先按优先级顺序查找
        for priority_class in priority_order:
            for provider in self.providers:
                if provider.__class__.__name__ == priority_class:
                    if await provider.is_available():
                        logger.info(f"🎯 选择TTS提供商: {provider.get_provider_name()}")
                        return provider
        
        # 如果没有找到优先级提供商，选择第一个可用的
        for provider in self.providers:
            if await provider.is_available():
                logger.info(f"🎯 选择TTS提供商: {provider.get_provider_name()}")
                return provider
        
        logger.warning("⚠️ 没有可用的TTS提供商")
        return None
    
    async def synthesize_speech(self, text: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """合成语音"""
        # 选择提供商
        if not self.current_provider:
            self.current_provider = await self.select_best_provider()
        
        if not self.current_provider:
            raise Exception("没有可用的TTS提供商")
        
        try:
            # 合成语音
            result = await self.current_provider.synthesize_speech(text)
            
            logger.info(f"🔊 语音合成完成: {text[:30]}...")
            return result
            
        except Exception as e:
            logger.error(f"❌ TTS合成失败: {str(e)}")
            # 尝试切换到备用提供商
            self.current_provider = None
            raise e
    
    async def add_to_queue(self, text: str, client_id: str):
        """添加到合成队列"""
        if client_id not in self.queue:
            self.queue[client_id] = []
        
        self.queue[client_id].append({
            "text": text,
            "timestamp": datetime.now()
        })
        
        logger.info(f"📝 已添加到TTS队列: {text[:30]}...")
    
    async def process_queue(self, client_id: str) -> Optional[Dict[str, Any]]:
        """处理合成队列"""
        if client_id not in self.queue or not self.queue[client_id]:
            return None
        
        # 获取队列中的第一个项目
        item = self.queue[client_id].pop(0)
        
        try:
            # 合成语音
            result = await self.synthesize_speech(item["text"], client_id)
            return result
        except Exception as e:
            logger.error(f"❌ 处理TTS队列失败: {str(e)}")
            return None
    
    def clear_queue(self, client_id: str):
        """清空合成队列"""
        if client_id in self.queue:
            del self.queue[client_id]
            logger.info(f"🧹 已清空客户端 {client_id} 的TTS队列")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = {}
        
        for provider in self.providers:
            provider_name = provider.get_provider_name()
            try:
                is_available = await provider.is_available()
                status[provider_name] = {
                    "available": is_available,
                    "voice": provider.voice,
                    "language": provider.language,
                    "status": "healthy" if is_available else "unavailable"
                }
            except Exception as e:
                status[provider_name] = {
                    "available": False,
                    "voice": provider.voice,
                    "language": provider.language,
                    "status": "error",
                    "error": str(e)
                }
        
        return status