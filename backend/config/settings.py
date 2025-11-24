"""
应用配置管理
"""

import os
import ast
from typing import Optional, List, Union
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
    debug: bool = Field(default=False, env="DEBUG")
    
    # LLM 配置
    llm_provider: str = Field(default="qwen3", env="LLM_PROVIDER")  # qwen3, openai, anthropic, local
    # Qwen3 配置
    qwen3_enabled: bool = Field(default=True, env="QWEN3_ENABLED")
    qwen3_model: str = Field(default="/home/leedow/.cache/modelscope/hub/models/Qwen/Qwen3-4B-Instruct-2507-FP8", env="QWEN3_MODEL")
    qwen3_dtype: str = Field(default="bfloat16", env="QWEN3_DTYPE")  # auto, float16, bfloat16
    qwen3_device_map: str = Field(default="auto", env="QWEN3_DEVICE_MAP")  # auto, cpu, cuda
    qwen3_attn_implementation: Optional[str] = Field(default=None, env="QWEN3_ATTN_IMPLEMENTATION")  # flash_attention_2
    qwen3_max_new_tokens: int = Field(default=512, env="QWEN3_MAX_NEW_TOKENS")
    qwen3_gpu_memory_utilization: float = Field(default=0.6, env="QWEN3_GPU_MEMORY_UTILIZATION")
    qwen3_max_model_len: int = Field(default=8192, env="QWEN3_MAX_MODEL_LEN")
    # OpenAI 配置
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    # Anthropic 配置
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # ASR 配置
    asr_provider: str = Field(default="paraformer_streaming", env="ASR_PROVIDER")  # whisper, speech_recognition, sensevoice, paraformer_streaming, fast_whisper
    whisper_model: str = Field(default="base", env="WHISPER_MODEL")  # tiny, base, small, medium, large
    # SenseVoiceSmall 配置
    sensevoice_enabled: bool = Field(default=True, env="SENSEVOICE_ENABLED")
    sensevoice_model: str = Field(default="iic/SenseVoiceSmall", env="SENSEVOICE_MODEL")
    sensevoice_device: str = Field(default="cuda", env="SENSEVOICE_DEVICE")
    sensevoice_hub: str = Field(default="ms", env="SENSEVOICE_HUB")
    sensevoice_trust_remote_code: bool = Field(default=True, env="SENSEVOICE_TRUST_REMOTE_CODE")
    sensevoice_vad_model: str = Field(default="fsmn-vad", env="SENSEVOICE_VAD_MODEL")
    # VAD 参数配置
    sensevoice_vad_max_single_segment_time: int = Field(default=30000, env="SENSEVOICE_VAD_MAX_SINGLE_SEGMENT_TIME")  # 毫秒
    sensevoice_vad_min_single_segment_time: int = Field(default=500, env="SENSEVOICE_VAD_MIN_SINGLE_SEGMENT_TIME")  # 毫秒
    sensevoice_vad_max_end_silence_time: int = Field(default=800, env="SENSEVOICE_VAD_MAX_END_SILENCE_TIME")  # 毫秒
    sensevoice_vad_threshold: float = Field(default=0.5, env="SENSEVOICE_VAD_THRESHOLD")  # VAD阈值
    # 滑动窗口配置
    sensevoice_sliding_window_enabled: bool = Field(default=True, env="SENSEVOICE_SLIDING_WINDOW_ENABLED")  # 是否启用滑动窗口
    sensevoice_window_size_bytes: int = Field(default=960000, env="SENSEVOICE_WINDOW_SIZE_BYTES")  # 窗口大小（字节），默认30秒
    
    # ParaformerStreaming 配置
    paraformer_streaming_enabled: bool = Field(default=True, env="PARAFORMER_STREAMING_ENABLED")
    paraformer_streaming_model: str = Field(default="paraformer-zh-streaming", env="PARAFORMER_STREAMING_MODEL")
    paraformer_streaming_device: str = Field(default="cuda", env="PARAFORMER_STREAMING_DEVICE")
    paraformer_streaming_hub: str = Field(default="ms", env="PARAFORMER_STREAMING_HUB")
    paraformer_streaming_trust_remote_code: bool = Field(default=True, env="PARAFORMER_STREAMING_TRUST_REMOTE_CODE")
    # 流式参数配置
    paraformer_streaming_chunk_size: str = Field(default="[0,10,5]", env="PARAFORMER_STREAMING_CHUNK_SIZE")  # chunk_size，默认600ms
    paraformer_streaming_encoder_chunk_look_back: int = Field(default=4, env="PARAFORMER_STREAMING_ENCODER_CHUNK_LOOK_BACK")  # encoder lookback
    paraformer_streaming_decoder_chunk_look_back: int = Field(default=1, env="PARAFORMER_STREAMING_DECODER_CHUNK_LOOK_BACK")  # decoder lookback
    # 静音检测配置
    paraformer_streaming_silence_detection_enabled: bool = Field(default=True, env="PARAFORMER_STREAMING_SILENCE_DETECTION_ENABLED")
    paraformer_streaming_silence_threshold: float = Field(default=0.01, env="PARAFORMER_STREAMING_SILENCE_THRESHOLD")
    
    # Fast-Whisper 配置
    fast_whisper_enabled: bool = Field(default=True, env="FAST_WHISPER_ENABLED")
    fast_whisper_model: str = Field(default="base", env="FAST_WHISPER_MODEL")  # tiny, base, small, medium, large, large-v2, large-v3
    fast_whisper_device: str = Field(default="cuda", env="FAST_WHISPER_DEVICE")  # cpu, cuda (默认使用GPU)
    fast_whisper_device_index: int = Field(default=0, env="FAST_WHISPER_DEVICE_INDEX")  # GPU索引
    fast_whisper_compute_type: str = Field(default="default", env="FAST_WHISPER_COMPUTE_TYPE")  # default, float16, int8, int8_float16
    # 识别参数
    fast_whisper_beam_size: int = Field(default=5, env="FAST_WHISPER_BEAM_SIZE")  # beam search大小
    fast_whisper_best_of: int = Field(default=5, env="FAST_WHISPER_BEST_OF")  # 候选数量
    fast_whisper_patience: float = Field(default=1.0, env="FAST_WHISPER_PATIENCE")  # patience参数
    fast_whisper_length_penalty: float = Field(default=1.0, env="FAST_WHISPER_LENGTH_PENALTY")  # 长度惩罚
    fast_whisper_temperature: float = Field(default=0.0, env="FAST_WHISPER_TEMPERATURE")  # 温度参数
    fast_whisper_compression_ratio_threshold: float = Field(default=2.4, env="FAST_WHISPER_COMPRESSION_RATIO_THRESHOLD")  # 压缩比阈值
    fast_whisper_log_prob_threshold: float = Field(default=-1.0, env="FAST_WHISPER_LOG_PROB_THRESHOLD")  # 对数概率阈值
    fast_whisper_no_speech_threshold: float = Field(default=0.6, env="FAST_WHISPER_NO_SPEECH_THRESHOLD")  # 无语音阈值
    fast_whisper_condition_on_previous_text: bool = Field(default=True, env="FAST_WHISPER_CONDITION_ON_PREVIOUS_TEXT")  # 是否基于前文
    fast_whisper_initial_prompt: Optional[str] = Field(default=None, env="FAST_WHISPER_INITIAL_PROMPT")  # 初始提示
    # VAD参数
    fast_whisper_vad_filter: bool = Field(default=False, env="FAST_WHISPER_VAD_FILTER")  # 是否启用VAD过滤
    # 静音检测配置
    fast_whisper_silence_detection_enabled: bool = Field(default=True, env="FAST_WHISPER_SILENCE_DETECTION_ENABLED")
    fast_whisper_silence_threshold: float = Field(default=0.01, env="FAST_WHISPER_SILENCE_THRESHOLD")
    
    # TTS 配置
    tts_provider: str = Field(default="zipvoice", env="TTS_PROVIDER")  # zipvoice, edge, gtts, pyttsx3, kokoro
    tts_voice: str = Field(default="zh-CN-XiaoxiaoNeural", env="TTS_VOICE")
    tts_rate: str = Field(default="+0%", env="TTS_RATE")
    tts_pitch: str = Field(default="+0Hz", env="TTS_PITCH")

    # ZipVoice 相关配置（HTTP API）
    tts_zipvoice_endpoint: str = Field(default="http://localhost:8005/tts", env="TTS_ZIPVOICE_ENDPOINT")
    tts_zipvoice_prompt_text: Optional[str] = Field(default=None, env="TTS_ZIPVOICE_PROMPT_TEXT")
    tts_zipvoice_prompt_wav_path: Optional[str] = Field(default=None, env="TTS_ZIPVOICE_PROMPT_WAV_PATH")
    tts_zipvoice_return_metrics: bool = Field(default=False, env="TTS_ZIPVOICE_RETURN_METRICS")
    tts_zipvoice_raw_evaluation: bool = Field(default=False, env="TTS_ZIPVOICE_RAW_EVALUATION")
    
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
    
    def _parse_chunk_size(self, chunk_size: Union[str, List[int]]) -> List[int]:
        """解析chunk_size字符串为列表
        
        Args:
            chunk_size: chunk_size字符串或列表
            
        Returns:
            List[int]: chunk_size列表
        """
        if isinstance(chunk_size, list):
            return chunk_size
        elif isinstance(chunk_size, str):
            try:
                # 使用ast.literal_eval安全地解析字符串
                parsed = ast.literal_eval(chunk_size)
                if isinstance(parsed, list) and all(isinstance(x, int) for x in parsed):
                    return parsed
                else:
                    raise ValueError(f"chunk_size必须是整数列表: {chunk_size}")
            except (ValueError, SyntaxError) as e:
                # 如果解析失败，使用默认值
                return [0, 10, 5]
        else:
            return [0, 10, 5]  # 默认值
    
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
                "vad_kwargs": {
                    "max_single_segment_time": self.sensevoice_vad_max_single_segment_time,
                    "min_single_segment_time": self.sensevoice_vad_min_single_segment_time,
                    "max_end_silence_time": self.sensevoice_vad_max_end_silence_time,
                    "threshold": self.sensevoice_vad_threshold,
                },
                "sliding_window_enabled": self.sensevoice_sliding_window_enabled,  # 滑动窗口启用开关
                "window_size_bytes": self.sensevoice_window_size_bytes,  # 窗口大小（字节）
                "language": self.character_language,
                "sample_rate": self.audio_sample_rate
            },
            "paraformer_streaming": {
                "enabled": self.paraformer_streaming_enabled,
                "model": self.paraformer_streaming_model,
                "device": self.paraformer_streaming_device,
                "hub": self.paraformer_streaming_hub,
                "trust_remote_code": self.paraformer_streaming_trust_remote_code,
                "chunk_size": self._parse_chunk_size(self.paraformer_streaming_chunk_size),  # 解析chunk_size字符串为列表
                "encoder_chunk_look_back": self.paraformer_streaming_encoder_chunk_look_back,
                "decoder_chunk_look_back": self.paraformer_streaming_decoder_chunk_look_back,
                "silence_detection_enabled": self.paraformer_streaming_silence_detection_enabled,
                "silence_threshold": self.paraformer_streaming_silence_threshold,
                "language": self.character_language,
                "sample_rate": self.audio_sample_rate
            },
            "fast_whisper": {
                "enabled": self.fast_whisper_enabled,
                "model": self.fast_whisper_model,
                "device": self.fast_whisper_device,
                "device_index": self.fast_whisper_device_index,
                "compute_type": self.fast_whisper_compute_type,
                "beam_size": self.fast_whisper_beam_size,
                "best_of": self.fast_whisper_best_of,
                "patience": self.fast_whisper_patience,
                "length_penalty": self.fast_whisper_length_penalty,
                "temperature": self.fast_whisper_temperature,
                "compression_ratio_threshold": self.fast_whisper_compression_ratio_threshold,
                "log_prob_threshold": self.fast_whisper_log_prob_threshold,
                "no_speech_threshold": self.fast_whisper_no_speech_threshold,
                "condition_on_previous_text": self.fast_whisper_condition_on_previous_text,
                "initial_prompt": self.fast_whisper_initial_prompt,
                "vad_filter": self.fast_whisper_vad_filter,
                "silence_detection_enabled": self.fast_whisper_silence_detection_enabled,
                "silence_threshold": self.fast_whisper_silence_threshold,
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
            "zipvoice": {
                "enabled": True,
                "endpoint": self.tts_zipvoice_endpoint,
                "prompt_text": self.tts_zipvoice_prompt_text,
                "prompt_wav_path": self.tts_zipvoice_prompt_wav_path,
                "return_metrics": self.tts_zipvoice_return_metrics,
                "raw_evaluation": self.tts_zipvoice_raw_evaluation,
                "language": self.character_language,
                "voice": self.tts_voice,
            },
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