"""
LLM 提供商基类
定义所有 LLM 提供商的统一接口
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseLLMProvider(ABC):
    """LLM提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model = config.get("model")
        self.max_tokens = config.get("max_tokens", 1000)
        self.temperature = config.get("temperature", 0.7)
    
    @abstractmethod
    async def generate_response(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        生成回复
        
        Args:
            prompt: 输入提示
            **kwargs: 额外参数
            
        Returns:
            Dict[str, Any]: 包含生成内容的字典
                - content: 生成的文本内容
                - model: 使用的模型名称
                - tokens_used: 使用的token数量
                - provider: 提供商名称
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        pass
    
    def get_provider_name(self) -> str:
        """
        获取提供商名称
        
        Returns:
            str: 提供商名称
        """
        return self.__class__.__name__.replace("Provider", "").lower()