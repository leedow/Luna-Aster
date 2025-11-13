"""
Kokoro TTS 提供商实现
使用 Kokoro TTS 模型进行语音合成，支持流式生成
"""

import io
import asyncio
import numpy as np
import soundfile as sf
from typing import Dict, Any, Optional, AsyncIterator
from loguru import logger

from .base import BaseTTSProvider


class KokoroProvider(BaseTTSProvider):
    """Kokoro TTS提供商，支持流式生成"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model = None
        self.pipeline = None
        self.lang_code = config.get("lang_code", "z")  # 默认语言代码
        self.voice = config.get("voice", "zf_001")  # 默认语音
        self.sample_rate = 24000  # Kokoro默认采样率
        self.repo_id = config.get("repo_id", "hexgrad/Kokoro-82M-v1.1-zh")
        self.KModel = None
        self.KPipeline = None
        self.device = None
        
        try:
            from kokoro import KModel, KPipeline
            import torch
            
            self.KModel = KModel
            self.KPipeline = KPipeline
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"✅ Kokoro TTS库导入成功，设备: {self.device}, 语音: {self.voice}")
        except ImportError:
            logger.error("❌ kokoro库未安装，请运行: pip install git+https://github.com/remsky/Kokoro-FastAPI.git")
        except Exception as e:
            logger.error(f"❌ Kokoro初始化失败: {str(e)}")

        self._ensure_pipeline()
    
    def _ensure_pipeline(self):
        """确保pipeline已初始化"""
        if self.model is None and self.KModel is not None:
            try:
                self.model = self.KModel(repo_id=self.repo_id).to(self.device).eval()
                logger.info(f"✅ Kokoro model加载成功: {self.repo_id}")
            except Exception as e:
                logger.error(f"❌ Kokoro model加载失败: {str(e)}")
                raise Exception(f"Kokoro model加载失败: {str(e)}")
        
        if self.pipeline is None and self.KPipeline is not None and self.model is not None:
            try:
                self.pipeline = self.KPipeline(
                    lang_code=self.lang_code, 
                    repo_id=self.repo_id,
                    model=self.model
                )
                logger.info(f"✅ Kokoro pipeline初始化成功")
            except Exception as e:
                logger.error(f"❌ Kokoro pipeline初始化失败: {str(e)}")
                raise Exception(f"Kokoro pipeline初始化失败: {str(e)}")
        return self.pipeline is not None
    
    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        #text = "美国只是一只纸老虎，我们中国人民不怕！"
        """合成语音（非流式，返回完整音频）"""
        if not self._ensure_pipeline():
            raise Exception("Kokoro未初始化")
        
        if not self.validate_text(text):
            raise Exception("无效的文本内容")
        
        try:
            voice = kwargs.get("voice", self.voice)
            
            # 使用generator生成音频，根据demo使用next()获取结果
            generator = self.pipeline(text, voice=voice)
            result = next(generator)
            audio_data = result.audio
            
            if audio_data is None or len(audio_data) == 0:
                raise Exception("生成的音频数据为空")
            
            # 转换为WAV格式的字节数据
            wav_buffer = io.BytesIO()
            sf.write(wav_buffer, audio_data, self.sample_rate, format='WAV')
            wav_bytes = wav_buffer.getvalue()
            
            # 计算时长
            duration = len(audio_data) / self.sample_rate
            
            result = {
                "audio_data": wav_bytes,
                "format": "wav",
                "sample_rate": self.sample_rate,
                "channels": 1,
                "duration": duration,
                "text": text,
                "voice": voice,
                "language": self.language,
                "provider": "kokoro",
                "model": f"kokoro-{voice}"
            }
            
            logger.info(f"🔊 Kokoro TTS合成成功: {text[:50]}... (语音: {voice}, 时长: {duration:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Kokoro TTS合成失败: {str(e)}")
            raise Exception(f"Kokoro TTS合成失败: {str(e)}")
    
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.KPipeline:
            return False
        
        return True
    
    def get_supported_voices(self) -> list:
        """获取支持的语音列表"""
        # Kokoro支持的语音列表（根据实际模型调整）
        return [
            "zf_001",
            
        ]
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        # Kokoro支持的语言代码
        return [
            "a",  # 自动检测
            "en",  # 英语
            "zh",  # 中文
            "ja",  # 日语
            "ko",  # 韩语
            "es",  # 西班牙语
            "fr",  # 法语
            "de",  # 德语
            "it",  # 意大利语
            "pt",  # 葡萄牙语
            "ru",  # 俄语
        ]

