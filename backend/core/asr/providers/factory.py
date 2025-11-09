"""
ASR 提供商工厂类
负责创建和管理不同的 ASR 提供商实例
"""

from typing import Dict, Any, Type, Optional
from loguru import logger

from .base import BaseASRProvider
from .whisper_provider import WhisperProvider
from .speech_recognition_provider import SpeechRecognitionProvider
from .mock_provider import MockASRProvider
from .sensevoice_provider import SenseVoiceSmallProvider
from .paraformer_streaming_provider import ParaformerStreamingProvider
from .fast_whisper_provider import FastWhisperProvider


class ASRProviderFactory:
    """ASR提供商工厂"""
    
    # 注册的提供商类
    _providers: Dict[str, Type[BaseASRProvider]] = {
        "whisper": WhisperProvider,
        "speech_recognition": SpeechRecognitionProvider,
        "mock": MockASRProvider,
        "sensevoice": SenseVoiceSmallProvider,
        "paraformer_streaming": ParaformerStreamingProvider,
        "fast_whisper": FastWhisperProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseASRProvider]):
        """
        注册新的ASR提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        cls._providers[name] = provider_class
        logger.info(f"📝 已注册ASR提供商: {name}")
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[BaseASRProvider]:
        """
        创建ASR提供商实例
        
        Args:
            provider_type: 提供商类型
            config: 配置信息
            
        Returns:
            BaseASRProvider: 提供商实例，如果创建失败返回None
        """
        if provider_type not in cls._providers:
            logger.error(f"❌ 未知的ASR提供商类型: {provider_type}")
            return None
        
        try:
            provider_class = cls._providers[provider_type]
            provider = provider_class(config)
            logger.info(f"✅ 创建ASR提供商成功: {provider_type}")
            return provider
        except Exception as e:
            logger.error(f"❌ 创建ASR提供商失败 {provider_type}: {str(e)}")
            return None
    
    @classmethod
    def create_providers_from_config(cls, config: Dict[str, Any], only_preferred: bool = False, preferred_provider: Optional[str] = None) -> Dict[str, BaseASRProvider]:
        """
        根据配置创建ASR提供商
        
        Args:
            config: 完整的ASR配置
            only_preferred: 是否只创建配置的首选提供商
            preferred_provider: 首选提供商名称
            
        Returns:
            Dict[str, BaseASRProvider]: 提供商实例字典
        """
        providers = {}
        
        # 如果只加载首选提供商，只创建配置的provider
        if only_preferred and preferred_provider:
            provider_config_key = preferred_provider
            if provider_config_key in config:
                provider_config = config[provider_config_key]
                # 检查是否启用（如果配置中有enabled字段）
                if provider_config.get("enabled", True):
                    provider = cls.create_provider(preferred_provider, provider_config)
                    if provider:
                        providers[preferred_provider] = provider
                        logger.info(f"🏭 ASR工厂创建了首选提供商: {preferred_provider}")
                    else:
                        raise RuntimeError(f"❌ 无法创建ASR提供商: {preferred_provider}，请检查配置和依赖")
                else:
                    raise RuntimeError(f"❌ ASR提供商 {preferred_provider} 未启用，请检查配置")
            else:
                raise RuntimeError(f"❌ ASR提供商 {preferred_provider} 的配置不存在，请检查配置")
        else:
            # 原有逻辑：创建所有配置的提供商（保留兼容性）
            # Whisper提供商
            if "whisper" in config and config["whisper"].get("api_key"):
                provider = cls.create_provider("whisper", config["whisper"])
                if provider:
                    providers["whisper"] = provider
            
            # SpeechRecognition提供商
            if "speech_recognition" in config:
                provider = cls.create_provider("speech_recognition", config["speech_recognition"])
                if provider:
                    providers["speech_recognition"] = provider

            # SenseVoiceSmall 提供商
            if "sensevoice" in config:
                provider = cls.create_provider("sensevoice", config["sensevoice"])
                if provider:
                    providers["sensevoice"] = provider
            
            # ParaformerStreaming 提供商
            if "paraformer_streaming" in config:
                provider = cls.create_provider("paraformer_streaming", config["paraformer_streaming"])
                if provider:
                    providers["paraformer_streaming"] = provider
            
            # FastWhisper 提供商
            if "fast_whisper" in config:
                provider = cls.create_provider("fast_whisper", config["fast_whisper"])
                if provider:
                    providers["fast_whisper"] = provider
            
            # Mock提供商（总是创建）
            mock_config = config.get("mock", {"model": "mock-asr-model"})
            provider = cls.create_provider("mock", mock_config)
            if provider:
                providers["mock"] = provider
            
            logger.info(f"🏭 ASR工厂创建了 {len(providers)} 个提供商: {list(providers.keys())}")
        
        return providers
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的提供商类型
        
        Returns:
            list: 提供商类型列表
        """
        return list(cls._providers.keys())
    
    @classmethod
    def get_provider_info(cls, provider_type: str) -> Dict[str, Any]:
        """
        获取提供商信息
        
        Args:
            provider_type: 提供商类型
            
        Returns:
            Dict: 提供商信息
        """
        if provider_type not in cls._providers:
            return {}
        
        provider_class = cls._providers[provider_type]
        return {
            "name": provider_type,
            "class": provider_class.__name__,
            "module": provider_class.__module__,
            "description": provider_class.__doc__ or "无描述"
        }