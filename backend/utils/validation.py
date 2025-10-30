"""
数据验证工具模块
提供消息、音频、文本等数据的验证功能
"""

import re
from typing import Optional, Dict, Any
from loguru import logger

def validate_message_content(content: str, max_length: int = 1000) -> bool:
    """验证消息内容"""
    try:
        # 检查是否为空
        if not content or not content.strip():
            return False
        
        # 检查长度
        if len(content) > max_length:
            logger.warning(f"⚠️ 消息内容过长: {len(content)} > {max_length}")
            return False
        
        # 检查是否包含恶意内容（简单示例）
        malicious_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning(f"⚠️ 检测到潜在恶意内容: {pattern}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 消息内容验证失败: {str(e)}")
        return False

def validate_client_id(client_id: str) -> bool:
    """验证客户端ID"""
    try:
        # 检查是否为空
        if not client_id or not client_id.strip():
            return False
        
        # 检查格式（UUID格式）
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, client_id, re.IGNORECASE):
            logger.warning(f"⚠️ 客户端ID格式无效: {client_id}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 客户端ID验证失败: {str(e)}")
        return False

def validate_audio_metadata(metadata: Dict[str, Any]) -> bool:
    """验证音频元数据"""
    try:
        required_fields = ['format', 'sample_rate', 'channels']
        
        # 检查必需字段
        for field in required_fields:
            if field not in metadata:
                logger.warning(f"⚠️ 缺少必需的音频元数据字段: {field}")
                return False
        
        # 验证格式
        valid_formats = ['wav', 'mp3', 'ogg', 'flac']
        if metadata['format'] not in valid_formats:
            logger.warning(f"⚠️ 不支持的音频格式: {metadata['format']}")
            return False
        
        # 验证采样率
        valid_sample_rates = [8000, 16000, 22050, 44100, 48000]
        if metadata['sample_rate'] not in valid_sample_rates:
            logger.warning(f"⚠️ 不支持的采样率: {metadata['sample_rate']}")
            return False
        
        # 验证声道数
        if metadata['channels'] not in [1, 2]:
            logger.warning(f"⚠️ 不支持的声道数: {metadata['channels']}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 音频元数据验证失败: {str(e)}")
        return False

def sanitize_text(text: str) -> str:
    """清理文本内容"""
    try:
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 移除控制字符
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text
    except Exception as e:
        logger.error(f"❌ 文本清理失败: {str(e)}")
        return text

def validate_rate_limit(client_id: str, requests_count: int, time_window: int, max_requests: int = 100) -> bool:
    """验证速率限制"""
    try:
        if requests_count > max_requests:
            logger.warning(f"⚠️ 客户端 {client_id} 超过速率限制: {requests_count}/{max_requests} 在 {time_window}秒内")
            return False
        
        return True
    except Exception as e:
        logger.error(f"❌ 速率限制验证失败: {str(e)}")
        return False