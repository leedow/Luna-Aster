"""
EdgeTTS 提供商实现
使用 Microsoft Edge TTS 进行语音合成
"""

import tempfile
import os
from typing import Dict, Any
from loguru import logger

from .base import BaseTTSProvider


class EdgeTTSProvider(BaseTTSProvider):
    """EdgeTTS提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.communicate = None
        
        try:
            import edge_tts
            self.edge_tts = edge_tts
            logger.info(f"✅ EdgeTTS初始化成功，语音: {self.voice}")
        except ImportError:
            logger.error("❌ edge-tts库未安装，请运行: pip install edge-tts")
            self.edge_tts = None
        except Exception as e:
            logger.error(f"❌ EdgeTTS初始化失败: {str(e)}")
            self.edge_tts = None
    
    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """合成语音"""
        if not self.edge_tts:
            raise Exception("EdgeTTS未初始化")
        
        if not self.validate_text(text):
            raise Exception("无效的文本内容")
        
        try:
            # 获取参数
            voice = kwargs.get("voice", self.voice)
            rate = kwargs.get("rate", self.rate)
            pitch = kwargs.get("pitch", self.pitch)
            
            # 格式化语音参数
            rate_str = f"{int((rate - 1) * 100):+d}%"
            pitch_str = f"{int((pitch - 1) * 50):+d}Hz"
            
            # 创建通信对象
            communicate = self.edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate_str,
                pitch=pitch_str
            )
            
            # 生成音频数据
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            if not audio_data:
                raise Exception("生成的音频数据为空")
            
            result = {
                "audio_data": audio_data,
                "format": "mp3",
                "sample_rate": 24000,  # EdgeTTS默认采样率
                "channels": 1,
                "duration": len(audio_data) / (24000 * 2),  # 估算时长
                "text": text,
                "voice": voice,
                "language": self.language,
                "provider": "edge_tts",
                "model": voice
            }
            
            logger.info(f"🔊 EdgeTTS合成成功: {text[:50]}... (语音: {voice})")
            return result
            
        except Exception as e:
            logger.error(f"❌ EdgeTTS合成失败: {str(e)}")
            raise Exception(f"EdgeTTS合成失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.edge_tts:
            return False
        
        try:
            # 测试简单的文本合成
            test_text = "测试"
            communicate = self.edge_tts.Communicate(
                text=test_text,
                voice=self.voice
            )
            
            # 尝试获取第一个音频块
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    return True
                    
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ EdgeTTS服务不可用: {str(e)}")
            return False
    
    def get_supported_voices(self) -> list:
        """获取支持的语音列表"""
        # EdgeTTS支持的中文语音
        chinese_voices = [
            "zh-CN-XiaoxiaoNeural",
            "zh-CN-XiaoyiNeural", 
            "zh-CN-YunjianNeural",
            "zh-CN-YunxiNeural",
            "zh-CN-YunxiaNeural",
            "zh-CN-YunyangNeural",
            "zh-CN-liaoning-XiaobeiNeural",
            "zh-CN-shaanxi-XiaoniNeural"
        ]
        
        # EdgeTTS支持的英文语音
        english_voices = [
            "en-US-AriaNeural",
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AndrewNeural",
            "en-US-EmmaNeural",
            "en-US-BrianNeural"
        ]
        
        return chinese_voices + english_voices
    
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
            "pt-BR",  # 葡萄牙语（巴西）
            "ru-RU"   # 俄语
        ]