"""
SpeechRecognition ASR 提供商实现
使用 speech_recognition 库进行语音识别
"""

import io
import tempfile
import os
import asyncio
from typing import Dict, Any
from loguru import logger

from .base import BaseASRProvider


class SpeechRecognitionProvider(BaseASRProvider):
    """SpeechRecognition ASR提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.recognizer = None
        self.engine = config.get("engine", "google")  # google, sphinx, wit, bing等
        
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            logger.info(f"✅ SpeechRecognition初始化成功，引擎: {self.engine}")
        except ImportError:
            logger.error("❌ speech_recognition库未安装，请运行: pip install SpeechRecognition")
        except Exception as e:
            logger.error(f"❌ SpeechRecognition初始化失败: {str(e)}")
    
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """转录音频"""
        if not self.recognizer:
            raise Exception("SpeechRecognition未初始化")
        
        if not self.validate_audio_format(audio_data):
            raise Exception("无效的音频格式")
        
        try:
            import speech_recognition as sr
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # 读取音频文件
                with sr.AudioFile(temp_file_path) as source:
                    audio = self.recognizer.record(source)
                
                # 在线程池中执行识别（因为speech_recognition是同步的）
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(
                    None, 
                    self._recognize_audio, 
                    audio
                )
                
                result = {
                    "text": text,
                    "language": self.language,
                    "duration": 0,  # speech_recognition不提供时长信息
                    "model": self.engine,
                    "provider": "speech_recognition",
                    "confidence": 0.8  # 默认置信度
                }
                
                logger.info(f"🎤 SpeechRecognition转录成功: {result['text'][:50]}...")
                return result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"❌ SpeechRecognition转录失败: {str(e)}")
            raise Exception(f"SpeechRecognition转录失败: {str(e)}")
    
    def _recognize_audio(self, audio) -> str:
        """执行音频识别（同步方法）"""
        import speech_recognition as sr
        
        try:
            if self.engine == "google":
                return self.recognizer.recognize_google(audio, language=self.language)
            elif self.engine == "sphinx":
                return self.recognizer.recognize_sphinx(audio, language=self.language)
            elif self.engine == "wit":
                # 需要配置WIT_AI_KEY
                wit_key = self.config.get("wit_key")
                if not wit_key:
                    raise Exception("Wit.ai需要API密钥")
                return self.recognizer.recognize_wit(audio, key=wit_key)
            elif self.engine == "bing":
                # 需要配置BING_KEY
                bing_key = self.config.get("bing_key")
                if not bing_key:
                    raise Exception("Bing需要API密钥")
                return self.recognizer.recognize_bing(audio, key=bing_key, language=self.language)
            else:
                # 默认使用Google
                return self.recognizer.recognize_google(audio, language=self.language)
                
        except sr.UnknownValueError:
            raise Exception("无法识别音频内容")
        except sr.RequestError as e:
            raise Exception(f"识别服务请求失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.recognizer:
            return False
        
        try:
            # 对于本地引擎（如sphinx），总是可用
            if self.engine == "sphinx":
                return True
            
            # 对于在线服务，尝试简单的网络检查
            import urllib.request
            
            if self.engine == "google":
                urllib.request.urlopen("https://www.google.com", timeout=5)
                return True
            elif self.engine == "wit":
                return bool(self.config.get("wit_key"))
            elif self.engine == "bing":
                return bool(self.config.get("bing_key"))
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ SpeechRecognition服务不可用: {str(e)}")
            return False