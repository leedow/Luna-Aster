"""
Pyttsx3 提供商实现
使用 pyttsx3 进行本地语音合成
"""

import tempfile
import os
import asyncio
from typing import Dict, Any
from loguru import logger

from .base import BaseTTSProvider


class Pyttsx3Provider(BaseTTSProvider):
    """Pyttsx3提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.engine = None
        self.driver = config.get("driver", None)  # 'sapi5', 'nsss', 'espeak'
        
        try:
            import pyttsx3
            self.pyttsx3 = pyttsx3
            self._init_engine()
            logger.info(f"✅ Pyttsx3初始化成功，语音: {self.voice}")
        except ImportError:
            logger.error("❌ pyttsx3库未安装，请运行: pip install pyttsx3")
            self.pyttsx3 = None
        except Exception as e:
            logger.error(f"❌ Pyttsx3初始化失败: {str(e)}")
            self.pyttsx3 = None
    
    def _init_engine(self):
        """初始化TTS引擎"""
        try:
            if self.driver:
                self.engine = self.pyttsx3.init(driverName=self.driver)
            else:
                self.engine = self.pyttsx3.init()
            
            # 设置语音参数
            if self.engine:
                # 设置语速
                self.engine.setProperty('rate', int(200 * self.rate))
                
                # 设置音量
                self.engine.setProperty('volume', 1.0)
                
                # 设置语音
                voices = self.engine.getProperty('voices')
                if voices and self.voice != "default":
                    for voice in voices:
                        if self.voice in voice.id or self.voice in voice.name:
                            self.engine.setProperty('voice', voice.id)
                            break
                            
        except Exception as e:
            logger.error(f"❌ Pyttsx3引擎初始化失败: {str(e)}")
            self.engine = None
    
    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """合成语音"""
        if not self.pyttsx3 or not self.engine:
            raise Exception("Pyttsx3未初始化")
        
        if not self.validate_text(text):
            raise Exception("无效的文本内容")
        
        try:
            # 获取参数
            rate = kwargs.get("rate", self.rate)
            voice = kwargs.get("voice", self.voice)
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                self._synthesize_sync,
                text,
                rate,
                voice
            )
            
            result = {
                "audio_data": audio_data,
                "format": "wav",
                "sample_rate": 22050,  # Pyttsx3默认采样率
                "channels": 1,
                "duration": len(audio_data) / (22050 * 2),  # 估算时长
                "text": text,
                "voice": voice,
                "language": self.language,
                "provider": "pyttsx3",
                "model": f"pyttsx3-{voice}"
            }
            
            logger.info(f"🔊 Pyttsx3合成成功: {text[:50]}... (语音: {voice})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Pyttsx3合成失败: {str(e)}")
            raise Exception(f"Pyttsx3合成失败: {str(e)}")
    
    def _synthesize_sync(self, text: str, rate: float, voice: str) -> bytes:
        """同步合成语音"""
        try:
            # 更新引擎设置
            self.engine.setProperty('rate', int(200 * rate))
            
            # 设置语音
            if voice != "default":
                voices = self.engine.getProperty('voices')
                if voices:
                    for v in voices:
                        if voice in v.id or voice in v.name:
                            self.engine.setProperty('voice', v.id)
                            break
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                # 保存到文件
                self.engine.save_to_file(text, temp_file_path)
                self.engine.runAndWait()
                
                # 读取音频数据
                with open(temp_file_path, "rb") as f:
                    audio_data = f.read()
                
                return audio_data
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise Exception(f"Pyttsx3同步合成失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.pyttsx3 or not self.engine:
            return False
        
        try:
            # 测试引擎是否正常工作
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._test_synthesis
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Pyttsx3服务不可用: {str(e)}")
            return False
    
    def _test_synthesis(self):
        """测试合成功能"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                self.engine.save_to_file("test", temp_file_path)
                self.engine.runAndWait()
                
                # 检查文件是否生成
                if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                    raise Exception("生成的音频文件为空")
                    
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise Exception(f"Pyttsx3测试失败: {str(e)}")
    
    def get_supported_voices(self) -> list:
        """获取支持的语音列表"""
        if not self.engine:
            return ["default"]
        
        try:
            voices = self.engine.getProperty('voices')
            if voices:
                return [voice.id for voice in voices]
            else:
                return ["default"]
        except Exception:
            return ["default"]
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        # Pyttsx3支持的语言取决于系统安装的TTS引擎
        return [
            "en-US",  # 英语（美国）
            "en-GB",  # 英语（英国）
            "zh-CN",  # 中文（简体）
            "zh-TW",  # 中文（繁体）
            "ja-JP",  # 日语
            "ko-KR",  # 韩语
            "fr-FR",  # 法语
            "de-DE",  # 德语
            "es-ES",  # 西班牙语
            "it-IT",  # 意大利语
            "pt-BR",  # 葡萄牙语
            "ru-RU"   # 俄语
        ]