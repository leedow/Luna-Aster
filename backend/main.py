"""
Luna-Aster 后端服务主入口
提供 WebSocket 服务，集成 LLM、ASR、TTS 功能
"""

import asyncio
import json
import logging
from typing import Dict, List
from datetime import datetime

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from core.llm.llm_service import LLMService
from core.asr.asr_service import ASRService
from core.tts.tts_service import TTSService
from core.vad.vad_service import VADService
from services.websocket_manager import WebSocketManager
from services.message_handler import MessageHandler
from config.settings import Settings
from models.message import Message, MessageType

# 初始化配置
settings = Settings()

# 创建 FastAPI 应用
app = FastAPI(
    title="Luna-Aster Backend",
    description="桌面虚拟角色后端服务",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务变量（延迟初始化）
websocket_manager: WebSocketManager = None
llm_service: LLMService = None
asr_service: ASRService = None
tts_service: TTSService = None
vad_service: VADService = None
message_handler: MessageHandler = None

def initialize_services():
    """初始化所有服务（只执行一次）"""
    global websocket_manager, llm_service, asr_service, tts_service, vad_service, message_handler
    
    # 如果已经初始化，直接返回
    if message_handler is not None:
        logger.debug("服务已初始化，跳过重复初始化")
        return
    
    logger.info("🚀 初始化服务...")
    websocket_manager = WebSocketManager()
    llm_service = LLMService(settings)
    asr_service = ASRService(settings)
    tts_service = TTSService(settings)
    vad_service = VADService(settings)
    message_handler = MessageHandler(llm_service, asr_service, tts_service, vad_service)
    message_handler.set_websocket_manager(websocket_manager)
    logger.info("✅ 所有服务初始化完成")

@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    logger.info("🚀 Luna-Aster 后端服务启动中...")
    
    # 初始化服务（确保只执行一次）
    initialize_services()
    
    logger.info("✅ 应用启动完成")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    logger.info("🛑 Luna-Aster 后端服务关闭中...")
    
    # 清理WebSocket连接
    if websocket_manager is not None:
        await websocket_manager.disconnect_all()
    
    logger.info("✅ 资源清理完成")

@app.get("/")
async def root():
    """根路径，返回服务状态"""
    # 确保服务已初始化
    if websocket_manager is None:
        initialize_services()
    
    return {
        "service": "Luna-Aster Backend",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "connected_clients": len(websocket_manager.active_connections) if websocket_manager else 0
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    # 确保服务已初始化
    if llm_service is None:
        initialize_services()
    
    return {
        "status": "healthy",
        "services": {
            "llm": await llm_service.health_check(),
            "asr": await asr_service.health_check(),
            "tts": await tts_service.health_check(),
            "vad": await vad_service.health_check()
        },
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接端点"""
    # 确保服务已初始化
    if websocket_manager is None:
        initialize_services()
    
    client_id = await websocket_manager.connect(websocket)
    logger.info(f"🔗 客户端 {client_id} 已连接")
    
    try:
        # 发送欢迎消息
        welcome_message = Message(
            type=MessageType.SYSTEM,
            content="欢迎使用 Luna-Aster！我是你的虚拟助手 Luna。",
            timestamp=datetime.now(),
            client_id=client_id
        )
        welcome_data = welcome_message.model_dump()
        welcome_data['timestamp'] = welcome_data['timestamp'].isoformat()
        await websocket_manager.send_personal_message(welcome_data, websocket)
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                # 确保设置正确的 client_id
                message_data['client_id'] = client_id
                message = Message(**message_data)
                
                logger.info(f"📨 收到来自 {client_id} 的消息: {message.type}")

                # 处理消息
                response = await message_handler.handle_message(message)
                
                # 发送响应
                if response:
                    response_data = response.model_dump()
                    # 手动转换 datetime 为 ISO 格式字符串
                    if 'timestamp' in response_data and response_data['timestamp']:
                        response_data['timestamp'] = response_data['timestamp'].isoformat()
                    await websocket_manager.send_personal_message(response_data, websocket)
                    
            except json.JSONDecodeError:
                logger.error(f"❌ 无法解析来自 {client_id} 的消息: {data}")
                error_message = Message(
                    type=MessageType.ERROR,
                    content="消息格式错误",
                    timestamp=datetime.now(),
                    client_id=client_id
                )
                error_data = error_message.model_dump()
                error_data['timestamp'] = error_data['timestamp'].isoformat()
                await websocket_manager.send_personal_message(error_data, websocket)
                
            except Exception as e:
                logger.error(f"❌ 处理消息时发生错误: {str(e)}")
                error_message = Message(
                    type=MessageType.ERROR,
                    content=f"处理消息时发生错误: {str(e)}",
                    timestamp=datetime.now(),
                    client_id=client_id
                )
                error_data = error_message.model_dump()
                error_data['timestamp'] = error_data['timestamp'].isoformat()
                await websocket_manager.send_personal_message(error_data, websocket)
                
    except WebSocketDisconnect:
        logger.info(f"🔌 客户端 {client_id} 已断开连接")
        websocket_manager.disconnect(websocket)
        # 清理用户会话和流水线
        await message_handler.cleanup_user_session(client_id)
        
    except Exception as e:
        logger.error(f"❌ WebSocket 连接错误: {str(e)}")
        websocket_manager.disconnect(websocket)
        # 清理用户会话和流水线
        await message_handler.cleanup_user_session(client_id)

@app.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    # 确保服务已初始化
    if websocket_manager is None:
        initialize_services()
    
    return {
        "connected_clients": len(websocket_manager.active_connections),
        "total_messages": message_handler.total_messages if message_handler else 0,
        "services_status": {
            "llm": await llm_service.health_check(),
            "asr": await asr_service.health_check(),
            "tts": await tts_service.health_check()
        },
        "uptime": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # 配置日志
    logger.add(
        "logs/luna_aster_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )