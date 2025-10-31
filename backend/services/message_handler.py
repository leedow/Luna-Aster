"""
消息处理服务
负责处理不同类型的消息并调用相应的服务
"""

import asyncio
from typing import Optional
from datetime import datetime
from loguru import logger

from models.message import (
    Message, MessageType, 
    create_llm_response_message,
    create_system_message,
    create_error_message,
    create_status_update_message
)
from core.llm.llm_service import LLMService
from core.asr.asr_service import ASRService
from core.tts.tts_service import TTSService

class MessageHandler:
    """消息处理器"""
    
    def __init__(self, llm_service: LLMService, asr_service: ASRService, tts_service: TTSService):
        self.llm_service = llm_service
        self.asr_service = asr_service
        self.tts_service = tts_service
        self.total_messages = 0
        
        # 用户会话状态
        self.user_sessions = {}
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息的主入口"""
        self.total_messages += 1
        
        try:
            # 根据消息类型分发处理
            handler_map = {
                MessageType.CHAT: self._handle_chat_message,
                MessageType.CONNECTION_ESTABLISHED: self._handle_connection_established,
                MessageType.START_LISTENING: self._handle_start_listening,
                MessageType.STOP_LISTENING: self._handle_stop_listening,
                MessageType.AUDIO_DATA: self._handle_audio_data,
                MessageType.START_SPEAKING: self._handle_start_speaking,
                MessageType.STOP_SPEAKING: self._handle_stop_speaking,
                MessageType.HEARTBEAT: self._handle_heartbeat,
            }
            
            handler = handler_map.get(message.type)
            if handler:
                return await handler(message)
            else:
                logger.warning(f"⚠️ 未知的消息类型: {message.type}")
                return create_error_message(
                    f"未知的消息类型: {message.type}",
                    error_code="UNKNOWN_MESSAGE_TYPE",
                    client_id=message.client_id
                )
                
        except Exception as e:
            logger.error(f"❌ 处理消息时发生错误: {str(e)}")
            return create_error_message(
                f"处理消息时发生错误: {str(e)}",
                error_code="MESSAGE_PROCESSING_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_chat_message(self, message: Message) -> Optional[Message]:
        """处理聊天消息"""
        if not message.content:
            return create_error_message(
                "聊天消息内容不能为空",
                error_code="EMPTY_CHAT_MESSAGE",
                client_id=message.client_id
            )
        
        logger.info(f"💬 处理聊天消息: {message.content[:50]}...")
        
        try:
            # 调用LLM服务生成回复
            start_time = datetime.now()
            response = await self.llm_service.generate_response(
                message.content, 
                client_id=message.client_id
            )
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 创建LLM响应消息
            llm_response = create_llm_response_message(
                content=response.get("content", "抱歉，我无法生成回复。"),
                model=response.get("model"),
                tokens_used=response.get("tokens_used"),
                processing_time=processing_time,
                client_id=message.client_id
            )
            
            logger.info(f"🤖 LLM回复生成完成，耗时: {processing_time:.2f}秒")
            return llm_response
            
        except Exception as e:
            logger.error(f"❌ LLM处理失败: {str(e)}")
            return create_error_message(
                f"生成回复时发生错误: {str(e)}",
                error_code="LLM_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_connection_established(self, message: Message) -> Optional[Message]:
        """处理连接建立消息"""
        logger.info(f"🤝 客户端 {message.client_id} 连接已确认")
        
        # 初始化用户会话
        if message.client_id:
            self.user_sessions[message.client_id] = {
                "connected_at": datetime.now(),
                "is_listening": False,
                "is_speaking": False,
                "conversation_history": []
            }
        
        return create_system_message(
            "连接已建立，Luna 已准备就绪！",
            level="info",
            client_id=message.client_id
        )
    
    async def _handle_start_listening(self, message: Message) -> Optional[Message]:
        """处理开始语音识别消息"""
        logger.info(f"🎤 客户端 {message.client_id} 开始语音识别")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_listening"] = True
        
        # 启动ASR服务
        try:
            await self.asr_service.start_listening(message.client_id)
            return create_status_update_message(
                service="asr",
                status="listening",
                details={"message": "语音识别已启动"},
                client_id=message.client_id
            )
        except Exception as e:
            logger.error(f"❌ 启动语音识别失败: {str(e)}")
            return create_error_message(
                f"启动语音识别失败: {str(e)}",
                error_code="ASR_START_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_stop_listening(self, message: Message) -> Optional[Message]:
        """处理停止语音识别消息"""
        logger.info(f"🛑 客户端 {message.client_id} 停止语音识别")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_listening"] = False
        
        # 停止ASR服务
        try:
            await self.asr_service.stop_listening(message.client_id)
            return create_status_update_message(
                service="asr",
                status="stopped",
                details={"message": "语音识别已停止"},
                client_id=message.client_id
            )
        except Exception as e:
            logger.error(f"❌ 停止语音识别失败: {str(e)}")
            return create_error_message(
                f"停止语音识别失败: {str(e)}",
                error_code="ASR_STOP_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_audio_data(self, message: Message) -> Optional[Message]:
        """处理音频数据消息"""
        logger.debug(f"🎵 收到客户端 {message.client_id} 的音频数据")
        
        try:
            # 处理音频数据
            if message.data and "audio_data" in message.data:
                # 解码 base64 音频数据
                import base64
                audio_data = base64.b64decode(message.data["audio_data"])
                result = await self.asr_service.transcribe_audio(audio_data)
                
                if result and result.get("text"):
                    # 如果识别出文本，自动处理为聊天消息
                    chat_message = Message(
                        type=MessageType.CHAT,
                        content=result["text"],
                        client_id=message.client_id
                    )
                    return await self._handle_chat_message(chat_message)
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 处理音频数据失败: {str(e)}")
            return create_error_message(
                f"处理音频数据失败: {str(e)}",
                error_code="AUDIO_PROCESSING_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_start_speaking(self, message: Message) -> Optional[Message]:
        """处理开始语音合成消息"""
        logger.info(f"🔊 客户端 {message.client_id} 开始语音合成")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_speaking"] = True
        
        return create_status_update_message(
            service="tts",
            status="speaking",
            details={"message": "语音合成已启动"},
            client_id=message.client_id
        )
    
    async def _handle_stop_speaking(self, message: Message) -> Optional[Message]:
        """处理停止语音合成消息"""
        logger.info(f"🔇 客户端 {message.client_id} 停止语音合成")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_speaking"] = False
        
        return create_status_update_message(
            service="tts",
            status="stopped",
            details={"message": "语音合成已停止"},
            client_id=message.client_id
        )
    
    async def _handle_heartbeat(self, message: Message) -> Optional[Message]:
        """处理心跳消息"""
        logger.debug(f"💓 收到客户端 {message.client_id} 的心跳")
        
        # 返回心跳响应
        return Message(
            type=MessageType.HEARTBEAT,
            content="pong",
            timestamp=datetime.now(),
            client_id=message.client_id
        )
    
    def get_user_session(self, client_id: str) -> Optional[dict]:
        """获取用户会话信息"""
        return self.user_sessions.get(client_id)
    
    def cleanup_user_session(self, client_id: str):
        """清理用户会话"""
        if client_id in self.user_sessions:
            del self.user_sessions[client_id]
            logger.info(f"🧹 已清理客户端 {client_id} 的会话数据")