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
        self.device = config.get("device", "cpu")  # 默认为 CPU，确保在 Windows 上可运行
        self.hub = config.get("hub", "ms")  # 模型来源：ModelScope(ms) 或 HuggingFace(hf)
        self.trust_remote_code = config.get("trust_remote_code", True)
        self.remote_code = config.get("remote_code")  # 可选，通常无需设置
        # VAD 配置（使用 Silero VAD）
        self.vad_model = config.get("vad_model", "silero-vad")
        self.vad_threshold = config.get("vad_threshold", 0.5)  # Silero VAD 阈值
        self.vad_min_speech_duration_ms = config.get("vad_min_speech_duration_ms", 250)  # 最小语音时长
        self.vad_max_speech_duration_s = config.get("vad_max_speech_duration_s", float('inf'))  # 最大语音时长
        self.vad_min_silence_duration_ms = config.get("vad_min_silence_duration_ms", 100)  # 最小静音时长

        # 启动时立即加载 AutoModel
        self._model = None
        self._vadModel = None
        self._vad_utils = None
        self._vad_device = "cpu"
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
        """在启动时加载 AutoModel 和 Silero VAD"""
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
            
            # 加载 Silero VAD
            try:
                import torch
                logger.info(f"📦 加载 Silero VAD 模型...")
                
                # 从 torch.hub 加载 Silero VAD
                self._vadModel, utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False,
                    source='local'
                )
                # 获取工具函数
                (self._get_speech_timestamps, self._save_audio, self._read_audio, self._VADIterator, self._collect_chunks) = utils
                # 设置设备
                if torch.cuda.is_available() and self.device != "cpu":
                    self._vadModel = self._vadModel.to(self.device)
                    self._vad_device = self.device
                    logger.info(f"✅ Silero VAD 已加载到 {self.device}")
                else:
                    self._vadModel = self._vadModel.to("cpu")
                    self._vad_device = "cpu"
                    logger.info(f"✅ Silero VAD 已加载到 CPU")
                
                self._vad_utils = utils

                logger.info(f"✅ Silero VAD 模型加载完成")
            except Exception as e:
                logger.warning(f"⚠️ 加载 Silero VAD 失败: {e}，将不使用 VAD")
                self._vadModel = None
                self._vad_utils = None
                
        except Exception as e:
            logger.error(f"❌ 加载 SenseVoiceSmall 失败: {e}")
            raise

    def _get_session(self, client_id: Optional[str]) -> Dict[str, Any]:
        """获取或创建客户端流式会话上下文"""
        key = client_id or "_default"
        if key not in self._sessions:
            vad_iterator = None
            if self._vadModel is not None and getattr(self, "_VADIterator", None):
                vad_iterator = self._VADIterator(
                    self._vadModel,
                    sampling_rate=16000,
                    # threshold=self.vad_threshold,
                    # min_speech_duration_ms=self.vad_min_speech_duration_ms,
                    # max_speech_duration_s=self.vad_max_speech_duration_s,
                    # min_silence_duration_ms=self.vad_min_silence_duration_ms,
                    # speech_pad_ms=30,
                )

            self._sessions[key] = {
                "buffer": bytearray(),  # 累积 WAV 字节
                "cache": {},            # 传递给 AutoModel.generate 的缓存对象
                "last_text": "",
                # Silero VAD 流式状态
                "vad_iterator": vad_iterator,
                "is_speech_active": False,
                "speech_start_pos": 0,
            }
        return self._sessions[key]

    def _clear_session(self, client_id: Optional[str]):
        """清理会话缓存与缓冲区"""
        key = client_id or "_default"
        if key in self._sessions:
            sess = self._sessions[key]
            vad_iterator = sess.get("vad_iterator")
            if vad_iterator:
                vad_iterator.reset_states()
            del self._sessions[key]
    
    def _is_segment_duplicate(self, current_segment: Tuple[int, int], last_segment: Optional[Tuple[int, int]], threshold_ms: int = 50) -> bool:
        """判断当前时间范围是否与上次重复
        
        Args:
            current_segment: 当前时间范围 (beg_ms, end_ms)
            last_segment: 上次时间范围 (beg_ms, end_ms) 或 None
            threshold_ms: 重复判断阈值（毫秒），默认50ms，如果时间范围差异小于此值则认为重复
            
        Returns:
            bool: 是否重复
        """
        if last_segment is None:
            return False
        
        if not isinstance(current_segment, (list, tuple)) or len(current_segment) < 2:
            return False
        if not isinstance(last_segment, (list, tuple)) or len(last_segment) < 2:
            return False
        
        current_beg, current_end = int(current_segment[0]), int(current_segment[1])
        last_beg, last_end = int(last_segment[0]), int(last_segment[1])
        
        # 判断是否相同（允许小误差）
        beg_diff = abs(current_beg - last_beg)
        end_diff = abs(current_end - last_end)
        
        # 如果起始和结束时间差异都在阈值内，认为重复
        is_duplicate = beg_diff <= threshold_ms and end_diff <= threshold_ms
        
        if is_duplicate:
            logger.debug(f"🔄 检测到重复时间范围: [{current_beg}ms, {current_end}ms] vs [{last_beg}ms, {last_end}ms] (差异: {beg_diff}ms, {end_diff}ms)")
        
        return is_duplicate
    
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
    
    def _extract_audio_segment(self, wav_data: bytes, beg_ms: int, end_ms: int) -> bytes:
        """根据时间范围裁剪 WAV 音频数据
        
        Args:
            wav_data: 完整的 WAV 字节数据（可能包含多个 WAV 块）
            beg_ms: 起始时间（毫秒）
            end_ms: 结束时间（毫秒）
            
        Returns:
            bytes: 裁剪后的 WAV 数据，如果失败或数据太短则返回原始数据
        """
        try:
            if len(wav_data) < 44 or not wav_data.startswith(b'RIFF'):
                logger.warning("⚠️ 非WAV格式，无法裁剪，使用原始数据")
                return wav_data
            
            # 先合并多个 WAV 块（如果有）
            merged_wav_data = self._merge_wav_chunks(wav_data)
            
            # 解析 WAV 头
            sample_rate, channels, sample_width = self._parse_wav_header(merged_wav_data)
            
            # 读取合并后的 WAV 数据
            wav_io = io.BytesIO(merged_wav_data)
            with wave.open(wav_io, 'rb') as wav_file:
                n_frames = wav_file.getnframes()
                
                # 验证帧数
                if n_frames == 0:
                    logger.warning(f"⚠️ WAV文件帧数为0，使用原始数据")
                    return wav_data
                
                # 计算音频总时长（毫秒）
                total_duration_ms = (n_frames / sample_rate) * 1000
                
                logger.info(f"📊 音频信息: {n_frames}帧, {sample_rate}Hz, 总时长: {total_duration_ms:.2f}ms")
                logger.info(f"📊 VAD时间范围: [{beg_ms}ms, {end_ms}ms]")
                
                # 验证时间范围
                original_beg_ms = beg_ms
                original_end_ms = end_ms
                
                if beg_ms < 0:
                    beg_ms = 0
                    logger.debug(f"📊 调整起始时间: {original_beg_ms}ms → {beg_ms}ms")
                
                if end_ms > total_duration_ms:
                    logger.warning(f"⚠️ 结束时间超出音频长度: {end_ms}ms > {total_duration_ms:.2f}ms")
                    logger.warning(f"⚠️ 原始buffer大小: {len(wav_data)}B, 合并后大小: {len(merged_wav_data)}B")
                    logger.warning(f"⚠️ 可能原因: buffer包含多个WAV块，但合并后总时长仍不足")
                    # 如果时间范围超出，使用原始数据而不是截断
                    logger.warning(f"⚠️ 使用原始buffer进行ASR推理")
                    return wav_data
                
                if beg_ms >= end_ms:
                    logger.warning(f"⚠️ 无效时间范围: [{beg_ms}ms, {end_ms}ms]")
                    logger.warning(f"⚠️ 原始时间范围: [{original_beg_ms}ms, {original_end_ms}ms]")
                    logger.warning(f"⚠️ 音频总时长: {total_duration_ms:.2f}ms")
                    logger.warning(f"⚠️ 原始buffer大小: {len(wav_data)}B, 合并后大小: {len(merged_wav_data)}B")
                    logger.warning(f"⚠️ 使用原始数据")
                    return wav_data
                
                # 计算帧位置（按帧对齐，而不是按字节）
                frames_per_ms = sample_rate / 1000.0
                beg_frame = int(beg_ms * frames_per_ms)
                end_frame = int(end_ms * frames_per_ms)
                
                # 确保不超出范围
                beg_frame = max(0, min(beg_frame, n_frames))
                end_frame = max(beg_frame, min(end_frame, n_frames))
                
                # 验证最小长度（至少需要 0.1 秒的音频）
                min_duration_ms = 100  # 最小 100ms
                min_frames = int(min_duration_ms * frames_per_ms)
                segment_frames_count = end_frame - beg_frame
                
                if segment_frames_count < min_frames:
                    logger.warning(f"⚠️ 裁剪后的音频太短: {segment_frames_count}帧 < {min_frames}帧 ({min_duration_ms}ms)，使用原始数据")
                    return wav_data
                
                # 读取指定范围的帧
                # 方法：先读取所有帧，然后裁剪
                all_frames = wav_file.readframes(n_frames)
                
                # 计算字节位置（按帧对齐）
                bytes_per_frame = channels * sample_width
                beg_bytes = beg_frame * bytes_per_frame
                end_bytes = end_frame * bytes_per_frame
                
                # 确保不超出范围
                beg_bytes = max(0, min(beg_bytes, len(all_frames)))
                end_bytes = max(beg_bytes, min(end_bytes, len(all_frames)))
                
                # 裁剪音频数据（按帧对齐）
                segment_frames = all_frames[beg_bytes:end_bytes]
                
                # 确保帧数对齐（必须是 bytes_per_frame 的倍数）
                remainder = len(segment_frames) % bytes_per_frame
                if remainder != 0:
                    # 截断到帧边界
                    segment_frames = segment_frames[:-remainder]
                
                # 重新验证长度
                if len(segment_frames) < min_frames * bytes_per_frame:
                    logger.warning(f"⚠️ 裁剪后的音频太短: {len(segment_frames)}B < {min_frames * bytes_per_frame}B，使用原始数据")
                    return wav_data
                
                # 验证读取的数据
                if not segment_frames or len(segment_frames) == 0:
                    logger.warning(f"⚠️ 裁剪后的音频数据为空，使用原始数据")
                    return wav_data
                
                # 创建新的 WAV 文件
                output = io.BytesIO()
                with wave.open(output, 'wb') as out_wav:
                    out_wav.setnchannels(channels)
                    out_wav.setsampwidth(sample_width)
                    out_wav.setframerate(sample_rate)
                    out_wav.writeframes(segment_frames)
                
                result = output.getvalue()
                
                # 最终验证：确保结果不为空且格式正确
                if len(result) < 44 or not result.startswith(b'RIFF'):
                    logger.warning(f"⚠️ 裁剪后的WAV格式异常，使用原始数据")
                    return wav_data
                
                logger.debug(f"✅ 音频裁剪成功: {len(wav_data)}B → {len(result)}B ({segment_frames_count}帧, {beg_ms}ms-{end_ms}ms)")
                return result
                
        except Exception as e:
            logger.error(f"❌ 音频裁剪失败: {e}，使用原始数据")
            return wav_data  # 失败时返回原始数据

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
            
            # 步骤1: Silero VAD 流式检测（如果启用）
            asr_input_data = None  # 待 ASR 推理的音频数据
            should_do_asr = False  # 是否执行 ASR 推理
            
            if self._vadModel is not None and len(audio_data) > 0:
                try:
                    import torch
                    import numpy as np
                    
                    vad_iterator = session.get("vad_iterator")
                    if vad_iterator is None and self._vadModel is not None and getattr(self, "_VADIterator", None):
                        vad_iterator = self._VADIterator(
                            self._vadModel,
                            sampling_rate=16000,
                            # threshold=self.vad_threshold,
                            # min_speech_duration_ms=self.vad_min_speech_duration_ms,
                            # max_speech_duration_s=self.vad_max_speech_duration_s,
                            # min_silence_duration_ms=self.vad_min_silence_duration_ms,
                            # speech_pad_ms=30,
                        )
                        session["vad_iterator"] = vad_iterator
                    
                    if vad_iterator is None:
                        raise RuntimeError("Silero VAD 未初始化")
                    
                    print(audio_format)
                    print(11111111111111111111111111111111)
                    # 1. 将新增的音频数据转换为 numpy 数组
                    if audio_format == "pcm":
                        # 使用 PCM 直接转换（无需解析 WAV 头）
                        new_audio_array, actual_sample_rate = await loop.run_in_executor(
                            None,
                            self._pcm_to_numpy,
                            audio_data,
                            sample_rate,  # 使用传入的采样率
                            channels,
                            2  # 16-bit PCM
                        )
                    else:
                        # 使用 WAV 转换（需要解析 WAV 头）
                        new_audio_array, actual_sample_rate = await loop.run_in_executor(
                            None,
                            self._wav_to_numpy,
                            audio_data,
                            16000  # Silero VAD 需要 16kHz
                        )
                    
                    new_samples = len(new_audio_array)
                    logger.debug(f"📊 新增音频: {new_samples} 采样点, {actual_sample_rate}Hz, 时长: {new_samples/actual_sample_rate*1000:.0f}ms")
                    
                    # 2. 使用 Silero VAD 流式检测
                    if new_audio_array.size == 0:
                        logger.debug("🎤 收到空音频块，跳过 Silero VAD 检测")
                        chunk_tensor = None
                    else:
                        chunk_tensor = torch.from_numpy(new_audio_array).to(self._vad_device)
                    
                    if chunk_tensor is None:
                        speech_event = None
                    else:
                        speech_event = vad_iterator(chunk_tensor, return_seconds=False)
                    
                    logger.debug(f"🎤 Silero VAD 事件: {speech_event}")
                    
                    current_has_speech = bool(speech_event and speech_event.get("start") is not None)
                    
                    if current_has_speech and not session["is_speech_active"]:
                        # 语音开始：记录当前 buffer 位置
                        session["is_speech_active"] = True
                        session["speech_start_pos"] = len(session["buffer"]) - len(audio_data)
                        logger.info(f"🟢 检测到语音开始 - 位置: {session['speech_start_pos']}B")
                    
                    elif speech_event and speech_event.get("end") is not None and session["is_speech_active"]:
                        # 语音结束：提取 buffer 片段并准备 ASR 推理
                        session["is_speech_active"] = False
                        speech_end_pos = len(session["buffer"])
                        
                        logger.info(f"🔴 检测到语音结束 - 位置: {speech_end_pos}B")
                        logger.info(f"📊 语音片段字节范围: [{session['speech_start_pos']} - {speech_end_pos}]，长度: {speech_end_pos - session['speech_start_pos']}B")
                        
                        # 提取语音片段
                        try:
                            # 从 buffer 中提取语音片段（字节范围）
                            speech_bytes = bytes(session["buffer"][session["speech_start_pos"]:speech_end_pos])
                            
                            # 合并可能的多个 WAV 块
                            merged_speech = await loop.run_in_executor(
                                None,
                                self._merge_wav_chunks,
                                speech_bytes
                            )
                            
                            # 验证提取的数据
                            if len(merged_speech) >= 44 and merged_speech.startswith(b'RIFF'):
                                asr_input_data = merged_speech
                                should_do_asr = True
                                logger.info(f"✅ 语音片段提取成功: {len(speech_bytes)}B → {len(merged_speech)}B")
                            else:
                                logger.warning(f"⚠️ 提取的语音片段格式异常，跳过ASR推理")
                                
                        except Exception as e:
                            logger.error(f"❌ 语音片段提取失败: {e}")
                    
                    # 如果语音仍在进行中，跳过 ASR 推理（等待语音结束）
                    if session["is_speech_active"]:
                        logger.debug(f"🔄 语音进行中，等待结束...")
                        return {
                            "text": session["last_text"],
                            "language": language or "auto",
                            "duration": None,
                            "model": self.model,
                            "provider": "sensevoice",
                            "confidence": 0.9,
                            "is_final": is_final,
                            "vad_detected": True,
                            "speech_active": True,
                        }
                    
                except Exception as e:
                    logger.error(f"❌ Silero VAD 检测失败: {e}")
                    # 回退到非 VAD 模式
                    asr_input_data = bytes(session["buffer"])
                    should_do_asr = len(asr_input_data) >= 44
            else:
                # 未启用 VAD，使用完整 buffer
                asr_input_data = bytes(session["buffer"])
                should_do_asr = len(asr_input_data) >= 44
            
            # 步骤2: ASR 推理（当检测到语音结束时）
            if not should_do_asr or not asr_input_data or len(asr_input_data) < 44:
                # 不需要 ASR 推理，返回上次结果
                if not should_do_asr:
                    logger.debug(f"⏸️ 等待语音片段完成")
                else:
                    logger.warning(f"⚠️ ASR输入数据无效: {len(asr_input_data) if asr_input_data else 0}B")
                
                return {
                    "text": session["last_text"],
                    "language": language or "auto",
                    "duration": None,
                    "model": self.model,
                    "provider": "sensevoice",
                    "confidence": 0.9,
                    "is_final": is_final,
                    "vad_detected": self._vadModel is not None,
                }
            
            # 执行 ASR 推理
            logger.info(f"🎯 开始ASR推理，音频大小: {len(asr_input_data)}B")
            
            # 注意：FunASR 支持直接以字节流作为 input
            # 流式 VAD 模式下，每个语音片段使用新的 cache（独立识别）
            asr_cache = {} if self._vadModel is not None else session["cache"]
            
            res = await loop.run_in_executor(
                None,  # 使用默认线程池
                self._generate_sync,
                asr_input_data,
                asr_cache,
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
            
            # 步骤3: 清除已处理的 buffer（流式 VAD 模式）
            if self._vadModel is not None and should_do_asr:
                # 清除整个 buffer（语音片段已处理完成）
                session["buffer"].clear()
                session["speech_start_pos"] = 0
                vad_iterator = session.get("vad_iterator")
                if vad_iterator:
                    vad_iterator.reset_states()
                session["cache"].clear()
                logger.info(f"🧹 Buffer已清除，准备接收下一个语音片段")

            result = {
                "text": text,
                "language": language or "auto",
                "duration": None,
                "model": self.model,
                "provider": "sensevoice",
                "confidence": 0.9,
                "is_final": is_final,
                "vad_detected": self._vadModel is not None,
                "buffer_cleared": self._vadModel is not None and should_do_asr,
            }
            return result

        except Exception as e:
            logger.error(f"❌ SenseVoiceSmall 识别失败: {e}")
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