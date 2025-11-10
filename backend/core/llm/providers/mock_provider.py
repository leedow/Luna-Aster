"""
Mock LLM 提供商
用于测试和开发环境的模拟提供商
"""

import asyncio
import random
from typing import Dict, Any
from loguru import logger

from .base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM提供商，用于测试"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.info("✅ Mock LLM 提供商初始化成功")
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成模拟回复"""
        # 模拟API调用延迟
        #await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # 模拟回复内容
        mock_responses = [
            "我理解你的意思，这确实值得深入讨论。",
            "这是一个很有趣的问题，让我来为你分析一下。",
            "根据你提到的情况，我建议可以从以下几个方面考虑。",
            "感谢你的提问，我很乐意帮助你解决这个问题。",
            "这个话题很有意思，我们可以从不同角度来看待它。"
        ]
        
        content = random.choice(mock_responses)
        tokens_used = len(prompt) + len(content)
        
        return {
            "content": content,
            "model": self.model or "mock-model",
            "tokens_used": tokens_used,
            "provider": "mock"
        }
    
    async def is_available(self) -> bool:
        """Mock提供商总是可用"""
        return True