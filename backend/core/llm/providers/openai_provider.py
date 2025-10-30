"""
OpenAI LLM 提供商
支持 OpenAI GPT 系列模型
"""

from typing import Dict, Any
from loguru import logger

from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.openai.com/v1")
        self.client = None
        
        if self.api_key:
            try:
                import openai
                self.client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info(f"✅ OpenAI客户端初始化成功，模型: {self.model}")
            except ImportError:
                logger.error("❌ OpenAI库未安装，请运行: pip install openai")
            except Exception as e:
                logger.error(f"❌ OpenAI客户端初始化失败: {str(e)}")
    
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成回复"""
        if not self.client:
            raise Exception("OpenAI客户端未初始化")
        
        try:
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": "你是Luna，一个友善、聪明、有趣的虚拟助手。请用自然、亲切的语调回复用户。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 调用API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            
            # 解析响应
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else 0
            
            return {
                "content": content,
                "model": self.model,
                "tokens_used": tokens_used,
                "provider": "openai"
            }
            
        except Exception as e:
            logger.error(f"❌ OpenAI API调用失败: {str(e)}")
            raise Exception(f"OpenAI API调用失败: {str(e)}")
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        if not self.client or not self.api_key:
            return False
        
        try:
            # 尝试调用API检查可用性
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"⚠️ OpenAI服务不可用: {str(e)}")
            return False