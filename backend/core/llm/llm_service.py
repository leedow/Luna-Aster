"""
LLM服务核心模块
支持多种LLM提供商（OpenAI、Anthropic等）
"""

import asyncio
from typing import Dict, Any, Optional, List, AsyncIterator
from datetime import datetime
from loguru import logger

from config.settings import Settings
from .providers import BaseLLMProvider, LLMProviderFactory


class LLMService:
    """LLM服务管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.current_provider = None
        self.conversation_history: Dict[str, List[Dict]] = {}
        
        # 初始化提供商
        self._initialize_providers()
    
    def _initialize_providers(self):
        print(44444444444444444444444444444444444)
        """初始化LLM提供商"""
        # 根据扁平配置创建提供商配置
        llm_config = {
            "qwen3": {
                "enabled": self.settings.qwen3_enabled,
                "model": self.settings.qwen3_model,
                "dtype": self.settings.qwen3_dtype,
                "device_map": self.settings.qwen3_device_map,
                "attn_implementation": self.settings.qwen3_attn_implementation,
                "max_new_tokens": self.settings.qwen3_max_new_tokens,
                "gpu_memory_utilization": getattr(self.settings, "qwen3_gpu_memory_utilization", 0.95),
                "max_model_len": getattr(self.settings, "qwen3_max_model_len", 8192),
            },
            # "openai": {
            #     "api_key": self.settings.openai_api_key,
            #     "model": self.settings.openai_model
            # },
            # "anthropic": {
            #     "api_key": self.settings.anthropic_api_key,
            #     "model": self.settings.anthropic_model
            # },
            # "mock": {
            #     "model": "mock-model"
            # }
        }
        
        # 使用工厂创建提供商
        self.providers = LLMProviderFactory.create_providers_from_config(llm_config)
        
        logger.info(f"📋 已初始化LLM提供商: {list(self.providers.keys())}")
    
    async def select_best_provider(self) -> Optional[BaseLLMProvider]:
        """选择最佳可用的提供商"""
        # 优先级顺序（Qwen3 作为默认首选）
        priority_order = ["qwen3", "openai", "anthropic", "mock"]
        
        for provider_name in priority_order:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if await provider.is_available():
                    logger.info(f"🎯 选择LLM提供商: {provider_name}")
                    return provider
        
        logger.warning("⚠️ 没有可用的LLM提供商")
        return None
    
    def _record_conversation(self, client_id: Optional[str], prompt: str, response: Dict[str, Any], start_time: datetime):
        if not client_id:
            return

        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []

        self.conversation_history[client_id].extend([
            {
                "role": "user",
                "content": prompt,
                "timestamp": start_time.isoformat()
            },
            {
                "role": "assistant",
                "content": response.get("content", ""),
                "timestamp": datetime.now().isoformat(),
                "model": response.get("model"),
                "provider": response.get("provider")
            }
        ])

        if len(self.conversation_history[client_id]) > 20:
            self.conversation_history[client_id] = self.conversation_history[client_id][-20:]

    async def generate_response(self, prompt: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """生成回复"""
        start_time = datetime.now()
        
        try:
            # 选择提供商
            provider = await self.select_best_provider()
            if not provider:
                raise Exception("没有可用的LLM提供商")
            
            # 获取会话历史，供 provider 进行前缀缓存复用
            history = self.get_conversation_history(client_id) if client_id else []

            # 生成回复
            response = await provider.generate_response(prompt, history=history)
            
            # 记录对话历史
            self._record_conversation(client_id, prompt, response, start_time)
            
            # 添加处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            response["processing_time"] = processing_time
            
            return response
            
        except Exception as e:
            logger.error(f"❌ LLM回复生成失败: {str(e)}")
            raise Exception(f"LLM回复生成失败: {str(e)}")

    async def stream_response(self, prompt: str, client_id: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
        """流式生成回复，yield chunk 和最终响应"""
        start_time = datetime.now()
        provider = await self.select_best_provider()
        if not provider:
            raise Exception("没有可用的LLM提供商")

        provider_name = provider.get_provider_name()
        collected_chunks: List[str] = []

        # 获取会话历史，供 provider 进行前缀缓存复用
        history = self.get_conversation_history(client_id) if client_id else []

        async for event in provider.stream_response(prompt, history=history):
            content = event.get("content")
            if content:
                collected_chunks.append(content)
                yield {
                    "type": "chunk",
                    "content": content,
                    "model": provider.model,
                    "provider": provider_name,
                }

            if event.get("is_final"):
                response = event.get("metadata") or {}
                if not response.get("content"):
                    response["content"] = "".join(collected_chunks).strip()
                response.setdefault("model", provider.model)
                response.setdefault("provider", provider_name)
                response.setdefault("tokens_used", int(len(response["content"].split()) * 1.3))

                processing_time = (datetime.now() - start_time).total_seconds()
                response["processing_time"] = processing_time

                self._record_conversation(client_id, prompt, response, start_time)

                yield {
                    "type": "final",
                    "response": response,
                }
                break
    
    def get_conversation_history(self, client_id: str) -> List[Dict]:
        """获取对话历史"""
        return self.conversation_history.get(client_id, [])
    
    def clear_conversation_history(self, client_id: str):
        """清除对话历史"""
        if client_id in self.conversation_history:
            del self.conversation_history[client_id]
            logger.info(f"🗑️ 已清除客户端 {client_id} 的对话历史")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = {
            "service": "LLM",
            "status": "healthy",
            "providers": {},
            "total_providers": len(self.providers),
            "available_providers": 0
        }
        
        # 检查每个提供商的状态
        for name, provider in self.providers.items():
            try:
                is_available = await provider.is_available()
                status["providers"][name] = {
                    "available": is_available,
                    "model": provider.model,
                    "provider_type": provider.get_provider_name()
                }
                if is_available:
                    status["available_providers"] += 1
            except Exception as e:
                status["providers"][name] = {
                    "available": False,
                    "error": str(e)
                }
        
        # 如果没有可用提供商，标记为不健康
        if status["available_providers"] == 0:
            status["status"] = "unhealthy"
        
        return status