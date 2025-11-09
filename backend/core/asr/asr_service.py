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
        """初始化ASR提供商（只加载配置的首选提供商）"""
        # 使用全局设置中的 ASR 配置
        asr_config = self.settings.asr_config
        # 获取首选提供商
        preferred_provider = self.settings.asr_provider
        
        if not preferred_provider:
            raise RuntimeError("❌ 未配置ASR提供商，请在配置中设置 asr_provider")
        
        # 只创建配置的首选提供商
        self.providers = ASRProviderFactory.create_providers_from_config(
            asr_config, 
            only_preferred=True, 
            preferred_provider=preferred_provider
        )
        
        if preferred_provider not in self.providers:
            raise RuntimeError(f"❌ 无法初始化ASR提供商: {preferred_provider}，请检查配置和依赖")
        
        logger.info(f"🎤 已初始化ASR提供商: {preferred_provider} (仅加载配置的提供商)")
    
    async def select_best_provider(self) -> Optional[BaseASRProvider]:
        """选择配置的ASR提供商（不使用降级逻辑）"""
        preferred = self.settings.asr_provider
        
        if not preferred:
            raise RuntimeError("❌ 未配置ASR提供商，请在配置中设置 asr_provider")
        
        # 只返回配置的提供商，不进行降级
        if preferred not in self.providers:
            raise RuntimeError(f"❌ ASR提供商 {preferred} 未初始化，请重启服务并检查配置")
        
        provider = self.providers[preferred]
        
        # 检查提供商是否可用
        if not await provider.is_available():
            raise RuntimeError(f"❌ ASR提供商 {preferred} 不可用，请检查依赖和配置。切换模型需要重启服务。")
        
        logger.debug(f"🎯 使用ASR提供商: {preferred}")
        return provider
    
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Optional[Dict[str, Any]]:
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
            
            # 如果返回None，表示没有有效识别结果（静音或空文本）
            if result is None:
                logger.debug(f"🎤 音频转录结果为空（静音或空文本），跳过处理")
                return None
            
            # 添加处理时间
            processing_time = (datetime.now() - start_time).total_seconds()
            result["processing_time"] = processing_time
            
            # 添加服务信息
            result["service"] = "ASR"
            result["timestamp"] = datetime.now().isoformat()
            
            # 再次检查文本是否为空（双重保险）
            text = result.get("text", "").strip()
            if not text:
                logger.debug(f"🎤 转录文本为空，跳过返回")
                return None
            
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
        """健康检查（只检查配置的提供商）"""
        preferred_provider = self.settings.asr_provider
        status = {
            "service": "ASR",
            "status": "healthy",
            "preferred_provider": preferred_provider,
            "providers": {},
            "total_providers": len(self.providers),
            "available_providers": 0,
            "temp_dir": self.temp_dir,
            "temp_dir_exists": os.path.exists(self.temp_dir)
        }
        
        # 只检查配置的提供商
        if preferred_provider and preferred_provider in self.providers:
            provider = self.providers[preferred_provider]
            try:
                is_available = await provider.is_available()
                status["providers"][preferred_provider] = {
                    "available": is_available,
                    "model": provider.model,
                    "language": provider.language,
                    "sample_rate": provider.sample_rate,
                    "provider_type": provider.get_provider_name()
                }
                if is_available:
                    status["available_providers"] = 1
                else:
                    status["status"] = "unhealthy"
                    status["error"] = f"配置的ASR提供商 {preferred_provider} 不可用"
            except Exception as e:
                status["providers"][preferred_provider] = {
                    "available": False,
                    "error": str(e)
                }
                status["status"] = "unhealthy"
                status["error"] = f"ASR提供商 {preferred_provider} 检查失败: {str(e)}"
        else:
            status["status"] = "unhealthy"
            status["error"] = f"配置的ASR提供商 {preferred_provider} 未初始化"
        
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