"""
WebSocket 连接管理器
负责管理客户端连接、消息广播等
"""

import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import WebSocket
from loguru import logger

def json_serializer(obj):
    """JSON序列化辅助函数，处理datetime等特殊对象"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 存储活跃连接
        self.active_connections: List[WebSocket] = []
        # 客户端ID映射
        self.client_connections: Dict[str, WebSocket] = {}
        # 连接元数据
        self.connection_metadata: Dict[str, Dict] = {}
    
    async def connect(self, websocket: WebSocket) -> str:
        """接受新的WebSocket连接"""
        await websocket.accept()
        
        # 生成唯一的客户端ID
        client_id = str(uuid.uuid4())
        
        # 添加到连接列表
        self.active_connections.append(websocket)
        self.client_connections[client_id] = websocket
        
        # 存储连接元数据
        self.connection_metadata[client_id] = {
            "connected_at": None,
            "last_activity": None,
            "message_count": 0
        }
        
        logger.info(f"✅ 客户端 {client_id} 连接成功，当前连接数: {len(self.active_connections)}")
        return client_id
    
    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 从客户端映射中移除
        client_id = None
        for cid, ws in self.client_connections.items():
            if ws == websocket:
                client_id = cid
                break
        
        if client_id:
            del self.client_connections[client_id]
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]
            logger.info(f"❌ 客户端 {client_id} 断开连接，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """发送个人消息"""
        try:
            json_str = json.dumps(message, ensure_ascii=False, default=json_serializer)
            await websocket.send_text(json_str)
            logger.debug(f"✅ 消息已发送: {message.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f"❌ 发送个人消息失败: {str(e)}")
            # 如果发送失败，可能连接已断开，移除该连接
            self.disconnect(websocket)
    
    async def send_message_to_client(self, client_id: str, message: dict):
        """发送消息给指定客户端"""
        if client_id in self.client_connections:
            websocket = self.client_connections[client_id]
            await self.send_personal_message(message, websocket)
        else:
            logger.warning(f"⚠️ 客户端 {client_id} 不存在或已断开连接")
    
    async def send_message(self, client_id: str, message):
        """发送消息对象给指定客户端（支持Message对象）"""
        if client_id in self.client_connections:
            websocket = self.client_connections[client_id]
            # 如果是Pydantic模型或Message对象，转换为字典
            if hasattr(message, 'model_dump'):
                # Pydantic v2
                message_dict = message.model_dump(exclude_none=True)
            elif hasattr(message, 'dict'):
                # Pydantic v1
                message_dict = message.dict(exclude_none=True)
            elif hasattr(message, 'to_dict'):
                # 自定义 to_dict 方法
                message_dict = message.to_dict()
            else:
                # 已经是字典
                message_dict = message
            await self.send_personal_message(message_dict, websocket)
        else:
            logger.warning(f"⚠️ 客户端 {client_id} 不存在或已断开连接")
    
    async def broadcast(self, message: dict, exclude_client: Optional[str] = None):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            logger.warning("⚠️ 没有活跃连接，无法广播消息")
            return
        
        # 需要移除的无效连接
        invalid_connections = []
        
        for client_id, websocket in self.client_connections.items():
            # 跳过排除的客户端
            if exclude_client and client_id == exclude_client:
                continue
            
            try:
                json_str = json.dumps(message, ensure_ascii=False, default=json_serializer)
                await websocket.send_text(json_str)
            except Exception as e:
                logger.error(f"❌ 广播消息给客户端 {client_id} 失败: {str(e)}")
                invalid_connections.append(websocket)
        
        # 清理无效连接
        for websocket in invalid_connections:
            self.disconnect(websocket)
        
        logger.info(f"📢 消息已广播给 {len(self.active_connections)} 个客户端")
    
    async def disconnect_all(self):
        """断开所有连接"""
        logger.info("🔌 正在断开所有WebSocket连接...")
        
        for websocket in self.active_connections.copy():
            try:
                await websocket.close()
            except Exception as e:
                logger.error(f"❌ 关闭连接时出错: {str(e)}")
        
        self.active_connections.clear()
        self.client_connections.clear()
        self.connection_metadata.clear()
        
        logger.info("✅ 所有连接已断开")
    
    def get_client_id_by_websocket(self, websocket: WebSocket) -> Optional[str]:
        """根据WebSocket获取客户端ID"""
        for client_id, ws in self.client_connections.items():
            if ws == websocket:
                return client_id
        return None
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)
    
    def get_client_metadata(self, client_id: str) -> Optional[Dict]:
        """获取客户端元数据"""
        return self.connection_metadata.get(client_id)
    
    def update_client_activity(self, client_id: str):
        """更新客户端活动时间"""
        if client_id in self.connection_metadata:
            from datetime import datetime
            self.connection_metadata[client_id]["last_activity"] = datetime.now()
            self.connection_metadata[client_id]["message_count"] += 1
    
    def get_connection_stats(self) -> Dict:
        """获取连接统计信息"""
        return {
            "total_connections": len(self.active_connections),
            "client_ids": list(self.client_connections.keys()),
            "metadata": self.connection_metadata
        }
    
    async def ping_all_clients(self):
        """向所有客户端发送心跳"""
        ping_message = {
            "type": "heartbeat",
            "timestamp": None,
            "server_time": None
        }
        
        await self.broadcast(ping_message)
        logger.debug("💓 心跳消息已发送给所有客户端")
    
    async def send_system_notification(self, message: str, level: str = "info"):
        """发送系统通知给所有客户端"""
        notification = {
            "type": "system",
            "content": message,
            "level": level,
            "timestamp": None
        }
        
        await self.broadcast(notification)
        logger.info(f"📢 系统通知已发送: {message}")