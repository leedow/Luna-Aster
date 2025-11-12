"""
Silero VAD 提供商
基于 Silero VAD 模型的语音活动检测
"""

import asyncio
import io
import wave
from typing import Any, Dict, Optional, Tuple
from loguru import logger
from .base import BaseVADProvider
import torch

class SileroVADProvider(BaseVADProvider):
    """Silero VAD 提供商（基于 torch.hub）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # VAD 配置
        self.model = config.get("model", "silero-vad")
        self.device = config.get("device", "cuda")
        self.threshold = config.get("threshold", 0.5)
        self.min_speech_duration_ms = config.get("min_speech_duration_ms", 250)
        self.max_speech_duration_s = config.get("max_speech_duration_s", float('inf'))
        self.min_silence_duration_ms = config.get("min_silence_duration_ms", 100)
        self.sample_rate = config.get("sample_rate", 16000)
        
        # 模型相关
        self._vadModel = None
        self._VADIterator = None
        self._vad_device = "cuda"
        
        # 每个客户端维护一份会话状态
        self._sessions: Dict[str, Dict[str, Any]] = {}
        
        # 启动时立即加载模型
        self._load_model()

    async def is_available(self) -> bool:
        """检查 Silero VAD 是否可用"""
        try:
            import torch  # noqa: F401
            return self._vadModel is not None
        except Exception as e:
            logger.warning(f"SileroVADProvider: torch 未安装或不可用: {e}")
            return False

    def _load_model(self):
        """在启动时加载 Silero VAD 模型"""
        if self._vadModel is not None:
            return
        
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
            (self._get_speech_timestamps, self._save_audio, self._read_audio, 
             self._VADIterator, self._collect_chunks) = utils
            
            # 设置设备
            if torch.cuda.is_available() and self.device != "cpu":
                self._vadModel = self._vadModel.to(self.device)
                self._vad_device = self.device
                logger.info(f"✅ Silero VAD 已加载到 {self.device}")
            else:
                self._vadModel = self._vadModel.to("cpu")
                self._vad_device = "cpu"
                logger.info(f"✅ Silero VAD 已加载到 CPU")
            
            logger.info(f"✅ Silero VAD 模型加载完成")
        except Exception as e:
            logger.error(f"❌ 加载 Silero VAD 失败: {e}")
            raise

    def _get_session(self, client_id: Optional[str]) -> Dict[str, Any]:
        """获取或创建客户端流式会话上下文"""
        key = client_id or "_default"
        if key not in self._sessions:
            vad_iterator = None
            if self._vadModel is not None and self._VADIterator:
                vad_iterator = self._VADIterator(
                    self._vadModel,
                    sampling_rate=self.sample_rate,
                )

            self._sessions[key] = {
                "buffer": bytearray(),  # 累积所有音频字节（用于调试）
                "speech_buffer": bytearray(),  # 仅累积语音片段（从start到end）
                "vad_iterator": vad_iterator,
                "is_speech_active": False,
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

    def _pcm_to_numpy(self, pcm_data: bytes, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> Tuple[Any, int]:  # type: ignore
        """将 PCM 字节数据直接转换为 numpy 数组"""
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
        """将 WAV 字节数据转换为 numpy 数组"""
        try:
            import numpy as np
            
            # 读取 WAV 文件
            wav_io = io.BytesIO(wav_data)
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
                ratio = sample_rate / actual_sample_rate
                new_length = int(len(audio_array) * ratio)
                indices = np.linspace(0, len(audio_array) - 1, new_length)
                audio_array = np.interp(indices, np.arange(len(audio_array)), audio_array)
                actual_sample_rate = sample_rate
            
            return audio_array, actual_sample_rate
        except Exception as e:
            logger.error(f"❌ WAV 转 numpy 失败: {e}")
            raise

    async def detect_speech(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """
        检测音频中的语音活动（流式）
        
        Args:
            audio_data: 音频字节数据
            **kwargs:
                - client_id: 客户端ID
                - audio_format: 音频格式 ('pcm' 或 'wav')
                - sample_rate: 采样率
                - channels: 声道数
        
        Returns:
            Dict包含检测结果
        """
        if self._vadModel is None:
            raise RuntimeError("Silero VAD 模型未加载")
        
        # 参数解析
        client_id: Optional[str] = kwargs.get("client_id")
        audio_format: str = kwargs.get("audio_format", "pcm")
        sample_rate: int = kwargs.get("sample_rate", self.sample_rate)
        channels: int = kwargs.get("channels", 1)
        
        # 准备会话
        session = self._get_session(client_id)
        session["buffer"].extend(audio_data or b"")

        try:
            loop = asyncio.get_event_loop()
            
            # 将新增的音频数据转换为 numpy 数组
            if audio_format == "pcm":
                new_audio_array, actual_sample_rate = await loop.run_in_executor(
                    None,
                    self._pcm_to_numpy,
                    audio_data,
                    sample_rate,
                    channels,
                    2  # 16-bit PCM
                )
            else:
                new_audio_array, actual_sample_rate = await loop.run_in_executor(
                    None,
                    self._wav_to_numpy,
                    audio_data,
                    self.sample_rate
                )
            
            new_samples = len(new_audio_array)
            logger.debug(f"📊 新增音频: {new_samples} 采样点, {actual_sample_rate}Hz")
            
            # 使用 Silero VAD 流式检测
            vad_iterator = session.get("vad_iterator")
            if vad_iterator is None:
                raise RuntimeError("Silero VAD 未初始化")
            
            if new_audio_array.size == 0:
                logger.debug("🎤 收到空音频块，跳过 Silero VAD 检测")
                return {
                    "vad_detected": False,
                    "speech_active": session["is_speech_active"],
                    "speech_segment": None,
                    "vad_metadata": {},
                }
            
            
            chunk_tensor = torch.from_numpy(new_audio_array).to(self._vad_device)
            
            # 使用 VADIterator 进行流式检测
            speech_event = vad_iterator(chunk_tensor, return_seconds=False)
            
            # 记录当前状态
            logger.debug(f"🎤 Silero VAD 事件: {speech_event}, 当前状态: is_speech_active={session['is_speech_active']}, speech_buffer_len={len(session['speech_buffer'])}B")
            
            # 检查事件类型
            has_start = speech_event and speech_event.get("start") is not None
            has_end = speech_event and speech_event.get("end") is not None
            
            # 处理语音开始事件：清空speech_buffer，开始累积
            if has_start:
                if session["is_speech_active"]:
                    logger.warning(f"⚠️ 检测到语音开始事件，但 is_speech_active 已经是 True，清空并重新开始")
                
                session["is_speech_active"] = True
                session["speech_buffer"].clear()  # 清空之前的累积
                session["speech_buffer"].extend(audio_data)  # 开始累积当前chunk
                logger.info(f"🟢 检测到语音开始，开始累积语音片段 (当前chunk: {len(audio_data)}B)")
                
                # 如果同时有 end 事件（极短语音片段），继续处理让 end 事件处理
                if not has_end:
                    return {
                        "vad_detected": True,
                        "speech_active": True,
                        "speech_segment": None,
                        "vad_metadata": {
                            "event": "speech_start",
                            "vad_event": speech_event,
                        }
                    }
                else:
                    logger.warning(f"⚠️ 同时检测到语音开始和结束，可能是极短的语音片段，继续处理end事件")
            
            # 如果语音正在进行中（且没有start事件），累积当前chunk到speech_buffer
            elif session["is_speech_active"]:
                session["speech_buffer"].extend(audio_data)
                logger.debug(f"📝 累积chunk到speech_buffer: {len(audio_data)}B (总长度: {len(session['speech_buffer'])}B)")
            
            # 处理语音结束事件：返回累积的speech_buffer并清空
            if has_end:
                if not session["is_speech_active"]:
                    logger.warning(f"⚠️ 检测到语音结束，但 is_speech_active=False，可能之前没有检测到语音开始")
                    # 即使没有检测到start，也返回当前累积的数据（如果有）
                
                session["is_speech_active"] = False
                
                # 提取累积的语音片段
                speech_segment = bytes(session["speech_buffer"])
                segment_length = len(speech_segment)
                
                logger.info(f"🔴 检测到语音结束 - 返回语音片段: {segment_length}B, 事件: {speech_event}")
                
                # 清空speech_buffer和buffer，准备下一个片段
                session["speech_buffer"].clear()
                session["buffer"].clear()
                vad_iterator.reset_states()
                
                if segment_length >= 2:  # 至少1个16-bit样本（PCM）或44字节（WAV）
                    return {
                        "vad_detected": True,
                        "speech_active": False,
                        "speech_segment": speech_segment,
                        "is_final": True,
                        "vad_metadata": {
                            "event": "speech_end",
                            "segment_length": segment_length,
                            "audio_format": audio_format,
                            "vad_event": speech_event,
                        }
                    }
                else:
                    logger.warning(f"⚠️ 语音片段太短: {segment_length}B，跳过")
                    return {
                        "vad_detected": False,
                        "speech_active": False,
                        "speech_segment": None,
                        "vad_metadata": {},
                    }
            
            # 如果语音仍在进行中（但没有检测到新的 start/end 事件）
            if session["is_speech_active"]:
                logger.debug(f"🔄 语音进行中，累积中... (当前speech_buffer长度: {len(session['speech_buffer'])}B)")
                return {
                    "vad_detected": True,
                    "speech_active": True,
                    "speech_segment": None,
                    "vad_metadata": {
                        "event": "speech_ongoing",
                        "buffer_length": len(session["speech_buffer"]),
                    }
                }
            
            # 没有检测到语音
            logger.debug(f"🔇 无语音活动")
            return {
                "vad_detected": False,
                "speech_active": False,
                "speech_segment": None,
                "vad_metadata": {},
            }
            
        except Exception as e:
            logger.error(f"❌ Silero VAD 检测失败: {e}")
            raise


