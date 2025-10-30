"""
ASR 基础提供商抽象类
定义所有 ASR 提供商的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import io


class BaseASRProvider(ABC):
    """ASR提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model", "base")
        self.language = config.get("language", "zh")
        self.sample_rate = config.get("sample_rate", 16000)
    
    @abstractmethod
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        转录音频数据
        
        Args:
            audio_data: 音频字节数据
            **kwargs: 额外参数
            
        Returns:
            Dict包含转录结果和元数据
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
    
    def validate_audio_format(self, audio_data: bytes) -> bool:
        """
        验证音频格式
        
        Args:
            audio_data: 音频字节数据
            
        Returns:
            bool: 格式是否有效
        """
        if not audio_data or len(audio_data) < 44:  # WAV header minimum size
            return False
        return True