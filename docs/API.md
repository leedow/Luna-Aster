# Luna-Aster API 文档

本文档详细描述了 Luna-Aster 后端服务的 API 接口和 WebSocket 通信协议。

## 📋 目录

- [REST API 接口](#rest-api-接口)
- [WebSocket 协议](#websocket-协议)
- [消息类型](#消息类型)
- [错误处理](#错误处理)
- [认证和安全](#认证和安全)
- [示例代码](#示例代码)

## 🌐 REST API 接口

### 基础信息

- **基础URL**: `http://localhost:8000`
- **API版本**: `v1.0.0`
- **内容类型**: `application/json`

### 端点列表

#### 1. 根端点

```http
GET /
```

**描述**: 获取服务器基本信息

**响应示例**:
```json
{
  "name": "Luna-Aster Backend",
  "version": "1.0.0",
  "status": "running",
  "endpoints": {
    "websocket": "/ws",
    "health": "/health",
    "stats": "/stats"
  }
}
```

#### 2. 健康检查

```http
GET /health
```

**描述**: 检查服务器和各个服务的健康状态

**响应示例**:
```json
{
  "status": "healthy",
  "timestamp": 1701234567.89,
  "services": {
    "llm": {
      "status": "healthy",
      "provider": "openai",
      "available_providers": ["openai", "anthropic", "mock"]
    },
    "asr": {
      "status": "healthy",
      "provider": "whisper",
      "available_providers": ["whisper", "speech_recognition", "mock"]
    },
    "tts": {
      "status": "healthy",
      "provider": "edge_tts",
      "available_providers": ["edge_tts", "gtts", "pyttsx3", "mock"]
    },
    "websocket": {
      "status": "healthy",
      "active_connections": 5
    }
  }
}
```

#### 3. 服务器统计

```http
GET /stats
```

**描述**: 获取服务器运行统计信息

**响应示例**:
```json
{
  "timestamp": 1701234567.89,
  "websocket": {
    "active_connections": 5,
    "total_connections": 127,
    "messages_sent": 1543,
    "messages_received": 1398,
    "uptime": 86400.5
  },
  "services": {
    "llm": {
      "status": "available",
      "requests_processed": 234,
      "average_response_time": 1.2
    },
    "asr": {
      "status": "available",
      "audio_processed": 89,
      "average_processing_time": 0.8
    },
    "tts": {
      "status": "available",
      "text_synthesized": 156,
      "average_synthesis_time": 0.6
    }
  }
}
```

## 🔌 WebSocket 协议

### 连接信息

- **WebSocket URL**: `ws://localhost:8000/ws`
- **协议**: WebSocket (RFC 6455)
- **子协议**: 无
- **心跳间隔**: 30秒

### 连接流程

1. **建立连接**: 客户端连接到 WebSocket 端点
2. **服务器确认**: 服务器发送连接确认消息
3. **消息交换**: 双向消息通信
4. **心跳维持**: 定期发送心跳消息
5. **连接关闭**: 正常或异常断开连接

### 消息格式

所有 WebSocket 消息都使用 JSON 格式：

```json
{
  "type": "message_type",
  "content": "message_content",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "unique-client-id",
  "data": {
    "additional": "data"
  }
}
```

#### 字段说明

| 字段 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `type` | string | ✅ | 消息类型，见[消息类型](#消息类型) |
| `content` | string | ❌ | 消息内容，根据类型而定 |
| `timestamp` | string | ✅ | ISO 8601 格式的时间戳 |
| `client_id` | string | ✅ | 客户端唯一标识符 |
| `data` | object | ❌ | 附加数据，根据消息类型而定 |

## 📨 消息类型

### 1. 连接管理

#### CONNECTION_ESTABLISHED
**方向**: 服务器 → 客户端  
**描述**: 连接建立确认

```json
{
  "type": "CONNECTION_ESTABLISHED",
  "content": "Connection established successfully",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123",
  "data": {
    "server_info": {
      "name": "Luna-Aster Backend",
      "version": "1.0.0"
    }
  }
}
```

#### HEARTBEAT
**方向**: 双向  
**描述**: 心跳消息，维持连接

```json
{
  "type": "HEARTBEAT",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123"
}
```

### 2. 聊天消息

#### CHAT
**方向**: 客户端 → 服务器  
**描述**: 用户发送的聊天消息

```json
{
  "type": "CHAT",
  "content": "你好，Luna！",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123"
}
```

#### LLM_RESPONSE
**方向**: 服务器 → 客户端  
**描述**: LLM 生成的回复

```json
{
  "type": "LLM_RESPONSE",
  "content": "你好！我是Luna，很高兴见到你！",
  "timestamp": "2023-12-01T10:00:01Z",
  "client_id": "client-123",
  "data": {
    "provider": "openai",
    "model": "gpt-3.5-turbo",
    "tokens_used": 25,
    "response_time": 1.2
  }
}
```

### 3. 语音识别 (ASR)

#### START_LISTENING
**方向**: 客户端 → 服务器  
**描述**: 开始语音识别

```json
{
  "type": "START_LISTENING",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123",
  "data": {
    "audio_config": {
      "sample_rate": 16000,
      "channels": 1,
      "format": "wav"
    }
  }
}
```

#### STOP_LISTENING
**方向**: 客户端 → 服务器  
**描述**: 停止语音识别

```json
{
  "type": "STOP_LISTENING",
  "timestamp": "2023-12-01T10:00:05Z",
  "client_id": "client-123"
}
```

#### AUDIO_DATA
**方向**: 客户端 → 服务器  
**描述**: 音频数据传输

```json
{
  "type": "AUDIO_DATA",
  "timestamp": "2023-12-01T10:00:01Z",
  "client_id": "client-123",
  "data": {
    "audio_data": "base64_encoded_audio_data",
    "sequence": 1,
    "is_final": false
  }
}
```

#### SPEECH_RECOGNITION
**方向**: 服务器 → 客户端  
**描述**: 语音识别结果

```json
{
  "type": "SPEECH_RECOGNITION",
  "content": "你好Luna",
  "timestamp": "2023-12-01T10:00:06Z",
  "client_id": "client-123",
  "data": {
    "provider": "whisper",
    "confidence": 0.95,
    "language": "zh",
    "processing_time": 0.8
  }
}
```

### 4. 语音合成 (TTS)

#### START_SPEAKING
**方向**: 服务器 → 客户端  
**描述**: 开始语音播放

```json
{
  "type": "START_SPEAKING",
  "content": "开始播放语音",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123"
}
```

#### STOP_SPEAKING
**方向**: 双向  
**描述**: 停止语音播放

```json
{
  "type": "STOP_SPEAKING",
  "timestamp": "2023-12-01T10:00:05Z",
  "client_id": "client-123"
}
```

#### AUDIO_GENERATED
**方向**: 服务器 → 客户端  
**描述**: 生成的音频数据

```json
{
  "type": "AUDIO_GENERATED",
  "timestamp": "2023-12-01T10:00:01Z",
  "client_id": "client-123",
  "data": {
    "audio_data": "base64_encoded_audio_data",
    "provider": "edge_tts",
    "voice": "zh-CN-XiaoxiaoNeural",
    "format": "wav",
    "duration": 3.5
  }
}
```

### 5. 状态更新

#### STATUS_UPDATE
**方向**: 服务器 → 客户端  
**描述**: 系统状态更新

```json
{
  "type": "STATUS_UPDATE",
  "content": "ASR服务已启动",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123",
  "data": {
    "service": "asr",
    "status": "active",
    "details": {
      "provider": "whisper",
      "listening": true
    }
  }
}
```

### 6. 系统消息

#### SYSTEM
**方向**: 服务器 → 客户端  
**描述**: 系统通知消息

```json
{
  "type": "SYSTEM",
  "content": "系统维护将在5分钟后开始",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123",
  "data": {
    "level": "warning",
    "category": "maintenance"
  }
}
```

### 7. 错误消息

#### ERROR
**方向**: 服务器 → 客户端  
**描述**: 错误信息

```json
{
  "type": "ERROR",
  "content": "语音识别服务暂时不可用",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123",
  "data": {
    "error_code": "ASR_SERVICE_UNAVAILABLE",
    "details": "Whisper API rate limit exceeded",
    "retry_after": 60
  }
}
```

## ❌ 错误处理

### 错误代码

| 错误代码 | 描述 | HTTP状态码 |
|----------|------|------------|
| `INVALID_MESSAGE_FORMAT` | 消息格式无效 | 400 |
| `INVALID_CLIENT_ID` | 客户端ID无效 | 400 |
| `MESSAGE_TOO_LONG` | 消息内容过长 | 400 |
| `RATE_LIMIT_EXCEEDED` | 请求频率超限 | 429 |
| `LLM_SERVICE_UNAVAILABLE` | LLM服务不可用 | 503 |
| `ASR_SERVICE_UNAVAILABLE` | ASR服务不可用 | 503 |
| `TTS_SERVICE_UNAVAILABLE` | TTS服务不可用 | 503 |
| `AUDIO_FORMAT_UNSUPPORTED` | 音频格式不支持 | 400 |
| `INTERNAL_SERVER_ERROR` | 内部服务器错误 | 500 |

### 错误响应格式

```json
{
  "type": "ERROR",
  "content": "错误描述",
  "timestamp": "2023-12-01T10:00:00Z",
  "client_id": "client-123",
  "data": {
    "error_code": "ERROR_CODE",
    "details": "详细错误信息",
    "retry_after": 60,
    "suggestions": [
      "检查网络连接",
      "稍后重试"
    ]
  }
}
```

## 🔐 认证和安全

### 当前版本

当前版本暂未实现身份认证，所有连接都被接受。

### 安全措施

1. **消息验证**: 所有消息都经过格式和内容验证
2. **速率限制**: 每个客户端有请求频率限制
3. **内容过滤**: 检测和过滤恶意内容
4. **连接限制**: 限制最大并发连接数
5. **超时处理**: 自动断开长时间无活动的连接

### 未来计划

- JWT 令牌认证
- API 密钥认证
- OAuth 2.0 集成
- 用户权限管理

## 💻 示例代码

### JavaScript/TypeScript 客户端

```typescript
class LunaAsterClient {
  private ws: WebSocket | null = null;
  private clientId: string = '';

  connect(url: string = 'ws://localhost:8000/ws'): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(url);
      
      this.ws.onopen = () => {
        console.log('Connected to Luna-Aster server');
        resolve();
      };
      
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      this.ws.onclose = () => {
        console.log('Disconnected from server');
      };
    });
  }

  sendMessage(type: string, content?: string, data?: any): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }

    const message = {
      type,
      content,
      timestamp: new Date().toISOString(),
      client_id: this.clientId,
      data
    };

    this.ws.send(JSON.stringify(message));
  }

  sendChat(content: string): void {
    this.sendMessage('CHAT', content);
  }

  startListening(): void {
    this.sendMessage('START_LISTENING', undefined, {
      audio_config: {
        sample_rate: 16000,
        channels: 1,
        format: 'wav'
      }
    });
  }

  stopListening(): void {
    this.sendMessage('STOP_LISTENING');
  }

  private handleMessage(message: any): void {
    switch (message.type) {
      case 'CONNECTION_ESTABLISHED':
        this.clientId = message.client_id;
        console.log('Client ID:', this.clientId);
        break;
      
      case 'LLM_RESPONSE':
        console.log('Luna says:', message.content);
        break;
      
      case 'SPEECH_RECOGNITION':
        console.log('You said:', message.content);
        break;
      
      case 'ERROR':
        console.error('Error:', message.content, message.data);
        break;
      
      default:
        console.log('Received message:', message);
    }
  }
}

// 使用示例
const client = new LunaAsterClient();
client.connect().then(() => {
  client.sendChat('你好，Luna！');
});
```

### Python 客户端

```python
import asyncio
import json
import websockets
from datetime import datetime
from typing import Optional, Dict, Any

class LunaAsterClient:
    def __init__(self):
        self.ws = None
        self.client_id = ""

    async def connect(self, url: str = "ws://localhost:8000/ws"):
        """连接到 Luna-Aster 服务器"""
        self.ws = await websockets.connect(url)
        print("Connected to Luna-Aster server")
        
        # 启动消息监听
        asyncio.create_task(self.listen_messages())

    async def send_message(self, msg_type: str, content: Optional[str] = None, data: Optional[Dict[str, Any]] = None):
        """发送消息到服务器"""
        if not self.ws:
            raise Exception("WebSocket is not connected")

        message = {
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "client_id": self.client_id,
            "data": data or {}
        }

        await self.ws.send(json.dumps(message))

    async def send_chat(self, content: str):
        """发送聊天消息"""
        await self.send_message("CHAT", content)

    async def start_listening(self):
        """开始语音识别"""
        await self.send_message("START_LISTENING", data={
            "audio_config": {
                "sample_rate": 16000,
                "channels": 1,
                "format": "wav"
            }
        })

    async def stop_listening(self):
        """停止语音识别"""
        await self.send_message("STOP_LISTENING")

    async def listen_messages(self):
        """监听服务器消息"""
        async for message in self.ws:
            data = json.loads(message)
            await self.handle_message(data)

    async def handle_message(self, message: Dict[str, Any]):
        """处理接收到的消息"""
        msg_type = message.get("type")
        
        if msg_type == "CONNECTION_ESTABLISHED":
            self.client_id = message.get("client_id", "")
            print(f"Client ID: {self.client_id}")
        
        elif msg_type == "LLM_RESPONSE":
            print(f"Luna says: {message.get('content')}")
        
        elif msg_type == "SPEECH_RECOGNITION":
            print(f"You said: {message.get('content')}")
        
        elif msg_type == "ERROR":
            print(f"Error: {message.get('content')}")
            print(f"Details: {message.get('data')}")
        
        else:
            print(f"Received message: {message}")

# 使用示例
async def main():
    client = LunaAsterClient()
    await client.connect()
    
    # 发送聊天消息
    await client.send_chat("你好，Luna！")
    
    # 保持连接
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 更多资源

- [WebSocket 协议详细说明](../shared/protocols.md)
- [前端集成指南](./FRONTEND_INTEGRATION.md)
- [服务配置指南](./SERVICE_CONFIGURATION.md)
- [故障排除指南](./TROUBLESHOOTING.md)

---

如有任何问题或建议，请在 [GitHub Issues](https://github.com/your-username/Luna-Aster/issues) 中提出。