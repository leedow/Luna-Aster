"""
音频处理工具模块
提供音频格式转换、编码解码等功能
"""

import base64
import io
import wave
import numpy as np
from typing import Optional, Tuple
from loguru import logger

def encode_audio_to_base64(audio_data: bytes) -> str:
    """将音频数据编码为base64字符串"""
    try:
        return base64.b64encode(audio_data).decode('utf-8')
    except Exception as e:
        logger.error(f"❌ 音频编码失败: {str(e)}")
        raise

def decode_audio_from_base64(audio_base64: str) -> bytes:
    """将base64字符串解码为音频数据"""
    try:
        return base64.b64decode(audio_base64)
    except Exception as e:
        logger.error(f"❌ 音频解码失败: {str(e)}")
        raise

def convert_audio_format(audio_data: bytes, target_format: str = "wav") -> bytes:
    """转换音频格式"""
    try:
        # 这里可以添加更复杂的音频格式转换逻辑
        # 目前简单返回原数据
        return audio_data
    except Exception as e:
        logger.error(f"❌ 音频格式转换失败: {str(e)}")
        raise

def validate_audio_data(audio_data: bytes, max_size: int = 10 * 1024 * 1024) -> bool:
    """验证音频数据"""
    try:
        # 检查数据大小
        if len(audio_data) > max_size:
            logger.warning(f"⚠️ 音频数据过大: {len(audio_data)} bytes")
            return False
        
        # 检查数据是否为空
        if len(audio_data) == 0:
            logger.warning("⚠️ 音频数据为空")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 音频数据验证失败: {str(e)}")
        return False

def get_audio_duration(audio_data: bytes, sample_rate: int = 16000) -> float:
    """获取音频时长（秒）"""
    try:
        # 简单估算，实际应该根据音频格式解析
        return len(audio_data) / (sample_rate * 2)  # 假设16位音频
    except Exception as e:
        logger.error(f"❌ 获取音频时长失败: {str(e)}")
        return 0.0

def create_silence_audio(duration: float, sample_rate: int = 16000) -> bytes:
    """创建静音音频数据"""
    try:
        samples = int(duration * sample_rate)
        silence = np.zeros(samples, dtype=np.int16)
        
        # 转换为WAV格式
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(silence.tobytes())
        
        return buffer.getvalue()
    except Exception as e:
        logger.error(f"❌ 创建静音音频失败: {str(e)}")
        raise