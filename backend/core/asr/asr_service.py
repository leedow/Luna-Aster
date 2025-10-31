"""
ASR服务核心模块
支持多种语音识别提供商（Whisper、SpeechRecognition等）
"""

import asyncio
import os
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from config.settings import Settings
from .providers import BaseASRProvider, ASRProviderFactory


class ASRService:
    """ASR服务管理器"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers: Dict[str, BaseASRProvider] = {}
        self.current_provider = None
        self.temp_dir = settings.audio_temp_dir
        
        # 确保临时目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 初始化提供商
        self._initialize_providers()
    
    def _initialize_providers(self):
        """初始化ASR提供商"""
        # 根据扁平配置创建提供商配置
        asr_config = {
            "whisper": {
                "api_key": self.settings.openai_api_key,
                "model": self.settings.whisper_model
            },
            "speech_recognition": {
                "engine": "google"
            },
            "mock": {
                "model": "mock-model"
            }
        }
        
        # 使用工厂创建提供商
        self.providers = ASRProviderFactory.create_providers_from_config(asr_config)
        
        logger.info(f"🎤 已初始化ASR提供商: {list(self.providers.keys())}")
    
    async def select_best_provider(self) -> Optional[BaseASRProvider]:
        """选择最佳可用的提供商"""
        # 优先级顺序
        priority_order = ["whisper", "speech_recognition", "mock"]
        
        for provider_name in priority_order:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if await provider.is_available():
                    logger.info(f"🎯 选择ASR提供商: {provider_name}")
                    return provider
        
        logger.warning("⚠️ 没有可用的ASR提供商")
        return None
    
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """转录音频"""
        start_time = datetime.now()
        
        try:
            # 验证音频数据
            if not audio_data or len(audio_data) == 0:
                raise Exception("音频数据为空")
            
            # 选择提供商
            provider = await self.select_best_provider()
            if not provider:
                raise Exception("没有可用的ASR提供商")
            
            # 执行转录
            result = await provider.transcribe_audio(audio_data, **kwargs)
            
            # 添加处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            
            # 添加服务信息
            result["service"] = "ASR"
            result["timestamp"] = datetime.now().isoformat()
            
            logger.info(f"🎤 音频转录成功: {result['text'][:50]}... (用时: {processing_time:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ 音频转录失败: {str(e)}")
            raise Exception(f"音频转录失败: {str(e)}")
    
    async def transcribe_file(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """转录音频文件"""
        try:
            # 读取文件
            with open(file_path, "rb") as f:
                audio_data = f.read()
            
            # 调用转录方法
            result = await self.transcribe_audio(audio_data, **kwargs)
            result["source_file"] = file_path
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 文件转录失败: {str(e)}")
            raise Exception(f"文件转录失败: {str(e)}")
    
    def save_audio_temp(self, audio_data: bytes, suffix: str = ".wav") -> str:
        """保存音频到临时文件"""
        try:
            temp_file = tempfile.NamedTemporaryFile(
                dir=self.temp_dir,
                suffix=suffix,
                delete=False
            )
            temp_file.write(audio_data)
            temp_file.close()
            
            logger.debug(f"💾 音频已保存到临时文件: {temp_file.name}")
            return temp_file.name
            
        except Exception as e:
            logger.error(f"❌ 保存临时音频文件失败: {str(e)}")
            raise Exception(f"保存临时音频文件失败: {str(e)}")
    
    def cleanup_temp_file(self, file_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.debug(f"🗑️ 已清理临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ 清理临时文件失败: {str(e)}")
    
    async def batch_transcribe(self, audio_files: List[str], **kwargs) -> List[Dict[str, Any]]:
        """批量转录音频文件"""
        results = []
        
        for file_path in audio_files:
            try:
                result = await self.transcribe_file(file_path, **kwargs)
                results.append(result)
            except Exception as e:
                error_result = {
                    "source_file": file_path,
                    "error": str(e),
                    "success": False
                }
                results.append(error_result)
                logger.error(f"❌ 批量转录失败 {file_path}: {str(e)}")
        
        logger.info(f"📊 批量转录完成: {len(results)} 个文件")
        return results
    
    async def start_listening(self, client_id: str) -> Dict[str, Any]:
        """开始语音识别监听"""
        logger.info(f"🎤 开始为客户端 {client_id} 启动语音识别")
        
        # 这里可以添加实时语音识别的逻辑
        # 目前只是返回状态确认
        return {
            "status": "listening",
            "client_id": client_id,
            "message": "语音识别已启动"
        }
    
    async def stop_listening(self, client_id: str) -> Dict[str, Any]:
        """停止语音识别监听"""
        logger.info(f"🛑 停止客户端 {client_id} 的语音识别")
        
        # 这里可以添加停止实时语音识别的逻辑
        # 目前只是返回状态确认
        return {
            "status": "stopped",
            "client_id": client_id,
            "message": "语音识别已停止"
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = {
            "service": "ASR",
            "status": "healthy",
            "providers": {},
            "total_providers": len(self.providers),
            "available_providers": 0,
            "temp_dir": self.temp_dir,
            "temp_dir_exists": os.path.exists(self.temp_dir)
        }
        
        # 检查每个提供商的状态
        for name, provider in self.providers.items():
            try:
                is_available = await provider.is_available()
                status["providers"][name] = {
                    "available": is_available,
                    "model": provider.model,
                    "language": provider.language,
                    "sample_rate": provider.sample_rate,
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
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的音频格式"""
        return [".wav", ".mp3", ".m4a", ".flac", ".ogg"]
    
    def get_provider_info(self, provider_name: str) -> Dict[str, Any]:
        """获取提供商信息"""
        if provider_name not in self.providers:
            return {}
        
        provider = self.providers[provider_name]
        return {
            "name": provider_name,
            "model": provider.model,
            "language": provider.language,
            "sample_rate": provider.sample_rate,
            "provider_type": provider.get_provider_name(),
            "config": provider.config
        }