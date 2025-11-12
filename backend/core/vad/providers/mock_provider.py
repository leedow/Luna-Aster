"""
Mock VAD 提供商
用于测试和开发，模拟VAD检测结果
"""

from typing import Dict, Any, Optional
from loguru import logger
from .base import BaseVADProvider


class MockVADProvider(BaseVADProvider):
    """Mock VAD 提供商（用于测试）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.always_detect = config.get("always_detect", False)
        self.detection_rate = config.get("detection_rate", 0.5)  # 50% 检测率

    async def is_available(self) -> bool:
        """Mock provider 总是可用"""
        return True

    async def detect_speech(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        模拟VAD检测
        
        Args:
            audio_data: 音频字节数据
            **kwargs: 额外参数
        
        Returns:
            Dict包含检测结果
        """
        import random
        
        # 简单的模拟逻辑：根据配置决定是否检测到语音
        if self.always_detect:
            vad_detected = True
        else:
            vad_detected = random.random() < self.detection_rate
        
        if vad_detected and len(audio_data) > 100:
            # 模拟检测到语音片段
            return {
                "vad_detected": True,
                "speech_active": False,
                "speech_segment": audio_data,  # 返回原始音频作为语音片段
                "vad_metadata": {
                    "provider": "mock",
                    "detection_rate": self.detection_rate,
                }
            }
        else:
            return {
                "vad_detected": False,
                "speech_active": False,
                "speech_segment": None,
                "vad_metadata": {
                    "provider": "mock",
                }
            }

