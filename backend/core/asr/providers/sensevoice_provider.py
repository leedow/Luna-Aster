"""
SenseVoiceSmall 基于 FunASR/ModelScope 的 ASR 提供商
支持以音频字节流进行推理，面向流式增量识别场景。

参考：
- FunASR AutoModel 用法（支持音频字节输入与缓存）：
  https://github.com/modelscope/FunASR
- SenseVoiceSmall 模型：
  https://www.modelscope.cn/models/iic/SenseVoiceSmall
"""

import asyncio
import io
import wave
from typing import Any, Dict, Optional, Tuple, Union
from loguru import logger
from .base import BaseASRProvider

class SenseVoiceSmallProvider(BaseASRProvider):
    """SenseVoiceSmall ASR 提供商（基于 FunASR AutoModel）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 模型与设备配置
        self.model = config.get("model", "iic/SenseVoiceSmall")
        self.device = "cuda"  # 默认为 GPU，确保在支持的环境上可运行
        self.hub = config.get("hub", "ms")  # 模型来源：ModelScope(ms) 或 HuggingFace(hf)
        self.trust_remote_code = config.get("trust_remote_code", True)
        self.remote_code = config.get("remote_code")  # 可选，通常无需设置

        # 启动时立即加载 AutoModel
        self._model = None
        self._load_model()
        # 每个客户端维护一份缓存与缓冲区，用于流式增量解码
        self._sessions: Dict[str, Dict[str, Any]] = {}

    async def is_available(self) -> bool:
        """检查 FunASR 是否可用（仅测试 import）"""
        try:
            import funasr  # noqa: F401
            return True
        except Exception as e:
            logger.warning(f"SenseVoiceSmallProvider: funasr 未安装或不可用: {e}")
            return False

    def _load_model(self):
        """在启动时加载 AutoModel"""
        if self._model is not None:
            return
        try:
            from funasr import AutoModel
            logger.info(
                f"📦 加载 SenseVoiceSmall 模型: {self.model} (hub={self.hub}, device={self.device})"
            )
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "device": self.device,
                "hub": self.hub,
            }
            # 兼容可选 remote_code
            if self.trust_remote_code:
                kwargs["trust_remote_code"] = True
                if self.remote_code:
                    kwargs["remote_code"] = self.remote_code

            self._model = AutoModel(**kwargs)
            logger.info(f"✅ SenseVoiceSmall 模型加载完成")
                
        except Exception as e:
            logger.error(f"❌ 加载 SenseVoiceSmall 失败: {e}")
            raise

    def _get_session(self, client_id: Optional[str]) -> Dict[str, Any]:
        """获取或创建客户端流式会话上下文"""
        key = client_id or "_default"
        if key not in self._sessions:
            self._sessions[key] = {
                "buffer": bytearray(),  # 累积音频字节
                "cache": {},            # 传递给 AutoModel.generate 的缓存对象
                "last_text": "",
            }
        return self._sessions[key]

    def _clear_session(self, client_id: Optional[str]):
        """清理会话缓存与缓冲区"""
        key = client_id or "_default"
        if key in self._sessions:
            del self._sessions[key]
    
    def _pcm_to_numpy(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> Tuple[Any, int]:  # type: ignore
        """将 PCM 字节数据直接转换为 numpy 数组
        
        Args:
            pcm_data: PCM 音频字节数据（16-bit signed integer）
            sample_rate: 采样率
            channels: 声道数
            sample_width: 采样宽度（字节），2 = 16-bit
            
        Returns:
            (audio_array, sample_rate): numpy 数组和采样率
        """
        try:
            import numpy as np
            
            # 根据采样宽度选择数据类型
            if sample_width == 2:  # 16-bit
                audio_array = np.frombuffer(pcm_data, dtype=np.int16)
            elif sample_width == 4:  # 32-bit
                audio_array = np.frombuffer(pcm_data, dtype=np.int32)
            else:
                audio_array = np.frombuffer(pcm_data, dtype=np.uint8)
            
            # 如果是多声道，取第一个声道
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)[:, 0]
            
            # 归一化到 [-1.0, 1.0]
            if sample_width == 2:
                audio_array = audio_array.astype(np.float32) / 32768.0
            elif sample_width == 4:
                audio_array = audio_array.astype(np.float32) / 2147483648.0
            else:
                audio_array = audio_array.astype(np.float32) / 128.0 - 1.0
            
            logger.debug(f"✅ PCM 转换成功: {len(pcm_data)}B → {len(audio_array)} 采样点, {sample_rate}Hz")
            return audio_array, sample_rate
        except Exception as e:
            logger.error(f"❌ PCM 转 numpy 失败: {e}")
            raise

    def _wav_to_numpy(self, wav_data: bytes, sample_rate: int = 16000) -> Tuple[Any, int]:  # type: ignore
        """将 WAV 字节数据转换为 numpy 数组
        
        Args:
            wav_data: WAV 格式的字节数据
            sample_rate: 目标采样率（默认 16000）
            
        Returns:
            tuple: (audio_array, actual_sample_rate) numpy 数组和实际采样率
        """
        try:
            import numpy as np
            
            # 先合并多个 WAV 块（如果有）
            merged_wav = self._merge_wav_chunks(wav_data)
            
            # 读取 WAV 文件
            wav_io = io.BytesIO(merged_wav)
            with wave.open(wav_io, 'rb') as wav_file:
                actual_sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                n_frames = wav_file.getnframes()
                frames = wav_file.readframes(n_frames)
            
            # 转换为 numpy 数组
            if sample_width == 2:  # 16-bit
                audio_array = np.frombuffer(frames, dtype=np.int16)
            elif sample_width == 4:  # 32-bit
                audio_array = np.frombuffer(frames, dtype=np.int32)
            else:
                audio_array = np.frombuffer(frames, dtype=np.uint8)
            
            # 如果是多声道，只取第一声道
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)[:, 0]
            
            # 转换为 float32 并归一化到 [-1, 1]
            audio_array = audio_array.astype(np.float32) / 32768.0
            
            # 如果需要重采样
            if actual_sample_rate != sample_rate:
                # 简单的线性重采样（如果需要更高质量，可以使用 scipy.signal.resample）
                ratio = sample_rate / actual_sample_rate
                new_length = int(len(audio_array) * ratio)
                indices = np.linspace(0, len(audio_array) - 1, new_length)
                audio_array = np.interp(indices, np.arange(len(audio_array)), audio_array)
                actual_sample_rate = sample_rate
            
            return audio_array, actual_sample_rate
            
        except Exception as e:
            logger.error(f"❌ WAV 转 numpy 失败: {e}")
            raise
    
    def _parse_wav_header(self, wav_data: bytes) -> Tuple[int, int, int]:
        """解析 WAV 头，获取采样率、声道数、位深度
        
        Args:
            wav_data: WAV 格式的字节数据
            
        Returns:
            tuple: (sample_rate, channels, sample_width) 采样率、声道数、位深度
        """
        try:
            if len(wav_data) < 44 or not wav_data.startswith(b'RIFF'):
                # 默认值：16kHz, 单声道, 16-bit
                return 16000, 1, 2
            
            wav_io = io.BytesIO(wav_data)
            with wave.open(wav_io, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                return sample_rate, channels, sample_width
        except Exception as e:
            logger.warning(f"⚠️ WAV头解析失败: {e}, 使用默认值")
            return 16000, 1, 2
    
    def _merge_wav_chunks(self, wav_data: bytes) -> bytes:
        """合并多个 WAV 块为一个完整的 WAV 文件
        
        Args:
            wav_data: 可能包含多个 WAV 块的字节数据
            
        Returns:
            bytes: 合并后的单个 WAV 文件
        """
        try:
            if len(wav_data) < 44 or not wav_data.startswith(b'RIFF'):
                return wav_data
            
            # 检查是否包含多个 WAV 块（查找多个 RIFF 头）
            riff_positions = []
            pos = 0
            while pos < len(wav_data):
                pos = wav_data.find(b'RIFF', pos)
                if pos == -1:
                    break
                riff_positions.append(pos)
                pos += 4
            
            # 如果只有一个 RIFF 头，直接返回
            if len(riff_positions) <= 1:
                return wav_data
            
            logger.debug(f"📦 检测到 {len(riff_positions)} 个 WAV 块，开始合并")
            
            # 解析第一个 WAV 头，获取参数
            first_wav_io = io.BytesIO(wav_data)
            with wave.open(first_wav_io, 'rb') as first_wav:
                sample_rate = first_wav.getframerate()
                channels = first_wav.getnchannels()
                sample_width = first_wav.getsampwidth()
                n_frames = first_wav.getnframes()
            
            # 收集所有 WAV 块的音频数据
            all_frames = bytearray()
            
            for i, riff_pos in enumerate(riff_positions):
                # 提取每个 WAV 块
                if i < len(riff_positions) - 1:
                    # 不是最后一个，找到下一个 RIFF 的位置
                    next_riff_pos = riff_positions[i + 1]
                    chunk_data = wav_data[riff_pos:next_riff_pos]
                else:
                    # 最后一个，到数据末尾
                    chunk_data = wav_data[riff_pos:]
                
                # 解析这个 WAV 块
                chunk_io = io.BytesIO(chunk_data)
                try:
                    with wave.open(chunk_io, 'rb') as chunk_wav:
                        chunk_frames = chunk_wav.readframes(chunk_wav.getnframes())
                        all_frames.extend(chunk_frames)
                except Exception as e:
                    logger.warning(f"⚠️ 解析 WAV 块 {i+1} 失败: {e}，跳过")
                    continue
            
            # 创建合并后的 WAV 文件
            output = io.BytesIO()
            with wave.open(output, 'wb') as out_wav:
                out_wav.setnchannels(channels)
                out_wav.setsampwidth(sample_width)
                out_wav.setframerate(sample_rate)
                out_wav.writeframes(bytes(all_frames))
            
            merged_data = output.getvalue()
            logger.debug(f"✅ 合并完成: {len(wav_data)}B → {len(merged_data)}B ({len(riff_positions)} 个块)")
            return merged_data
            
        except Exception as e:
            logger.error(f"❌ WAV 合并失败: {e}，使用原始数据")
            return wav_data

    def _generate_sync(self, input_data: bytes, cache: dict, language: str):
        """同步执行模型推理（在线程池中调用，避免阻塞事件循环）
        
        Args:
            input_data: 音频字节数据
            cache: 会话缓存对象
            language: 语言代码
            
        Returns:
            模型推理结果
        """
        return self._model.generate(
            input=input_data,
            cache=cache,
            language=language,
            streaming=True,
            use_itn=True,
            incremental=True
        )

    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """增量转录音频字节（支持流式）

        说明：前端可以发送 WAV 或 PCM 格式的音频数据，此处直接累积并在每次调用时做一次增量解码。
        为避免复杂的端侧终止标记处理，这里每个块都会给出最新累计文本，前端可用作实时显示。
        """
        # 参数解析
        client_id: Optional[str] = kwargs.get("client_id")
        language: str = kwargs.get("language", self.language)
        # is_final 在当前版本不强依赖（Stop 时由上层清理即可）
        is_final: bool = kwargs.get("is_final", False)
        # 音频格式参数
        audio_format: str = kwargs.get("audio_format", "pcm")  # 'wav' 或 'pcm'
        sample_rate: int = kwargs.get("sample_rate", 16000)
        channels: int = kwargs.get("channels", 1)

        # 确保模型已加载（启动时已加载，这里只是检查）
        if self._model is None:
            raise RuntimeError("SenseVoiceSmall 模型未加载")
        
        # 准备会话
        session = self._get_session(client_id)
        session["buffer"].extend(audio_data or b"")

        try:
            loop = asyncio.get_event_loop()
            
            # 准备 ASR 输入数据（使用完整 buffer）
            asr_input_data = bytes(session["buffer"])
            should_do_asr = len(asr_input_data) >= 44  # WAV 文件最小长度为 44 字节
            
            if not should_do_asr:
                logger.debug(f"⏸️ 音频数据不足，等待更多数据")
                result = {
                    "text": session["last_text"],
                    "language": language or "auto",
                    "duration": None,
                    "model": self.model,
                    "provider": "sensevoice",
                    "confidence": 0.9,
                    "is_final": is_final,
                }
                # 如果 is_final=True，即使数据不足也清空 buffer 和 cache
                if is_final:
                    logger.info(f"🧹 is_final=True，清空 buffer 和 cache（数据不足）")
                    session["buffer"].clear()
                    session["cache"].clear()
                return result
            
            # 执行 ASR 推理
            logger.info(f"🎯 开始ASR推理，音频大小: {len(asr_input_data)}B")
            
            # 注意：FunASR 支持直接以字节流作为 input
            res = await loop.run_in_executor(
                None,  # 使用默认线程池
                self._generate_sync,
                asr_input_data,
                session["cache"],
                language or "auto",
            )

            # 结果解析：res 典型为 List[Dict]，取第一项的 "text"
            text = ""
            if isinstance(res, (list, tuple)) and len(res) > 0:
                first = res[0]
                # 有的实现是 res[0]["text"]，也可能嵌套；兼容处理
                if isinstance(first, dict):
                    text = first.get("text", "") or ""
                elif isinstance(first, (list, tuple)) and len(first) > 0 and isinstance(first[0], dict):
                    text = first[0].get("text", "") or ""

            session["last_text"] = text
            logger.info(f"✅ ASR识别完成: {text}")

            # 如果 is_final=True，清空 buffer 和 cache，准备下一段识别
            if is_final:
                logger.info(f"🧹 is_final=True，清空 buffer 和 cache")
                session["buffer"].clear()
                session["cache"].clear()
                logger.debug(f"✅ buffer 和 cache 已清空，准备下一段识别")

            result = {
                "text": text,
                "language": language or "auto",
                "duration": None,
                "model": self.model,
                "provider": "sensevoice",
                "confidence": 0.9,
                "is_final": is_final,
            }
            return result

        except Exception as e:
            logger.error(f"❌ SenseVoiceSmall 识别失败: {e}")
            # 如果 is_final=True，即使识别失败也清空 buffer 和 cache
            if is_final:
                logger.info(f"🧹 is_final=True，清空 buffer 和 cache（识别失败）")
                session = self._get_session(client_id)
                session["buffer"].clear()
                session["cache"].clear()
            raise

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
            "provider": "sensevoice",
            "confidence": 0.9,
            "is_final": True,
        }