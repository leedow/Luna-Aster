"""
LLM 提供商工厂
负责创建和管理不同的 LLM 提供商实例
"""

from typing import Dict, Any, Optional
from loguru import logger

from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .mock_provider import MockLLMProvider


class LLMProviderFactory:
    """LLM 提供商工厂类"""
    
    # 注册的提供商类型
    _providers = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "mock": MockLLMProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[BaseLLMProvider]:
        """
        创建指定类型的提供商实例
        
        Args:
            provider_type: 提供商类型 (openai, anthropic, mock)
            config: 提供商配置
            
        Returns:
            BaseLLMProvider: 提供商实例，如果创建失败返回 None
        """
        if provider_type not in cls._providers:
            logger.error(f"❌ 不支持的LLM提供商类型: {provider_type}")
            return None
        
        try:
            provider_class = cls._providers[provider_type]
            provider = provider_class(config)
            logger.info(f"✅ 创建LLM提供商成功: {provider_type}")
            return provider
        except Exception as e:
            logger.error(f"❌ 创建LLM提供商失败 {provider_type}: {str(e)}")
            return None
    
    @classmethod
    def get_available_providers(cls) -> list:
        """
        获取所有可用的提供商类型
        
        Returns:
            list: 可用的提供商类型列表
        """
        return list(cls._providers.keys())
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: type):
        """
        注册新的提供商类型
        
        Args:
            provider_type: 提供商类型名称
            provider_class: 提供商类
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise ValueError(f"提供商类必须继承自 BaseLLMProvider")
        
        cls._providers[provider_type] = provider_class
        logger.info(f"✅ 注册LLM提供商: {provider_type}")
    
    @classmethod
    def create_providers_from_config(cls, llm_config: Dict[str, Any]) -> Dict[str, BaseLLMProvider]:
        """
        根据配置创建多个提供商实例
        
        Args:
            llm_config: LLM配置字典
            
        Returns:
            Dict[str, BaseLLMProvider]: 提供商实例字典
        """
        providers = {}
        
        # OpenAI提供商
        if llm_config.get("openai", {}).get("api_key"):
            openai_provider = cls.create_provider("openai", llm_config["openai"])
            if openai_provider:
                providers["openai"] = openai_provider
        
        # Anthropic提供商
        if llm_config.get("anthropic", {}).get("api_key"):
            anthropic_provider = cls.create_provider("anthropic", llm_config["anthropic"])
            if anthropic_provider:
                providers["anthropic"] = anthropic_provider
        
        # Mock提供商（总是可用）
        mock_provider = cls.create_provider("mock", {"model": "mock-model"})
        if mock_provider:
            providers["mock"] = mock_provider
        
        logger.info(f"📋 已创建LLM提供商: {list(providers.keys())}")
        return providers