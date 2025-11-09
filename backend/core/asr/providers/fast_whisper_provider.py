"""
Fast-Whisper ASR 提供商实现
使用 faster-whisper 库进行快速语音识别

参考：
- faster-whisper 文档：
  https://github.com/guillaumekln/faster-whisper
- Whisper 模型：
  https://github.com/openai/whisper
"""

import asyncio
import tempfile
import os
import wave
import numpy as np
import io
from typing import Dict, Any, Optional
from loguru import logger
from .base import BaseASRProvider


class FastWhisperProvider(BaseASRProvider):
    """Fast-Whisper ASR 提供商（基于 faster-whisper）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 模型配置
        self.model = config.get("model", "base")  # tiny, base, small, medium, large, large-v2, large-v3
        self.device = config.get("device", "cuda")  # cpu, cuda (默认使用GPU)
        self.device_index = config.get("device_index", 0)  # GPU索引
        self.compute_type = config.get("compute_type", "default")  # default, float16, int8, int8_float16
        
        # 识别参数
        self.language = config.get("language", "zh")  # 语言代码
        self.beam_size = config.get("beam_size", 5)  # beam search大小
        self.best_of = config.get("best_of", 5)  # 候选数量
        self.patience = config.get("patience", 1.0)  # patience参数
        self.length_penalty = config.get("length_penalty", 1.0)  # 长度惩罚
        self.temperature = config.get("temperature", 0.0)  # 温度参数
        self.compression_ratio_threshold = config.get("compression_ratio_threshold", 2.4)  # 压缩比阈值
        self.log_prob_threshold = config.get("log_prob_threshold", -1.0)  # 对数概率阈值
        self.no_speech_threshold = config.get("no_speech_threshold", 0.6)  # 无语音阈值
        self.condition_on_previous_text = config.get("condition_on_previous_text", True)  # 是否基于前文
        self.initial_prompt = config.get("initial_prompt", None)  # 初始提示
        
        # VAD参数
        self.vad_filter = config.get("vad_filter", False)  # 是否启用VAD过滤
        self.vad_parameters = config.get("vad_parameters", {})  # VAD参数
        
        # 静音检测配置
        self.silence_detection_enabled = config.get("silence_detection_enabled", True)
        self.silence_threshold = config.get("silence_threshold", 0.01)
        
        logger.info(f"📦 Fast-Whisper 配置:")
        logger.info(f"   - 模型: {self.model}")
        logger.info(f"   - 设备: {self.device}")
        logger.info(f"   - 语言: {self.language}")
        logger.info(f"   - beam_size: {self.beam_size}")
        logger.info(f"   - compute_type: {self.compute_type}")
        
        if self.silence_detection_enabled:
            logger.info(f"🔇 静音检测已启用: 阈值={self.silence_threshold}")
        else:
            logger.info(f"🔇 静音检测未启用")
        
        # 启动时延迟加载模型（避免启动时阻塞）
        self._model = None
        self._model_loaded = False

    async def is_available(self) -> bool:
        """检查 faster-whisper 是否可用"""
        try:
            from faster_whisper import WhisperModel  # noqa: F401
            return True
        except Exception as e:
            logger.warning(f"FastWhisperProvider: faster-whisper 未安装或不可用: {e}")
            return False

    def _load_model(self):
        """加载 WhisperModel（延迟加载）"""
        if self._model is not None:
            return
        
        try:
            from faster_whisper import WhisperModel
            
            logger.info(
                f"📦 加载 Fast-Whisper 模型: {self.model} (device={self.device}, compute_type={self.compute_type})"
            )
            
            # 构建模型参数
            model_kwargs = {
                "device": self.device,
                "device_index": self.device_index,
                "compute_type": self.compute_type,
            }
            
            # 如果compute_type是default，根据设备自动选择
            if self.compute_type == "default":
                if self.device == "cuda":
                    model_kwargs["compute_type"] = "float16"
                else:
                    model_kwargs["compute_type"] = "int8"
            
            # 尝试加载模型，如果GPU不可用，自动回退到CPU
            try:
                self._model = WhisperModel(self.model, **model_kwargs)
                self._model_loaded = True
                logger.info(f"✅ Fast-Whisper 模型加载完成 (device={self.device}, compute_type={model_kwargs['compute_type']})")
            except Exception as gpu_error:
                # 如果GPU加载失败，尝试回退到CPU
                if self.device == "cuda":
                    logger.warning(f"⚠️ GPU加载失败: {gpu_error}，尝试回退到CPU")
                    model_kwargs["device"] = "cpu"
                    model_kwargs["compute_type"] = "int8"
                    try:
                        self._model = WhisperModel(self.model, **model_kwargs)
                        self._model_loaded = True
                        self.device = "cpu"  # 更新设备配置
                        logger.info(f"✅ Fast-Whisper 模型加载完成 (回退到CPU, compute_type=int8)")
                    except Exception as cpu_error:
                        logger.error(f"❌ CPU加载也失败: {cpu_error}")
                        raise cpu_error
                else:
                    raise gpu_error
                    
        except ImportError as e:
            logger.error(f"❌ faster-whisper 未安装: {e}")
            raise RuntimeError(f"faster-whisper 未安装，请运行: pip install faster-whisper")
        except Exception as e:
            logger.error(f"❌ 加载 Fast-Whisper 失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise

    def _wav_bytes_to_samples(self, wav_data: bytes) -> tuple:
        """将WAV字节数据转换为采样点数组
        
        Args:
            wav_data: WAV格式的字节数据
            
        Returns:
            tuple: (samples, sample_rate) 采样点数组和采样率
        """
        try:
            wav_io = io.BytesIO(wav_data)
            with wave.open(wav_io, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                frames = wav_file.readframes(n_frames)
                
                # 转换为numpy数组
                sample_width = wav_file.getsampwidth()
                if sample_width == 2:  # 16-bit
                    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                elif sample_width == 4:  # 32-bit
                    samples = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
                else:
                    raise ValueError(f"不支持的采样位深度: {sample_width}")
                
                return samples, sample_rate
        except Exception as e:
            logger.error(f"❌ WAV解析失败: {e}")
            raise

    def _is_silence_audio(self, audio_data: bytes) -> bool:
        """检测音频是否为静音"""
        if not self.silence_detection_enabled:
            return False
        
        if not audio_data or len(audio_data) < 44:
            return True
        
        try:
            samples, _ = self._wav_bytes_to_samples(audio_data)
            if len(samples) == 0:
                return True
            
            # 计算音频幅度的标准差
            amplitude = np.abs(samples)
            std = np.std(amplitude)
            is_silence = std < self.silence_threshold
            
            if is_silence:
                logger.debug(f"🔇 检测到静音: std={std:.6f} < threshold={self.silence_threshold}")
            
            return is_silence
        except Exception as e:
            logger.debug(f"🔇 静音检测失败: {e}，假设不是静音")
            return False

    def _transcribe_sync(self, audio_file_path: str) -> Dict[str, Any]:
        """同步执行模型推理
        
        Args:
            audio_file_path: 音频文件路径
            
        Returns:
            模型推理结果
        """
        # 构建识别参数
        transcribe_kwargs = {
            "language": self.language if self.language != "auto" else None,
            "beam_size": self.beam_size,
            "best_of": self.best_of,
            "patience": self.patience,
            "length_penalty": self.length_penalty,
            "temperature": self.temperature,
            "compression_ratio_threshold": self.compression_ratio_threshold,
            "log_prob_threshold": self.log_prob_threshold,
            "no_speech_threshold": self.no_speech_threshold,
            "condition_on_previous_text": self.condition_on_previous_text,
        }
        
        # 添加初始提示
        if self.initial_prompt:
            transcribe_kwargs["initial_prompt"] = self.initial_prompt
        
        # 添加VAD参数
        if self.vad_filter:
            transcribe_kwargs["vad_filter"] = True
            if self.vad_parameters:
                transcribe_kwargs["vad_parameters"] = self.vad_parameters
        
        # 执行识别
        segments, info = self._model.transcribe(audio_file_path, **transcribe_kwargs)
        
        # 收集所有分段
        text_segments = []
        full_text = ""
        
        for segment in segments:
            segment_text = segment.text.strip()
            if segment_text:
                text_segments.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment_text
                })
                full_text += segment_text
        
        # 构建结果
        result = {
            "text": full_text.strip(),
            "language": info.language if hasattr(info, 'language') else self.language,
            "language_probability": info.language_probability if hasattr(info, 'language_probability') else 0.0,
            "duration": info.duration if hasattr(info, 'duration') else 0.0,
            "model": self.model,
            "provider": "fast_whisper",
            "confidence": 0.9,  # faster-whisper不直接提供置信度
            "segments": text_segments if text_segments else None,
        }
        
        return result

    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Optional[Dict[str, Any]]:
        """转录音频"""
        try:
            # 确保模型已加载
            if self._model is None:
                try:
                    self._load_model()
                except Exception as load_error:
                    logger.error(f"❌ Fast-Whisper 模型加载失败: {load_error}")
                    raise RuntimeError(f"Fast-Whisper 模型加载失败: {load_error}")
            
            if self._model is None:
                raise RuntimeError("Fast-Whisper 模型未加载")
            
            # 验证音频数据
            if not audio_data or len(audio_data) == 0:
                logger.debug(f"🔇 音频数据为空，跳过处理")
                return None
            
            # 静音检测：在传入模型之前检测新输入的音频是否为静音
            if self.silence_detection_enabled:
                try:
                    is_silence_input = self._is_silence_audio(audio_data)
                    if is_silence_input:
                        logger.debug(f"🔇 检测到静音输入，跳过处理 (大小: {len(audio_data)}字节)")
                        return None
                except Exception as silence_error:
                    logger.debug(f"🔇 静音检测失败: {silence_error}，继续处理")
            
            if not self.validate_audio_format(audio_data):
                logger.warning(f"⚠️ 无效的音频格式，大小: {len(audio_data)}字节")
                raise Exception("无效的音频格式")
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # 在线程池中执行识别（因为faster-whisper是同步的）
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._transcribe_sync,
                    temp_file_path,
                )
                
                # 清理文本
                text = result.get("text", "").strip()
                
                # 检测文本是否为空
                if not text:
                    logger.debug(f"🔇 检测到空文本（静音），跳过返回结果")
                    return None
                
                result["text"] = text
                
                logger.info(f"🎤 Fast-Whisper转录成功: {text[:50]}...")
                return result
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ 清理临时文件失败: {cleanup_error}")
                    
        except RuntimeError:
            # 重新抛出RuntimeError
            raise
        except Exception as e:
            logger.error(f"❌ Fast-Whisper转录失败: {str(e)}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            raise Exception(f"Fast-Whisper转录失败: {str(e)}")

