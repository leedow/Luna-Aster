"""
Mock TTS 提供商实现
用于测试和开发的模拟语音合成提供商
"""

import asyncio
import random
from typing import Dict, Any
from loguru import logger

from .base import BaseTTSProvider


class MockTTSProvider(BaseTTSProvider):
    """Mock TTS提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mock_delay = config.get("mock_delay", 0)  # 模拟延迟
        self.mock_audio_size = config.get("mock_audio_size", 1024)  # 模拟音频大小
        logger.info(f"✅ Mock TTS初始化成功，语音: {self.voice}")
    
    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """模拟语音合成"""
        if not self.validate_text(text):
            raise Exception("无效的文本内容")
        
        try:
            # 获取参数
            rate = kwargs.get("rate", self.rate)
            voice = kwargs.get("voice", self.voice)
            
            # 模拟处理延迟
            delay = self.mock_delay * (1 + random.uniform(-0.3, 0.3))
            await asyncio.sleep(delay)
            
            # 生成模拟音频数据
            audio_data = self._generate_mock_audio(text)
            
            # 计算模拟时长
            duration = len(text) * 0.1 * (2.0 - rate)  # 基于文本长度和语速
            
            result = {
                "audio_data": audio_data,
                "format": "wav",
                "sample_rate": 22050,
                "channels": 1,
                "duration": duration,
                "text": text,
                "voice": voice,
                "language": self.language,
                "provider": "mock",
                "model": f"mock-{voice}"
            }
            
            logger.info(f"🔊 Mock TTS合成成功: {text[:50]}... (语音: {voice}, 时长: {duration:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Mock TTS合成失败: {str(e)}")
            raise Exception(f"Mock TTS合成失败: {str(e)}")
    
    def _generate_mock_audio(self, text: str) -> bytes:
        """生成模拟音频数据"""
        # 基于文本长度生成不同大小的模拟数据
        base_size = self.mock_audio_size
        text_factor = min(len(text) / 100, 10)  # 文本长度因子
        audio_size = int(base_size * (1 + text_factor))
        
        # 生成模拟的WAV头部和数据
        wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x22\x56\x00\x00\x44\xac\x00\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
        
        # 生成模拟音频数据（基于文本内容的伪随机数据）
        random.seed(hash(text) % 2**32)  # 基于文本内容的种子，确保相同文本生成相同音频
        audio_data = bytes([random.randint(0, 255) for _ in range(audio_size)])
        
        return wav_header + audio_data
    
    async def is_available(self) -> bool:
        """检查服务是否可用（Mock总是可用）"""
        return True
    
    def get_supported_voices(self) -> list:
        """获取支持的语音列表"""
        return [
            "mock-female-1",
            "mock-female-2",
            "mock-male-1",
            "mock-male-2",
            "mock-child",
            "mock-elderly",
            "mock-robot",
            "default"
        ]
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        return [
            "zh-CN",  # 中文（简体）
            "zh-TW",  # 中文（繁体）
            "en-US",  # 英语（美国）
            "en-GB",  # 英语（英国）
            "ja-JP",  # 日语
            "ko-KR",  # 韩语
            "fr-FR",  # 法语
            "de-DE",  # 德语
            "es-ES",  # 西班牙语
            "it-IT",  # 意大利语
            "pt-BR",  # 葡萄牙语
            "ru-RU",  # 俄语
            "ar-SA",  # 阿拉伯语
            "hi-IN",  # 印地语
            "th-TH",  # 泰语
            "vi-VN"   # 越南语
        ]
    
    def validate_text(self, text: str) -> bool:
        """验证文本内容（Mock接受任何非空文本）"""
        return bool(text and text.strip())