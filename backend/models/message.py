"""
消息数据模型定义
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field

class MessageType(str, Enum):
    """消息类型枚举"""
    # 基础消息类型
    CHAT = "chat"                           # 文本聊天
    SYSTEM = "system"                       # 系统消息
    ERROR = "error"                         # 错误消息
    
    # 连接相关
    CONNECTION_ESTABLISHED = "connection_established"  # 连接建立
    CONNECTION_LOST = "connection_lost"                # 连接丢失
    HEARTBEAT = "heartbeat"                           # 心跳
    
    # 语音相关
    START_LISTENING = "start_listening"     # 开始语音识别
    STOP_LISTENING = "stop_listening"       # 停止语音识别
    AUDIO_DATA = "audio_data"               # 音频数据
    SPEECH_RECOGNIZED = "speech_recognized" # 语音识别结果
    
    # TTS 相关
    START_SPEAKING = "start_speaking"       # 开始语音合成
    STOP_SPEAKING = "stop_speaking"         # 停止语音合成
    AUDIO_GENERATED = "audio_generated"     # 音频生成完成
    
    # LLM 相关
    LLM_THINKING = "llm_thinking"           # LLM 思考中
    LLM_RESPONSE = "llm_response"           # LLM 响应
    
    # 状态相关
    STATUS_UPDATE = "status_update"         # 状态更新
    SERVICE_READY = "service_ready"         # 服务就绪
    SERVICE_ERROR = "service_error"         # 服务错误

class Message(BaseModel):
    """消息基础模型"""
    type: MessageType = Field(..., description="消息类型")
    content: Optional[str] = Field(None, description="消息内容")
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
    client_id: Optional[str] = Field(None, description="客户端ID")
    message_id: Optional[str] = Field(None, description="消息ID")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ChatMessage(Message):
    """聊天消息模型"""
    type: MessageType = MessageType.CHAT
    content: str = Field(..., description="聊天内容")
    sender: str = Field(default="user", description="发送者")
    
class SystemMessage(Message):
    """系统消息模型"""
    type: MessageType = MessageType.SYSTEM
    content: str = Field(..., description="系统消息内容")
    level: str = Field(default="info", description="消息级别: info, warning, error")

class ErrorMessage(Message):
    """错误消息模型"""
    type: MessageType = MessageType.ERROR
    content: str = Field(..., description="错误信息")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")

class AudioMessage(Message):
    """音频消息模型"""
    type: MessageType = MessageType.AUDIO_DATA
    audio_data: Optional[str] = Field(None, description="Base64编码的音频数据")
    audio_format: str = Field(default="wav", description="音频格式")
    sample_rate: int = Field(default=16000, description="采样率")
    duration: Optional[float] = Field(None, description="音频时长(秒)")

class SpeechRecognitionMessage(Message):
    """语音识别结果消息"""
    type: MessageType = MessageType.SPEECH_RECOGNIZED
    content: str = Field(..., description="识别的文本")
    confidence: Optional[float] = Field(None, description="置信度")
    language: Optional[str] = Field(None, description="识别的语言")

class LLMResponseMessage(Message):
    """LLM响应消息"""
    type: MessageType = MessageType.LLM_RESPONSE
    content: str = Field(..., description="LLM生成的回复")
    model: Optional[str] = Field(None, description="使用的模型")
    tokens_used: Optional[int] = Field(None, description="使用的token数量")
    processing_time: Optional[float] = Field(None, description="处理时间(秒)")

class StatusUpdateMessage(Message):
    """状态更新消息"""
    type: MessageType = MessageType.STATUS_UPDATE
    service: str = Field(..., description="服务名称")
    status: str = Field(..., description="状态: ready, busy, error, offline")
    details: Optional[Dict[str, Any]] = Field(None, description="状态详情")

class AudioGeneratedMessage(Message):
    """音频生成完成消息"""
    type: MessageType = MessageType.AUDIO_GENERATED
    audio_data: str = Field(..., description="Base64编码的音频数据")
    audio_format: str = Field(default="wav", description="音频格式")
    text: str = Field(..., description="合成的文本")
    voice: Optional[str] = Field(None, description="使用的语音")

# 消息工厂函数
def create_chat_message(content: str, sender: str = "user", client_id: Optional[str] = None) -> ChatMessage:
    """创建聊天消息"""
    return ChatMessage(content=content, sender=sender, client_id=client_id)

def create_system_message(content: str, level: str = "info", client_id: Optional[str] = None) -> SystemMessage:
    """创建系统消息"""
    return SystemMessage(content=content, level=level, client_id=client_id)

def create_error_message(content: str, error_code: Optional[str] = None, 
                        details: Optional[Dict[str, Any]] = None, 
                        client_id: Optional[str] = None) -> ErrorMessage:
    """创建错误消息"""
    return ErrorMessage(
        content=content, 
        error_code=error_code, 
        details=details, 
        client_id=client_id
    )

def create_llm_response_message(content: str, model: Optional[str] = None,
                               tokens_used: Optional[int] = None,
                               processing_time: Optional[float] = None,
                               client_id: Optional[str] = None) -> LLMResponseMessage:
    """创建LLM响应消息"""
    return LLMResponseMessage(
        content=content,
        model=model,
        tokens_used=tokens_used,
        processing_time=processing_time,
        client_id=client_id
    )

def create_status_update_message(service: str, status: str, 
                                details: Optional[Dict[str, Any]] = None,
                                client_id: Optional[str] = None) -> StatusUpdateMessage:
    """创建状态更新消息"""
    return StatusUpdateMessage(
        service=service,
        status=status,
        details=details,
        client_id=client_id
    )