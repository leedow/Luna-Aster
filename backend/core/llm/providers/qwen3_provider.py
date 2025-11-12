"""
Qwen3 LLM 提供商
支持 Qwen3-VL 系列模型（基于 ModelScope）
"""

from typing import Dict, Any, Optional
from loguru import logger
import asyncio
import torch

from .base import BaseLLMProvider


class Qwen3Provider(BaseLLMProvider):
    """Qwen3 LLM提供商（基于 ModelScope）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get("model", "Qwen/Qwen3-VL-2B-Instruct")
        self.dtype = torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32
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
    
    def _generate_sync(self, messages: list, max_new_tokens: int) -> str:
        """同步执行模型推理（在线程池中调用，避免阻塞事件循环）"""
        # 准备输入
        inputs = self._processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )
        inputs = inputs.to(self._model.device)
        
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
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回复"""
        if not self._model or not self._processor:
            raise Exception("Qwen3 模型未加载")
        
        try:
            # 构建消息（纯文本模式）
            # Qwen3 支持多模态，但这里我们只使用文本
            # 注意：Qwen3 可能不支持 system 角色，所以将系统提示合并到用户消息中
            system_prompt = kwargs.get("system_prompt", "你是Luna，一个友善、聪明、有趣的虚拟助手。请用自然、亲切的语调回复用户。")
            
            # 构建完整的用户提示（包含系统提示）
            full_prompt = f"{system_prompt}\n\n用户: {prompt}\n助手:"
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt}
                    ]
                }
            ]
            
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
            tokens_used = len(content.split()) * 1.3  # 粗略估算
            
            return {
                "content": content,
                "model": self.model_name,
                "tokens_used": int(tokens_used),
                "provider": "qwen3"
            }
            
        except Exception as e:
            logger.error(f"❌ Qwen3 生成回复失败: {str(e)}")
            raise Exception(f"Qwen3 生成回复失败: {str(e)}")

