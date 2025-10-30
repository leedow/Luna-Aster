# Luna-Aster 前后端通信协议

## 概述

本文档定义了 Luna-Aster 桌面虚拟角色应用的前后端通信协议。前端使用 Electron + React，后端使用 Python WebSocket 服务。

## WebSocket 连接

### 连接地址
```
ws://localhost:8000/ws
```

### 连接流程
1. 前端发起 WebSocket 连接
2. 后端返回连接确认消息
3. 开始双向通信
4. 定期发送心跳消息保持连接

## 消息格式

所有消息都使用 JSON 格式，基本结构如下：

```json
{
  "type": "message_type",
  "content": "message_content",
  "timestamp": "2024-01-01T00:00:00Z",
  "client_id": "uuid",
  "data": {}
}
```

### 字段说明
- `type`: 消息类型（必需）
- `content`: 消息内容（可选）
- `timestamp`: 时间戳（自动生成）
- `client_id`: 客户端唯一标识（必需）
- `data`: 附加数据（可选）

## 消息类型

### 1. 连接管理

#### CONNECTION_ESTABLISHED
连接建立确认
```json
{
  "type": "CONNECTION_ESTABLISHED",
  "content": "连接已建立",
  "client_id": "uuid"
}
```

#### HEARTBEAT
心跳消息
```json
{
  "type": "HEARTBEAT",
  "content": "ping",
  "client_id": "uuid"
}
```

### 2. 聊天消息

#### CHAT
用户聊天消息
```json
{
  "type": "CHAT",
  "content": "用户输入的文本",
  "client_id": "uuid"
}
```

#### LLM_RESPONSE
LLM 回复消息
```json
{
  "type": "LLM_RESPONSE",
  "content": "LLM生成的回复",
  "client_id": "uuid",
  "data": {
    "model": "gpt-3.5-turbo",
    "tokens_used": 150,
    "processing_time": 1.2
  }
}
```

### 3. 语音识别 (ASR)

#### START_LISTENING
开始语音识别
```json
{
  "type": "START_LISTENING",
  "client_id": "uuid"
}
```

#### STOP_LISTENING
停止语音识别
```json
{
  "type": "STOP_LISTENING",
  "client_id": "uuid"
}
```

#### AUDIO_DATA
音频数据传输
```json
{
  "type": "AUDIO_DATA",
  "client_id": "uuid",
  "data": {
    "audio_data": "base64_encoded_audio",
    "format": "wav",
    "sample_rate": 16000,
    "channels": 1
  }
}
```

#### SPEECH_RECOGNITION
语音识别结果
```json
{
  "type": "SPEECH_RECOGNITION",
  "content": "识别出的文本",
  "client_id": "uuid",
  "data": {
    "confidence": 0.95,
    "language": "zh-CN",
    "provider": "whisper"
  }
}
```

### 4. 语音合成 (TTS)

#### START_SPEAKING
开始语音合成
```json
{
  "type": "START_SPEAKING",
  "content": "要合成的文本",
  "client_id": "uuid"
}
```

#### STOP_SPEAKING
停止语音合成
```json
{
  "type": "STOP_SPEAKING",
  "client_id": "uuid"
}
```

#### AUDIO_GENERATED
语音合成结果
```json
{
  "type": "AUDIO_GENERATED",
  "client_id": "uuid",
  "data": {
    "audio_data": "base64_encoded_audio",
    "format": "mp3",
    "voice": "zh-CN-XiaoxiaoNeural",
    "text": "原始文本",
    "duration": 3.5
  }
}
```

### 5. 状态更新

#### STATUS_UPDATE
服务状态更新
```json
{
  "type": "STATUS_UPDATE",
  "client_id": "uuid",
  "data": {
    "service": "asr|tts|llm",
    "status": "listening|speaking|processing|idle",
    "details": {}
  }
}
```

### 6. 系统消息

#### SYSTEM
系统消息
```json
{
  "type": "SYSTEM",
  "content": "系统消息内容",
  "client_id": "uuid",
  "data": {
    "level": "info|warning|error",
    "code": "MESSAGE_CODE"
  }
}
```

#### ERROR
错误消息
```json
{
  "type": "ERROR",
  "content": "错误描述",
  "client_id": "uuid",
  "data": {
    "error_code": "ERROR_CODE",
    "details": {}
  }
}
```

## 通信流程

### 1. 初始化连接
```
前端 -> 后端: WebSocket 连接请求
后端 -> 前端: CONNECTION_ESTABLISHED
前端 -> 后端: HEARTBEAT (定期)
后端 -> 前端: HEARTBEAT (响应)
```

### 2. 文本聊天
```
前端 -> 后端: CHAT
后端 -> 前端: STATUS_UPDATE (processing)
后端 -> 前端: LLM_RESPONSE
```

### 3. 语音对话
```
前端 -> 后端: START_LISTENING
后端 -> 前端: STATUS_UPDATE (listening)
前端 -> 后端: AUDIO_DATA (持续)
后端 -> 前端: SPEECH_RECOGNITION
后端 -> 前端: LLM_RESPONSE
前端 -> 后端: START_SPEAKING
后端 -> 前端: AUDIO_GENERATED
前端 -> 后端: STOP_LISTENING
```

## 错误处理

### 错误代码
- `INVALID_MESSAGE_FORMAT`: 消息格式无效
- `MISSING_CLIENT_ID`: 缺少客户端ID
- `RATE_LIMIT_EXCEEDED`: 超过速率限制
- `SERVICE_UNAVAILABLE`: 服务不可用
- `AUDIO_PROCESSING_ERROR`: 音频处理错误
- `LLM_ERROR`: LLM服务错误
- `ASR_ERROR`: 语音识别错误
- `TTS_ERROR`: 语音合成错误

### 错误响应示例
```json
{
  "type": "ERROR",
  "content": "服务暂时不可用",
  "client_id": "uuid",
  "data": {
    "error_code": "SERVICE_UNAVAILABLE",
    "details": {
      "service": "llm",
      "reason": "API配额已用完"
    }
  }
}
```

## 安全考虑

1. **输入验证**: 所有输入数据都需要验证
2. **速率限制**: 防止客户端发送过多请求
3. **数据清理**: 清理用户输入的恶意内容
4. **连接管理**: 限制并发连接数
5. **日志记录**: 记录所有重要操作

## 性能优化

1. **消息压缩**: 大型音频数据使用压缩
2. **批量处理**: 合并小的音频片段
3. **缓存机制**: 缓存常用的TTS结果
4. **连接池**: 复用数据库和API连接
5. **异步处理**: 使用异步I/O提高并发性能