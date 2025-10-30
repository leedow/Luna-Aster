"""
TTS 基础提供商抽象类
定义所有 TTS 提供商的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
import os


class BaseTTSProvider(ABC):
    """TTS提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.voice = config.get("voice", "default")
        self.rate = config.get("rate", 1.0)
        self.pitch = config.get("pitch", 1.0)
        self.language = config.get("language", "zh-CN")
    
    @abstractmethod
    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            **kwargs: 额外参数
            
        Returns:
            Dict包含音频数据和元数据
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        pass
    
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称
        """
        return self.__class__.__name__.replace("Provider", "").lower()
    
    def validate_text(self, text: str) -> bool:
        """
        验证文本内容
        
        Args:
            text: 要验证的文本
            
        Returns:
            bool: 文本是否有效
        """
        if not text or not text.strip():
            return False
        
        # 检查文本长度限制
        max_length = self.config.get("max_text_length", 5000)
        if len(text) > max_length:
            return False
        
        return True
    
    def get_supported_voices(self) -> list:
        """
        获取支持的语音列表
        
        Returns:
            list: 支持的语音列表
        """
        return ["default"]
    
    def get_supported_languages(self) -> list:
        """
        获取支持的语言列表
        
        Returns:
            list: 支持的语言列表
        """
        return ["zh-CN", "en-US"]