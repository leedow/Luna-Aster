"""
Mock ASR 提供商实现
用于测试和开发的模拟语音识别服务
"""

import asyncio
import random
from typing import Dict, Any
from loguru import logger

from .base import BaseASRProvider


class MockASRProvider(BaseASRProvider):
    """模拟ASR提供商（用于测试）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        logger.info("✅ Mock ASR提供商初始化成功")
    
    async def transcribe_audio(self, audio_data: bytes, **kwargs) -> Dict[str, Any]:
        """模拟音频转录"""
        # 模拟处理时间
        await asyncio.sleep(random.uniform(0.5, 2.0))
        
        # 模拟转录结果
        mock_texts = [
            "你好，我想要查询天气信息",
            "请帮我播放一首音乐",
            "今天的新闻有什么",
            "设置一个提醒",
            "我想要了解股票行情",
            "请告诉我时间",
            "帮我搜索一下资料",
            "我要预定餐厅",
            "查看我的日程安排",
            "发送一条消息"
        ]
        
        # 根据音频长度选择不同的文本
        audio_length = len(audio_data)
        if audio_length < 1000:
            text = "你好"
        elif audio_length < 5000:
            text = random.choice(mock_texts[:5])
        else:
            text = random.choice(mock_texts)
        
        # 模拟置信度
        confidence = random.uniform(0.7, 0.95)
        
        # 模拟时长（基于音频数据大小估算）
        duration = max(1.0, audio_length / 16000)  # 假设16kHz采样率
        
        result = {
            "text": text,
            "language": self.language,
            "duration": duration,
            "model": "mock-asr-model",
            "provider": "mock",
            "confidence": confidence
        }
        
        # 模拟分段信息
        if len(text) > 10:
            words = text.split()
            segments = []
            current_time = 0.0
            
            for i, word in enumerate(words):
                segment_duration = random.uniform(0.3, 0.8)
                segments.append({
                    "start": current_time,
                    "end": current_time + segment_duration,
                    "text": word
                })
                current_time += segment_duration
            
            result["segments"] = segments
        
        logger.info(f"🎤 Mock ASR转录完成: {text}")
        return result
    
    async def is_available(self) -> bool:
        """检查服务是否可用"""
        # Mock服务总是可用
        return True
    
    def validate_audio_format(self, audio_data: bytes) -> bool:
        """验证音频格式"""
        # Mock服务接受任何格式
        return len(audio_data) > 0