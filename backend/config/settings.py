"""
应用配置管理
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Settings(BaseSettings):
    """应用配置类"""
    
    # 服务器配置
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8765, env="PORT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # LLM 配置
    llm_provider: str = Field(default="openai", env="LLM_PROVIDER")  # openai, anthropic, local
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # ASR 配置
    asr_provider: str = Field(default="whisper", env="ASR_PROVIDER")  # whisper, speech_recognition, sensevoice
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")  # tiny, base, small, medium, large
    # SenseVoiceSmall 配置
    sensevoice_enabled: bool = Field(default=True, env="SENSEVOICE_ENABLED")
    sensevoice_model: str = Field(default="iic/SenseVoiceSmall", env="SENSEVOICE_MODEL")
    sensevoice_device: str = Field(default="cpu", env="SENSEVOICE_DEVICE")
    sensevoice_hub: str = Field(default="ms", env="SENSEVOICE_HUB")
    sensevoice_trust_remote_code: bool = Field(default=True, env="SENSEVOICE_TRUST_REMOTE_CODE")
    sensevoice_vad_model: str = Field(default="fsmn-vad", env="SENSEVOICE_VAD_MODEL")
    
    # TTS 配置
    tts_provider: str = Field(default="edge", env="TTS_PROVIDER")  # edge, gtts, pyttsx3
    tts_voice: str = Field(default="zh-CN-XiaoxiaoNeural", env="TTS_VOICE")
    tts_rate: str = Field(default="+0%", env="TTS_RATE")
    tts_pitch: str = Field(default="+0Hz", env="TTS_PITCH")
    
    # 音频配置
    audio_sample_rate: int = Field(default=16000, env="AUDIO_SAMPLE_RATE")
    audio_chunk_size: int = Field(default=1024, env="AUDIO_CHUNK_SIZE")
    audio_format: str = Field(default="wav", env="AUDIO_FORMAT")
    
    # 文件路径配置
    audio_temp_dir: str = Field(default="temp/audio", env="AUDIO_TEMP_DIR")
    logs_dir: str = Field(default="logs", env="LOGS_DIR")
    models_dir: str = Field(default="models", env="MODELS_DIR")
    
    # 虚拟角色配置
    character_name: str = Field(default="Luna", env="CHARACTER_NAME")
    character_personality: str = Field(
        default="友善、聪明、乐于助人的虚拟助手",
        env="CHARACTER_PERSONALITY"
    )
    character_language: str = Field(default="zh-CN", env="CHARACTER_LANGUAGE")
    
    # 安全配置
    max_message_length: int = Field(default=1000, env="MAX_MESSAGE_LENGTH")
    max_audio_duration: int = Field(default=60, env="MAX_AUDIO_DURATION")  # 秒
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")  # 每分钟
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.audio_temp_dir,
            self.logs_dir,
            self.models_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    @property
    def llm_config(self) -> dict:
        """获取 LLM 配置"""
        config = {
            "provider": self.llm_provider,
            "character_name": self.character_name,
            "character_personality": self.character_personality,
            "language": self.character_language,
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_model
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model
            }
        }
        
        return config
    
    @property
    def asr_config(self) -> dict:
        """获取 ASR 配置"""
        return {
            "provider": self.asr_provider,
            "whisper": {
                "api_key": self.openai_api_key,
                "model": self.whisper_model,
                "language": self.character_language,
                "sample_rate": self.audio_sample_rate
            },
            "speech_recognition": {
                "enabled": True,
                "language": self.character_language,
                "sample_rate": self.audio_sample_rate
            },
            "sensevoice": {
                "enabled": self.sensevoice_enabled,
                "model": self.sensevoice_model,
                "device": self.sensevoice_device,
                "hub": self.sensevoice_hub,
                "trust_remote_code": self.sensevoice_trust_remote_code,
                "vad_model": self.sensevoice_vad_model,
                "language": self.character_language,
                "sample_rate": self.audio_sample_rate
            },
            "sample_rate": self.audio_sample_rate,
            "chunk_size": self.audio_chunk_size,
            "temp_dir": self.audio_temp_dir,
            "language": self.character_language
        }
    
    @property
    def tts_config(self) -> dict:
        """获取 TTS 配置"""
        return {
            "provider": self.tts_provider,
            "edge": {
                "enabled": True,
                "voice": self.tts_voice,
                "rate": self.tts_rate,
                "pitch": self.tts_pitch,
                "language": self.character_language
            },
            "gtts": {
                "enabled": True,
                "language": self.character_language,
                "slow": False
            },
            "pyttsx3": {
                "enabled": True,
                "voice": self.tts_voice,
                "rate": 200,
                "volume": 0.9
            },
            "temp_dir": self.audio_temp_dir,
            "language": self.character_language
        }
    
    def validate_api_keys(self) -> bool:
        """验证必要的 API 密钥是否存在"""
        if self.llm_provider == "openai" and not self.openai_api_key:
            return False
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            return False
        return True