"""
Qwen3 LLM 提供商
支持 Qwen3-VL 系列模型（基于 ModelScope）
"""

from typing import Dict, Any, Optional, List, AsyncIterator
from loguru import logger
import asyncio
import torch
from transformers import TextIteratorStreamer
from functools import partial

from .base import BaseLLMProvider


class Qwen3Provider(BaseLLMProvider):
    """Qwen3 LLM提供商（基于 ModelScope）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "Qwen/Qwen3-VL-4B-Instruct")
        self.dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self.device_map = config.get("device_map", "auto")
        self.attn_implementation = config.get("attn_implementation")  # 可选：flash_attention_2
        self.max_new_tokens = config.get("max_new_tokens", 512)
        
        # 模型和处理器
        self._model = None
        self._processor = None
        
        # 启动时立即加载模型
        self._load_model()
    
    def _load_model(self):
        
        """在启动时加载 Qwen3 模型"""
        if self._model is not None:
            return
        
        try:
            from modelscope import Qwen3VLForConditionalGeneration, AutoProcessor
            
            logger.info(f"📦 加载 Qwen3 模型: {self.model_name}")
            
            # 构建模型加载参数
            model_kwargs = {
                "torch_dtype": self.dtype,
                "device_map": self.device_map,
            }
            
            # 如果配置了 flash_attention_2，添加该参数
            if self.attn_implementation:
                model_kwargs["attn_implementation"] = self.attn_implementation
            
            # 加载模型
            self._model = Qwen3VLForConditionalGeneration.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            # 加载处理器
            self._processor = AutoProcessor.from_pretrained(self.model_name)
            
            logger.info(f"✅ Qwen3 模型加载完成，设备: {self._model.device}")
            
        except ImportError as e:
            logger.error(f"❌ ModelScope 库未安装，请运行: pip install modelscope")
            raise
        except Exception as e:
            logger.error(f"❌ 加载 Qwen3 模型失败: {e}")
            raise
    
    async def is_available(self) -> bool:
        """检查 Qwen3 是否可用"""
        try:
            from modelscope import Qwen3VLForConditionalGeneration  # noqa: F401
            return self._model is not None and self._processor is not None
        except Exception as e:
            logger.warning(f"Qwen3Provider: modelscope 未安装或不可用: {e}")
            return False
    
    def _build_messages(self, prompt: str, **kwargs) -> List[Dict[str, Any]]:
        system_prompt = kwargs.get(
            "system_prompt",
            "你是Luna，一个友善、聪明、有趣的虚拟助手。请用自然、亲切的语调回复用户。请用简短的话语回复每次对话，并在合适的情况下提问，避免把天聊死",
        )

        full_prompt = f"{system_prompt}\n\n用户: {prompt}\n助手:"

        return [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": full_prompt}
                ]
            }
        ]

    def _prepare_inputs(self, messages: list):
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )
        return inputs.to(self._model.device)

    def _generate_sync(self, messages: list, max_new_tokens: int) -> str:
        """同步执行模型推理（在线程池中调用，避免阻塞事件循环）"""
        inputs = self._prepare_inputs(messages)
        
        # 推理：生成输出
        with torch.no_grad():
            generated_ids = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens
            )
        
        # 提取生成的文本（去除输入部分）
        generated_ids_trimmed = [
            out_ids[len(in_ids):] 
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        # 解码输出文本
        output_text = self._processor.batch_decode(
            generated_ids_trimmed,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False
        )
        
        return output_text[0] if output_text else ""
    
    def _estimate_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)

    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回复"""
        if not self._model or not self._processor:
            raise Exception("Qwen3 模型未加载")
        
        try:
            messages = self._build_messages(prompt, **kwargs)
            
            # 获取 max_new_tokens（优先使用 kwargs，否则使用配置）
            max_new_tokens = kwargs.get("max_new_tokens", self.max_new_tokens)
            
            # 在线程池中执行推理（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None,  # 使用默认线程池
                self._generate_sync,
                messages,
                max_new_tokens
            )
            
            # 计算 token 数量（近似值）
            # 注意：Qwen3 没有直接返回 token 数量，这里使用文本长度估算
            tokens_used = self._estimate_tokens(content)  # 粗略估算
            
            return {
                "content": content,
                "model": self.model_name,
                "tokens_used": int(tokens_used),
                "provider": "qwen3"
            }
            
        except Exception as e:
            logger.error(f"❌ Qwen3 生成回复失败: {str(e)}")
            raise Exception(f"Qwen3 生成回复失败: {str(e)}")

    @staticmethod
    def _next_from_streamer(streamer: TextIteratorStreamer) -> Optional[str]:
        try:
            return next(streamer)
        except StopIteration:
            return None

    async def stream_response(self, prompt: str, **kwargs) -> AsyncIterator[Dict[str, Any]]:
        """流式生成回复"""
        if not self._model or not self._processor:
            raise Exception("Qwen3 模型未加载")

        messages = self._build_messages(prompt, **kwargs)
        max_new_tokens = kwargs.get("max_new_tokens", self.max_new_tokens)

        tokenizer = getattr(self._processor, "tokenizer", None) or self._processor
        streamer = TextIteratorStreamer(
            tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        inputs = self._prepare_inputs(messages)
        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_new_tokens,
            "streamer": streamer,
        }

        loop = asyncio.get_running_loop()
        generation_future = loop.run_in_executor(
            None,
            partial(self._generate_with_streamer, generation_kwargs),
        )

        collected_chunks: List[str] = []

        try:
            while True:
                chunk = await loop.run_in_executor(None, self._next_from_streamer, streamer)
                if chunk is None:
                    break

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
        finally:
            await generation_future

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

    def _generate_with_streamer(self, generation_kwargs: Dict[str, Any]) -> None:
        with torch.no_grad():
            self._model.generate(**generation_kwargs)

