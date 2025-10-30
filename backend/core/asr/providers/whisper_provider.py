"""
Whisper ASR 提供商实现
使用 OpenAI Whisper API 进行语音识别
"""

import io
import tempfile
import os
from typing import Dict, Any
from loguru import logger

from .base import BaseASRProvider


class WhisperProvider(BaseASRProvider):
    """Whisper ASR提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info(f"✅ Whisper客户端初始化成功，模型: {self.model}")
            except ImportError:
                logger.error("❌ OpenAI库未安装，请运行: pip install openai")
            except Exception as e:
                logger.error(f"❌ Whisper客户端初始化失败: {str(e)}")
    
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """转录音频"""
        if not self.client:
            raise Exception("Whisper客户端未初始化")
        
        if not self.validate_audio_format(audio_data):
            raise Exception("无效的音频格式")
        
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # 调用Whisper API
                with open(temp_file_path, "rb") as audio_file:
                    response = await self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file,
                        language=self.language,
                        response_format="verbose_json"
                    )
                
                # 解析响应
                result = {
                    "text": response.text,
                    "language": response.language if hasattr(response, 'language') else self.language,
                    "duration": response.duration if hasattr(response, 'duration') else 0,
                    "model": self.model,
                    "provider": "whisper",
                    "confidence": 0.9  # Whisper不提供置信度，使用默认值
                }
                
                # 如果有分段信息
                if hasattr(response, 'segments') and response.segments:
                    result["segments"] = [
                        {
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text
                        }
                        for segment in response.segments
                    ]
                
                logger.info(f"🎤 Whisper转录成功: {result['text'][:50]}...")
                return result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"❌ Whisper转录失败: {str(e)}")
            raise Exception(f"Whisper转录失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.client or not self.api_key:
            return False
        
        try:
            # 创建一个很小的测试音频文件
            test_audio = b'\x52\x49\x46\x46\x24\x08\x00\x00\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00\x64\x61\x74\x61\x00\x08\x00\x00'
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(test_audio)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, "rb") as audio_file:
                    await self.client.audio.transcriptions.create(
                        model=self.model,
                        file=audio_file
                    )
                return True
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.warning(f"⚠️ Whisper服务不可用: {str(e)}")
            return False