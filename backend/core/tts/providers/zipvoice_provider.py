"""
ZipVoice 提供商实现
通过调用第三方 HTTP API 进行语音合成

默认调用示例（供参考）：
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{
        "prompt_text":"你好啊。",
        "prompt_wav_path":"./prompt.wav",
        "text":"你说对不对啊。哈哈哈哈哈哈",
        "return_metrics":true,
        "raw_evaluation":false
      }'
"""

from typing import Dict, Any, Optional
from loguru import logger
import base64
import os

from .base import BaseTTSProvider


class ZipVoiceProvider(BaseTTSProvider):
    """ZipVoice TTS提供商（HTTP API）"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 端点与调用参数
        self.endpoint: str = config.get("endpoint", "http://localhost:8005/tts")
        self.prompt_text: Optional[str] = config.get("prompt_text")
        self.prompt_wav_path: Optional[str] = config.get("prompt_wav_path")
        self.return_metrics: bool = False #bool(config.get("return_metrics", False))
        self.raw_evaluation: bool = False #bool(config.get("raw_evaluation", False))

        try:
            import httpx  # noqa: F401
            self._httpx_available = True
            logger.info("✅ ZipVoiceProvider 初始化成功")
        except Exception:
            self._httpx_available = False
            logger.error("❌ httpx 未安装，无法调用 ZipVoice API。请安装 httpx")

    async def synthesize_speech(self, text: str, **kwargs) -> Dict[str, Any]:
        """调用 ZipVoice HTTP API 合成语音"""
        if not self._httpx_available:
            raise Exception("ZipVoiceProvider 未初始化（httpx 不可用）")

        if not self.validate_text(text):
            raise Exception("无效的文本内容")

        # 读取可能的覆盖参数
        endpoint = kwargs.get("endpoint", self.endpoint)
        prompt_text = kwargs.get("prompt_text", self.prompt_text)
        prompt_wav_path = kwargs.get("prompt_wav_path", self.prompt_wav_path)
        return_metrics = kwargs.get("return_metrics", self.return_metrics)
        raw_evaluation = kwargs.get("raw_evaluation", self.raw_evaluation)

        payload: Dict[str, Any] = {"text": text}
        #if prompt_text:
        payload["prompt_text"] = "当然可以啦，你知道吗，我真的很喜欢你的声音。"
        # 根据接口示例，prompt_wav_path 为字符串路径参数，不强制本地存在
        #if prompt_wav_path:
        payload["prompt_wav_path"] = "prompt5.wav"
        # 保持与示例一致的布尔字段
        payload["return_metrics"] = bool(return_metrics)
        payload["raw_evaluation"] = True #bool(raw_evaluation)

        try:
            import httpx
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                resp = await client.post(endpoint, json=payload)
                resp.raise_for_status()

                content_type = resp.headers.get("content-type", "")

                # 1) 如果直接返回二进制音频
                if content_type.startswith("audio/") or "octet-stream" in content_type:
                    audio_bytes = resp.content
                    audio_format = "wav" if "wav" in content_type else (
                        "mp3" if "mpeg" in content_type or "mp3" in content_type else "wav"
                    )
                else:
                    # 2) 如果返回 JSON，尝试解析 base64 字段
                    data = resp.json()
                    audio_bytes, audio_format = self._extract_audio_from_json(data)

                if not audio_bytes:
                    raise Exception("ZipVoice API 返回为空音频")

                result = {
                    "audio_data": audio_bytes,
                    "format": audio_format,
                    "sample_rate": 24000,  # 默认值，具体依赖服务端
                    "channels": 1,
                    "duration": None,  # 无法准确获知时长
                    "text": text,
                    "voice": self.voice,
                    "language": self.language,
                    "provider": "zipvoice",
                    "model": "zipvoice-api",
                }

                logger.info(f"🔊 ZipVoice 合成成功: {text[:50]}...")
                return result

        except Exception as e:
            logger.error(f"❌ ZipVoice 合成失败: {str(e)}")
            raise Exception(f"ZipVoice 合成失败: {str(e)}")

    async def is_available(self) -> bool:
        """检查 ZipVoice API 是否可用"""
        return True

    def _extract_audio_from_json(self, data: Dict[str, Any]) -> (bytes, str):
        """从 JSON 响应中提取音频（支持多字段兜底）"""
        possible_keys = [
            "audio_data",
            "audio",
            "audio_base64",
            "wav_base64",
            "mp3_base64",
            "wav",
            "mp3",
        ]

        fmt = "wav"
        for key in possible_keys:
            if key in data and isinstance(data[key], str):
                try:
                    audio_bytes = base64.b64decode(data[key])
                    # 根据 key 猜测格式
                    if "mp3" in key:
                        fmt = "mp3"
                    elif "wav" in key:
                        fmt = "wav"
                    return audio_bytes, fmt
                except Exception:
                    continue

        # 也可能嵌套在 data 字段
        if "data" in data and isinstance(data["data"], dict):
            return self._extract_audio_from_json(data["data"])  # 递归检查

        return b"", fmt