"""
Paraformer-zh-streaming 基于 FunASR/ModelScope 的流式 ASR 提供商
支持流式增量识别，使用 chunk_size、encoder_chunk_look_back、decoder_chunk_look_back 等参数

参考：
- FunASR AutoModel 流式用法：
  https://github.com/modelscope/FunASR
- Paraformer-zh-streaming 模型：
  https://www.modelscope.cn/models/iic/paraformer-zh-streaming
"""

import asyncio
import wave
import numpy as np
import io
from typing import Any, Dict, Optional
from loguru import logger
from .base import BaseASRProvider


class ParaformerStreamingProvider(BaseASRProvider):
    """Paraformer-zh-streaming ASR 提供商（基于 FunASR AutoModel 流式）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 模型与设备配置
        self.model = config.get("model", "paraformer-zh-streaming")
        self.device = config.get("device", "cpu")
        self.hub = config.get("hub", "ms")
        self.trust_remote_code = config.get("trust_remote_code", True)
        self.remote_code = config.get("remote_code")
        
        # 流式参数配置
        # chunk_size = [0, 10, 5] 表示 600ms
        # chunk_size = [0, 8, 4] 表示 480ms
        self.chunk_size = config.get("chunk_size", [0, 10, 5])  # 默认600ms
        self.encoder_chunk_look_back = config.get("encoder_chunk_look_back", 4)  # encoder lookback
        self.decoder_chunk_look_back = config.get("decoder_chunk_look_back", 1)  # decoder lookback
        
        # 计算 chunk_stride（采样点数）
        # chunk_size[1] * 960 表示 chunk 的采样点数
        # 960 是 16kHz 采样率下 60ms 的采样点数 (16000 * 0.06 = 960)
        self.chunk_stride = self.chunk_size[1] * 960  # 默认 10 * 960 = 9600 采样点（600ms）
        
        # 静音检测配置
        self.silence_detection_enabled = config.get("silence_detection_enabled", True)
        self.silence_threshold = config.get("silence_threshold", 0.01)
        
        logger.info(f"📦 ParaformerStreaming 配置:")
        logger.info(f"   - 模型: {self.model}")
        logger.info(f"   - 设备: {self.device}")
        logger.info(f"   - chunk_size: {self.chunk_size} ({self.chunk_size[1] * 60}ms)")
        logger.info(f"   - encoder_chunk_look_back: {self.encoder_chunk_look_back}")
        logger.info(f"   - decoder_chunk_look_back: {self.decoder_chunk_look_back}")
        logger.info(f"   - chunk_stride: {self.chunk_stride} 采样点")
        
        if self.silence_detection_enabled:
            logger.info(f"🔇 静音检测已启用: 阈值={self.silence_threshold}")
        else:
            logger.info(f"🔇 静音检测未启用")

        # 启动时立即加载 AutoModel
        self._model = None
        self._load_model()
        # 每个客户端维护一份缓存与缓冲区
        self._sessions: Dict[str, Dict[str, Any]] = {}

    async def is_available(self) -> bool:
        """检查 FunASR 是否可用"""
        try:
            import funasr  # noqa: F401
            return True
        except Exception as e:
            logger.warning(f"ParaformerStreamingProvider: funasr 未安装或不可用: {e}")
            return False

    def _load_model(self):
        """在启动时加载 AutoModel"""
        if self._model is not None:
            return
        try:
            from funasr import AutoModel
            logger.info(
                f"📦 加载 Paraformer-zh-streaming 模型: {self.model} (hub={self.hub}, device={self.device})"
            )
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "device": self.device,
                "hub": self.hub,
            }
            if self.trust_remote_code:
                kwargs["trust_remote_code"] = True
                if self.remote_code:
                    kwargs["remote_code"] = self.remote_code

            self._model = AutoModel(**kwargs)
            logger.info(f"✅ Paraformer-zh-streaming 模型加载完成")
        except Exception as e:
            logger.error(f"❌ 加载 Paraformer-zh-streaming 失败: {e}")
            raise

    def _get_session(self, client_id: Optional[str]) -> Dict[str, Any]:
        """获取或创建客户端流式会话上下文"""
        key = client_id or "_default"
        if key not in self._sessions:
            self._sessions[key] = {
                "audio_buffer": [],  # 累积的音频采样点列表
                "cache": {},  # 传递给 AutoModel.generate 的缓存对象
                "last_text": "",
                "sample_rate": 16000,  # 默认采样率
            }
        return self._sessions[key]

    def _clear_session(self, client_id: Optional[str]):
        """清理会话缓存与缓冲区"""
        key = client_id or "_default"
        if key in self._sessions:
            del self._sessions[key]

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

    def _generate_sync(self, speech_chunk: np.ndarray, cache: dict, is_final: bool):
        """同步执行模型推理
        
        Args:
            speech_chunk: 音频采样点数组
            cache: 会话缓存对象
            is_final: 是否为最后一个chunk
            
        Returns:
            模型推理结果
        """
        return self._model.generate(
            input=speech_chunk,
            cache=cache,
            is_final=is_final,
            chunk_size=self.chunk_size,
            encoder_chunk_look_back=self.encoder_chunk_look_back,
            decoder_chunk_look_back=self.decoder_chunk_look_back,
        )

    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Optional[Dict[str, Any]]:
        """流式转录音频字节
        
        说明：前端以 WAV 分块推送，此处累积音频采样点，按 chunk_stride 切分处理
        """
        # 参数解析
        client_id: Optional[str] = kwargs.get("client_id")
        language: str = kwargs.get("language", self.language)
        is_final: bool = kwargs.get("is_final", False)

        # 确保模型已加载
        if self._model is None:
            raise RuntimeError("Paraformer-zh-streaming 模型未加载")
        
        # 静音检测：在传入FunASR之前检测新输入的音频是否为静音
  
        
        # 准备会话
        session = self._get_session(client_id)
        
        # 将WAV字节转换为采样点
        try:
            samples, sample_rate = self._wav_bytes_to_samples(audio_data)
            session["sample_rate"] = sample_rate
            
            # 累积到buffer
            session["audio_buffer"].extend(samples.tolist())
        except Exception as e:
            logger.error(f"❌ 音频解析失败: {e}")
            return None
        
        # 将buffer转换为numpy数组
        audio_buffer = np.array(session["audio_buffer"], dtype=np.float32)
        
        # 按chunk_stride切分处理
        total_chunk_num = int((len(audio_buffer) - 1) / self.chunk_stride + 1)
        
        # 只处理最后一个chunk（流式处理）
        if total_chunk_num > 0:
            i = total_chunk_num - 1
            start_idx = i * self.chunk_stride
            end_idx = (i + 1) * self.chunk_stride
            
            # 提取当前chunk
            speech_chunk = audio_buffer[start_idx:end_idx]
            
            # 如果是最后一个chunk或者是final，标记为final
            chunk_is_final = is_final or (i == total_chunk_num - 1 and len(speech_chunk) < self.chunk_stride)
            
            # 调用模型推理
            try:
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(
                    None,
                    self._generate_sync,
                    speech_chunk,
                    session["cache"],
                    chunk_is_final,
                )
                
                # 解析结果
                text = ""
                if isinstance(res, (list, tuple)) and len(res) > 0:
                    first = res[0]
                    if isinstance(first, dict):
                        text = first.get("text", "") or ""
                    elif isinstance(first, (list, tuple)) and len(first) > 0:
                        if isinstance(first[0], dict):
                            text = first[0].get("text", "") or ""
                
                # 清理文本
                text = text.strip() if text else ""
                
                # 获取上次识别的文本
                last_text = session.get("last_text", "")
                
                # 检测文本是否为空
                if not text and not chunk_is_final:
                    logger.debug(f"🔇 检测到空文本（静音），跳过返回结果")
                    return None
                
                # 检测文本是否与上次相同
                if text == last_text and text != "" and not chunk_is_final:
                    logger.debug(f"🔇 文本未变化（可能是静音），跳过返回结果: {text[:30] if text else ''}")
                    return None
                
                # 更新会话状态
                session["last_text"] = text
                
                # 判断句子结束（通过标点符号）
                sentence_end_punctuation = "。！？.!?"
                is_sentence_end = text and text[-1] in sentence_end_punctuation
                
                result = {
                    "text": text,
                    "language": language or "auto",
                    "duration": None,
                    "model": self.model,
                    "provider": "paraformer_streaming",
                    "confidence": 0.9,
                    "is_final": chunk_is_final,
                    "is_sentence_end": is_sentence_end,
                }
                
                if is_sentence_end:
                    logger.info(f"🎤 句子结束检测: {text[-30:] if len(text) > 30 else text}")
                
                return result
                
            except Exception as e:
                logger.error(f"❌ Paraformer-zh-streaming 识别失败: {e}")
                raise
        
        return None

    # 可选：供外部在 STOP 时调用进行清理
    def finalize_session(self, client_id: Optional[str]) -> Dict[str, Any]:
        """返回最后一次文本并清理会话"""
        sess = self._sessions.get(client_id or "_default")
        text = sess.get("last_text", "") if sess else ""
        self._clear_session(client_id)
        return {
            "text": text,
            "language": self.language,
            "model": self.model,
            "provider": "paraformer_streaming",
            "confidence": 0.9,
            "is_final": True,
        }

