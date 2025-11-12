"""
VAD 提供商工厂类
负责创建和管理不同的 VAD 提供商实例
"""

from typing import Dict, Any, Type, Optional
from loguru import logger

from .base import BaseVADProvider
from .silero_vad_provider import SileroVADProvider
from .mock_provider import MockVADProvider


class VADProviderFactory:
    """VAD提供商工厂"""
    
    # 注册的提供商类
    _providers: Dict[str, Type[BaseVADProvider]] = {
        "silero": SileroVADProvider,
        "mock": MockVADProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseVADProvider]):
        """
        注册新的VAD提供商
        
        Args:
            name: 提供商名称
            provider_class: 提供商类
        """
        cls._providers[name] = provider_class
        logger.info(f"📝 已注册VAD提供商: {name}")
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[BaseVADProvider]:
        """
        创建VAD提供商实例
        
        Args:
            provider_type: 提供商类型
            config: 配置信息
            
        Returns:
            BaseVADProvider: 提供商实例，如果创建失败返回None
        """
        if provider_type not in cls._providers:
            logger.error(f"❌ 未知的VAD提供商类型: {provider_type}")
            return None
        
        try:
            provider_class = cls._providers[provider_type]
            provider = provider_class(config)
            logger.info(f"✅ 创建VAD提供商成功: {provider_type}")
            return provider
        except Exception as e:
            logger.error(f"❌ 创建VAD提供商失败 {provider_type}: {str(e)}")
            return None
    
    @classmethod
    def create_providers_from_config(cls, config: Dict[str, Any], only_preferred: bool = False, preferred_provider: Optional[str] = None) -> Dict[str, BaseVADProvider]:
        """
        根据配置创建VAD提供商
        
        Args:
            config: 完整的VAD配置
            only_preferred: 是否只创建配置的首选提供商
            preferred_provider: 首选提供商名称
            
        Returns:
            Dict[str, BaseVADProvider]: 提供商实例字典
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
                        logger.info(f"🏭 VAD工厂创建了首选提供商: {preferred_provider}")
                    else:
                        raise RuntimeError(f"❌ 无法创建VAD提供商: {preferred_provider}，请检查配置和依赖")
                else:
                    raise RuntimeError(f"❌ VAD提供商 {preferred_provider} 未启用，请检查配置")
            else:
                raise RuntimeError(f"❌ VAD提供商 {preferred_provider} 的配置不存在，请检查配置")
        else:
            # 创建所有启用的提供商
            for provider_name, provider_config in config.items():
                if provider_config.get("enabled", True):
                    provider = cls.create_provider(provider_name, provider_config)
                    if provider:
                        providers[provider_name] = provider
        
        return providers
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的提供商类型
        
        Returns:
            list: 提供商类型列表
        """
        return list(cls._providers.keys())

