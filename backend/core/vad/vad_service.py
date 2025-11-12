"""
VAD服务核心模块
支持多种语音活动检测提供商（Silero VAD等）
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from config.settings import Settings
from .providers import BaseVADProvider, VADProviderFactory


class VADService:
    """VAD服务管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: Dict[str, BaseVADProvider] = {}
        self.current_provider = None
        
        # 初始化提供商
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化VAD提供商（只加载配置的首选提供商）"""
        # 使用全局设置中的 VAD 配置
        vad_config = getattr(self.settings, 'vad_config', {})
        # 获取首选提供商
        preferred_provider = getattr(self.settings, 'vad_provider', 'silero')
        
        if not vad_config:
            logger.warning("⚠️ 未配置VAD提供商，将使用默认配置")
            vad_config = {
                "silero": {
                    "enabled": True,
                    "model": "silero-vad",
                    "device": "cpu",
                    "threshold": 0.5,
                    "sample_rate": 16000,
                }
            }
        
        # 只创建配置的首选提供商
        self.providers = VADProviderFactory.create_providers_from_config(
            vad_config, 
            only_preferred=True, 
            preferred_provider=preferred_provider
        )
        
        if preferred_provider not in self.providers:
            logger.warning(f"⚠️ 无法初始化VAD提供商: {preferred_provider}，将使用Mock提供商")
            # 回退到Mock提供商
            mock_config = {"enabled": True, "always_detect": False, "detection_rate": 0.5}
            mock_provider = VADProviderFactory.create_provider("mock", mock_config)
            if mock_provider:
                self.providers["mock"] = mock_provider
                preferred_provider = "mock"
        
        logger.info(f"🎤 已初始化VAD提供商: {preferred_provider}")
    
    async def select_best_provider(self) -> Optional[BaseVADProvider]:
        """选择配置的VAD提供商"""
        preferred = getattr(self.settings, 'vad_provider', 'silero')
        
        if not preferred:
            logger.warning("⚠️ 未配置VAD提供商，使用默认")
            preferred = "silero"
        
        # 如果配置的提供商不存在，尝试使用可用的提供商
        if preferred not in self.providers:
            if self.providers:
                preferred = list(self.providers.keys())[0]
                logger.warning(f"⚠️ 配置的VAD提供商不存在，使用: {preferred}")
            else:
                raise RuntimeError("❌ 没有可用的VAD提供商")
        
        provider = self.providers[preferred]
        
        # 检查提供商是否可用
        if not await provider.is_available():
            logger.warning(f"⚠️ VAD提供商 {preferred} 不可用，尝试其他提供商")
            # 尝试其他提供商
            for name, prov in self.providers.items():
                if await prov.is_available():
                    logger.info(f"✅ 使用VAD提供商: {name}")
                    return prov
            raise RuntimeError("❌ 没有可用的VAD提供商")
        
        logger.debug(f"🎯 使用VAD提供商: {preferred}")
        return provider
    
    async def detect_speech(self, audio_data: bytes, **kwargs) -> Optional[Dict[str, Any]]:
        """
        检测音频中的语音活动
        
        Args:
            audio_data: 音频字节数据
            **kwargs: 额外参数
                - client_id: 客户端ID
                - audio_format: 音频格式 ('pcm' 或 'wav')
                - sample_rate: 采样率
                - channels: 声道数
        
        Returns:
            Dict包含检测结果，如果检测失败返回None
        """
        start_time = datetime.now()
        
        try:
            # 验证音频数据
            if not audio_data or len(audio_data) == 0:
                logger.debug("⚠️ 音频数据为空，跳过VAD检测")
                return None
            
            # 选择提供商
            provider = await self.select_best_provider()
            if not provider:
                raise Exception("没有可用的VAD提供商")
            
            # 执行检测
            result = await provider.detect_speech(audio_data, **kwargs)
            
            if result is None:
                logger.debug(f"🎤 VAD检测结果为空")
                return None
            
            # 添加处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            
            # 添加服务信息
            result["service"] = "VAD"
            result["timestamp"] = datetime.now().isoformat()
            result["provider"] = provider.get_provider_name()
            
            logger.debug(f"🎤 VAD检测完成: detected={result.get('vad_detected')}, active={result.get('speech_active')} (用时: {processing_time:.3f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ VAD检测失败: {str(e)}")
            raise Exception(f"VAD检测失败: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        preferred_provider = getattr(self.settings, 'vad_provider', 'silero')
        status = {
            "service": "VAD",
            "status": "healthy",
            "preferred_provider": preferred_provider,
            "providers": {},
            "total_providers": len(self.providers),
            "available_providers": 0,
        }
        
        # 检查所有提供商
        for provider_name, provider in self.providers.items():
            try:
                is_available = await provider.is_available()
                status["providers"][provider_name] = {
                    "available": is_available,
                    "model": provider.model,
                    "sample_rate": provider.sample_rate,
                    "provider_type": provider.get_provider_name()
                }
                if is_available:
                    status["available_providers"] += 1
            except Exception as e:
                status["providers"][provider_name] = {
                    "available": False,
                    "error": str(e)
                }
        
        if status["available_providers"] == 0:
            status["status"] = "unhealthy"
            status["error"] = "没有可用的VAD提供商"
        
        return status

