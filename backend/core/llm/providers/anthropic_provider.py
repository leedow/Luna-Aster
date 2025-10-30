"""
Anthropic LLM 提供商
支持 Claude 系列模型
"""

from typing import Dict, Any
from loguru import logger

from .base import BaseLLMProvider


class AnthropicProvider(BaseLLMProvider):
    """Anthropic LLM提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.client = None
        
        if self.api_key:
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
                logger.info(f"✅ Anthropic客户端初始化成功，模型: {self.model}")
            except ImportError:
                logger.error("❌ Anthropic库未安装，请运行: pip install anthropic")
            except Exception as e:
                logger.error(f"❌ Anthropic客户端初始化失败: {str(e)}")
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回复"""
        if not self.client:
            raise Exception("Anthropic客户端未初始化")
        
        try:
            # 调用Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # 解析响应
            content = response.content[0].text
            tokens_used = response.usage.input_tokens + response.usage.output_tokens if response.usage else 0
            
            return {
                "content": content,
                "model": self.model,
                "tokens_used": tokens_used,
                "provider": "anthropic"
            }
            
        except Exception as e:
            logger.error(f"❌ Anthropic API调用失败: {str(e)}")
            raise Exception(f"Anthropic API调用失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.client or not self.api_key:
            return False
        
        try:
            # 尝试调用API检查可用性
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ Anthropic服务不可用: {str(e)}")
            return False