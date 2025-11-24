"""
Qwen3 LLM 提供商（基于 vLLM 异步引擎）
启用前缀缓存（KV Cache）以复用会话上下文。
"""

from typing import Dict, Any, Optional, List, AsyncIterator
from loguru import logger
import asyncio
from uuid import uuid4

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.sampling_params import SamplingParams, RequestOutputKind

from .base import BaseLLMProvider


class Qwen3Provider(BaseLLMProvider):
    """Qwen3 LLM提供商（vLLM）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "Qwen/Qwen3-VL-4B-Instruct")
        self.max_new_tokens = config.get("max_new_tokens", 512)
        self.gpu_memory_utilization = float(config.get("gpu_memory_utilization", 0.75))
        self.max_model_len = int(config.get("max_model_len", 8192))

        # vLLM 异步引擎
        self._engine: Optional[AsyncLLMEngine] = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """初始化 vLLM 异步引擎并启用前缀缓存"""
        if self._engine is not None:
            return

        try:
            logger.info(f"📦 使用 vLLM 加载模型: {self.model_name}")

            engine_args = AsyncEngineArgs(
                model=self.model_name,
                enable_prefix_caching=True,
                gpu_memory_utilization=self.gpu_memory_utilization,
                max_model_len=self.max_model_len,
            )

            self._engine = AsyncLLMEngine.from_engine_args(engine_args)
            logger.info("✅ vLLM 异步引擎初始化完成，并启用前缀缓存")

        except Exception as e:
            logger.error(f"❌ vLLM 引擎初始化失败: {e}")
            raise
    
    async def is_available(self) -> bool:
        """检查 vLLM 引擎是否健康"""
        if not self._engine:
            return False
        try:
            await self._engine.check_health()
            return True
        except Exception as e:
            logger.warning(f"Qwen3Provider(vLLM): 引擎不可用: {e}")
            return False
    
    def _build_full_prompt(self, prompt: str, **kwargs) -> str:
        """使用 ChatML 格式构造提示，限制只生成 assistant 回复。"""
        system_prompt = kwargs.get(
            "system_prompt",
            "你是Luna，一个友善、聪明、有趣的虚拟助手。请用自然、亲切的语调回复用户。请用简短的话语回复每次对话，不要超过3句话，并在合适的情况下提问，避免把天聊死",
        )
        history: List[Dict[str, Any]] = kwargs.get("history", []) or []

        segments: List[str] = []
        # system 段
        segments.append(f"<|im_start|>system\n{system_prompt}<|im_end|>\n")
        # history 段
        for msg in history:
            role = msg.get("role")
            if role not in ("user", "assistant"):
                continue
            content = str(msg.get("content", ""))
            if not content:
                continue
            segments.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")

        # 当前用户输入与打开助手段
        segments.append(f"<|im_start|>user\n{prompt}<|im_end|>\n")
        segments.append("<|im_start|>assistant\n")

        return "".join(segments)

    def _estimate_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)

    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回复（非流式），复用会话前缀缓存"""
        if not self._engine:
            raise Exception("vLLM 引擎未初始化")

        try:
            # 构建完整提示，包含会话历史
            full_prompt = self._build_full_prompt(prompt, **kwargs)
            max_new_tokens = kwargs.get("max_new_tokens", self.max_new_tokens)

            sampling_params = SamplingParams(
                max_tokens=max_new_tokens,
                temperature=self.temperature,
                stop=["<|im_end|>", "</s>", "<|endoftext|>"]
            )

            request_id = str(uuid4())
            content_parts: List[str] = []

            async for output in self._engine.generate(
                prompt=full_prompt,
                sampling_params=sampling_params,
                request_id=request_id,
            ):
                # 默认 FULL 模式，最后一次包含完整文本
                # 这里累积文本，确保兼容不同输出模式
                for comp in output.outputs:
                    if comp.text:
                        content_parts.append(comp.text)
                if getattr(output, "finished", False):
                    break

            content = "".join(content_parts).strip()
            tokens_used = self._estimate_tokens(content)

            return {
                "content": content,
                "model": self.model_name,
                "tokens_used": int(tokens_used),
                "provider": "qwen3",
            }

        except Exception as e:
            logger.error(f"❌ Qwen3(vLLM) 生成回复失败: {str(e)}")
            raise Exception(f"Qwen3(vLLM) 生成回复失败: {str(e)}")
    
    async def stream_response(self, prompt: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """流式生成回复（增量token），复用会话前缀缓存"""
        if not self._engine:
            raise Exception("vLLM 引擎未初始化")

        # 构建完整提示
        full_prompt = self._build_full_prompt(prompt, **kwargs)
        max_new_tokens = kwargs.get("max_new_tokens", self.max_new_tokens)

        sampling_params = SamplingParams(
            max_tokens=max_new_tokens,
            temperature=self.temperature,
            output_kind=RequestOutputKind.DELTA,
            stop=["<|im_end|>", "</s>", "<|endoftext|>"]
        )

        request_id = str(uuid4())
        collected_chunks: List[str] = []

        async for output in self._engine.generate(
            prompt=full_prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        ):
            # 逐步输出新增文本
            for comp in output.outputs:
                chunk = comp.text or ""
                if not chunk:
                    continue
                collected_chunks.append(chunk)
                yield {
                    "content": chunk,
                    "is_final": False,
                    "metadata": {
                        "model": self.model_name,
                        "provider": "qwen3",
                    },
                }

            if getattr(output, "finished", False):
                break

        full_text = "".join(collected_chunks).strip()
        tokens_used = self._estimate_tokens(full_text)
        metadata = {
            "content": full_text,
            "model": self.model_name,
            "tokens_used": int(tokens_used),
            "provider": "qwen3",
        }

        yield {
            "content": None,
            "is_final": True,
            "metadata": metadata,
        }

