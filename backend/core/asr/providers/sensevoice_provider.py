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
from typing import Any, Dict, Optional
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
        # VAD 配置（提升长音频与流式场景稳定性）
        self.vad_model = config.get("vad_model", "fsmn-vad")
        self.vad_kwargs = config.get("vad_kwargs", {"max_single_segment_time": 30000})

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
            # 附加 VAD
            if self.vad_model:
                kwargs["vad_model"] = self.vad_model
            if self.vad_kwargs:
                kwargs["vad_kwargs"] = self.vad_kwargs

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
                "buffer": bytearray(),  # 累积 WAV 字节
                "cache": {},            # 传递给 AutoModel.generate 的缓存对象
                "last_text": "",
            }
        return self._sessions[key]

    def _clear_session(self, client_id: Optional[str]):
        """清理会话缓存与缓冲区"""
        key = client_id or "_default"
        if key in self._sessions:
            del self._sessions[key]

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

        说明：前端以 WAV（含头）分块推送，此处直接累积并在每次调用时做一次增量解码。
        为避免复杂的端侧终止标记处理，这里每个块都会给出最新累计文本，前端可用作实时显示。
        """
        # 参数解析
        client_id: Optional[str] = kwargs.get("client_id")
        language: str = kwargs.get("language", self.language)
        # is_final 在当前版本不强依赖（Stop 时由上层清理即可）
        is_final: bool = kwargs.get("is_final", False)

        # 确保模型已加载（启动时已加载，这里只是检查）
        if self._model is None:
            raise RuntimeError("SenseVoiceSmall 模型未加载")
        
        # 准备会话
        session = self._get_session(client_id)
        session["buffer"].extend(audio_data or b"")

        # 调用 AutoModel.generate - 在线程池中执行，避免阻塞事件循环
        try:
            # 注意：FunASR 支持直接以字节流作为 input
            # 传入会话级 cache，可让模型做增量复用（如果模型支持）
            # 使用线程池执行同步推理，避免阻塞 WebSocket 消息处理
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(
                None,  # 使用默认线程池
                self._generate_sync,
                bytes(session["buffer"]),
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