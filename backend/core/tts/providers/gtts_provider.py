"""
GTTS 提供商实现
使用 Google Text-to-Speech 进行语音合成
"""

import tempfile
import os
import asyncio
from typing import Dict, Any
from loguru import logger

from .base import BaseTTSProvider


class GTTSProvider(BaseTTSProvider):
    """GTTS提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.gtts = None
        self.slow = config.get("slow", False)
        
        try:
            from gtts import gTTS
            self.gtts = gTTS
            logger.info(f"✅ GTTS初始化成功，语言: {self.language}")
        except ImportError:
            logger.error("❌ gtts库未安装，请运行: pip install gtts")
        except Exception as e:
            logger.error(f"❌ GTTS初始化失败: {str(e)}")
    
    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """合成语音"""
        if not self.gtts:
            raise Exception("GTTS未初始化")
        
        if not self.validate_text(text):
            raise Exception("无效的文本内容")
        
        try:
            # 获取参数
            language = kwargs.get("language", self.language)
            slow = kwargs.get("slow", self.slow)
            
            # 在线程池中执行同步操作
            loop = asyncio.get_event_loop()
            audio_data = await loop.run_in_executor(
                None,
                self._synthesize_sync,
                text,
                language,
                slow
            )
            
            result = {
                "audio_data": audio_data,
                "format": "mp3",
                "sample_rate": 24000,  # GTTS默认采样率
                "channels": 1,
                "duration": len(audio_data) / (24000 * 2),  # 估算时长
                "text": text,
                "voice": f"gtts-{language}",
                "language": language,
                "provider": "gtts",
                "model": f"gtts-{language}"
            }
            
            logger.info(f"🔊 GTTS合成成功: {text[:50]}... (语言: {language})")
            return result
            
        except Exception as e:
            logger.error(f"❌ GTTS合成失败: {str(e)}")
            raise Exception(f"GTTS合成失败: {str(e)}")
    
    def _synthesize_sync(self, text: str, language: str, slow: bool) -> bytes:
        """同步合成语音"""
        try:
            # 创建GTTS对象
            tts = self.gtts(
                text=text,
                lang=language,
                slow=slow
            )
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                # 保存音频
                tts.save(temp_file_path)
                
                # 读取音频数据
                with open(temp_file_path, "rb") as f:
                    audio_data = f.read()
                
                return audio_data
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise Exception(f"GTTS同步合成失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.gtts:
            return False
        
        try:
            # 测试网络连接
            import urllib.request
            urllib.request.urlopen("https://translate.google.com", timeout=5)
            
            # 测试简单的文本合成
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._test_synthesis
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ GTTS服务不可用: {str(e)}")
            return False
    
    def _test_synthesis(self):
        """测试合成功能"""
        try:
            tts = self.gtts(text="test", lang="en")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            try:
                tts.save(temp_file_path)
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            raise Exception(f"GTTS测试失败: {str(e)}")
    
    def get_supported_voices(self) -> list:
        """获取支持的语音列表"""
        # GTTS基于语言，没有特定的语音
        return [f"gtts-{lang}" for lang in self.get_supported_languages()]
    
    def get_supported_languages(self) -> list:
        """获取支持的语言列表"""
        return [
            "zh",     # 中文
            "zh-cn",  # 中文（简体）
            "zh-tw",  # 中文（繁体）
            "en",     # 英语
            "ja",     # 日语
            "ko",     # 韩语
            "fr",     # 法语
            "de",     # 德语
            "es",     # 西班牙语
            "it",     # 意大利语
            "pt",     # 葡萄牙语
            "ru",     # 俄语
            "ar",     # 阿拉伯语
            "hi",     # 印地语
            "th",     # 泰语
            "vi",     # 越南语
            "tr",     # 土耳其语
            "pl",     # 波兰语
            "nl",     # 荷兰语
            "sv"      # 瑞典语
        ]