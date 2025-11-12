"""
VAD 基础提供商抽象类
定义所有 VAD 提供商的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseVADProvider(ABC):
    """VAD提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model", "base")
        self.sample_rate = config.get("sample_rate", 16000)
        self.threshold = config.get("threshold", 0.5)
    
    @abstractmethod
    async def detect_speech(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        检测音频中的语音活动
        
        Args:
            audio_data: 音频字节数据
            **kwargs: 额外参数
                - client_id: 客户端ID（用于会话管理）
                - audio_format: 音频格式 ('pcm' 或 'wav')
                - sample_rate: 采样率
                - channels: 声道数
            
        Returns:
            Dict包含检测结果：
            {
                "vad_detected": bool,  # 是否检测到语音
                "speech_active": bool,  # 语音是否正在进行中
                "speech_segment": Optional[bytes],  # 检测到的语音片段（当语音结束时）
                "vad_metadata": Dict,  # VAD元数据
            }
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
        if not audio_data or len(audio_data) == 0:
            return False
        return True

