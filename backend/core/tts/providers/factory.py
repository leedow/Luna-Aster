"""
TTS 提供商工厂
负责创建和管理不同的 TTS 提供商实例
"""

from typing import Dict, Any, List, Type, Optional
from loguru import logger

from .base import BaseTTSProvider
from .edge_tts_provider import EdgeTTSProvider
from .gtts_provider import GTTSProvider
from .pyttsx3_provider import Pyttsx3Provider
from .mock_provider import MockTTSProvider
from .kokoro_provider import KokoroProvider
from .zipvoice_provider import ZipVoiceProvider


class TTSProviderFactory:
    """TTS提供商工厂"""
    
    # 注册的提供商类型
    _providers: Dict[str, Type[BaseTTSProvider]] = {
        "edge_tts": EdgeTTSProvider,
        "gtts": GTTSProvider,
        "pyttsx3": Pyttsx3Provider,
        "mock": MockTTSProvider,
        "kokoro": KokoroProvider,
        "zipvoice": ZipVoiceProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseTTSProvider]):
        """注册新的提供商类型"""
        if not issubclass(provider_class, BaseTTSProvider):
            raise ValueError(f"提供商类必须继承自 BaseTTSProvider")
        
        cls._providers[name] = provider_class
        logger.info(f"✅ 注册TTS提供商: {name}")
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> BaseTTSProvider:
        """创建单个提供商实例"""
        if provider_type not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"未知的TTS提供商类型: {provider_type}。可用类型: {available}")
        
        try:
            provider_class = cls._providers[provider_type]
            provider = provider_class(config)
            logger.info(f"✅ 创建TTS提供商: {provider_type}")
            return provider
            
        except Exception as e:
            logger.error(f"❌ 创建TTS提供商失败 ({provider_type}): {str(e)}")
            raise Exception(f"创建TTS提供商失败 ({provider_type}): {str(e)}")
    
    @classmethod
    def create_providers(cls, providers_config: List[Dict[str, Any]]) -> List[BaseTTSProvider]:
        """创建多个提供商实例"""
        providers = []
        
        for config in providers_config:
            provider_type = config.get("type")
            if not provider_type:
                logger.warning("⚠️ 跳过无效的TTS提供商配置（缺少type字段）")
                continue
            
            try:
                provider = cls.create_provider(provider_type, config)
                providers.append(provider)
            except Exception as e:
                logger.error(f"❌ 跳过TTS提供商 {provider_type}: {str(e)}")
                continue
        
        if not providers:
            logger.warning("⚠️ 没有成功创建任何TTS提供商，创建Mock提供商作为后备")
            mock_config = {
                "type": "mock",
                "voice": "default",
                "language": "zh-CN",
                "rate": 1.0
            }
            providers.append(cls.create_provider("mock", mock_config))
        
        logger.info(f"✅ 成功创建 {len(providers)} 个TTS提供商")
        return providers
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """获取可用的提供商类型列表"""
        return list(cls._providers.keys())
    
    @classmethod
    def get_provider_info(cls, provider_type: str) -> Optional[Dict[str, Any]]:
        """获取提供商信息"""
        if provider_type not in cls._providers:
            return None
        
        provider_class = cls._providers[provider_type]
        
        # 创建临时实例获取信息
        try:
            temp_config = {
                "voice": "default",
                "language": "zh-CN",
                "rate": 1.0
            }
            temp_provider = provider_class(temp_config)
            
            return {
                "type": provider_type,
                "name": provider_class.__name__,
                "description": provider_class.__doc__ or "无描述",
                "supported_voices": temp_provider.get_supported_voices(),
                "supported_languages": temp_provider.get_supported_languages()
            }
            
        except Exception as e:
            logger.warning(f"⚠️ 获取TTS提供商信息失败 ({provider_type}): {str(e)}")
            return {
                "type": provider_type,
                "name": provider_class.__name__,
                "description": provider_class.__doc__ or "无描述",
                "supported_voices": ["default"],
                "supported_languages": ["zh-CN"],
                "error": str(e)
            }
    
    @classmethod
    def get_all_providers_info(cls) -> Dict[str, Dict[str, Any]]:
        """获取所有提供商信息"""
        info = {}
        for provider_type in cls._providers:
            info[provider_type] = cls.get_provider_info(provider_type)
        return info