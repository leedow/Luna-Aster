"""
ASR Providers 模块
提供统一的语音识别接口和多种实现
"""

from .base import BaseASRProvider
from .whisper_provider import WhisperProvider
from .speech_recognition_provider import SpeechRecognitionProvider
from .mock_provider import MockASRProvider
from .sensevoice_provider import SenseVoiceSmallProvider
from .factory import ASRProviderFactory

__all__ = [
    "BaseASRProvider",
    "WhisperProvider", 
    "SpeechRecognitionProvider",
    "MockASRProvider",
    "SenseVoiceSmallProvider",
    "ASRProviderFactory"
]