# Backend ASR 处理调用流程

本文档详细描述了后端项目通过 WebSocket 接收音频数据进行 ASR（自动语音识别）处理的完整调用链路。

## 📋 目录

- [概述](#概述)
- [调用链路](#调用链路)
- [详细方法说明](#详细方法说明)
- [完整调用流程图](#完整调用流程图)
- [关键设计点](#关键设计点)

## 概述

当客户端通过 WebSocket 发送音频数据时，后端系统会经过以下层次进行处理：

1. **WebSocket 接收层** - 接收和解析客户端消息
2. **消息处理层** - 根据消息类型分发到对应处理器
3. **ASR 服务层** - 管理 ASR 提供商和选择最佳服务
4. **ASR 提供商层** - 执行具体的语音识别推理

## 调用链路

### 1. WebSocket 接收层

#### 1.1 WebSocket 端点
- **文件**: `backend/main.py`
- **类**: `FastAPI` (FastAPI 框架)
- **方法**: `@app.websocket("/ws")` → `websocket_endpoint()`
- **行号**: `main.py:93-164`
- **功能**: 
  - 接收 WebSocket 连接请求
  - 接收客户端发送的文本消息（JSON 格式）
  - 解析消息并创建 `Message` 对象
  - 调用消息处理器处理消息
  - 将处理结果发送回客户端

#### 1.2 WebSocket 管理器
- **文件**: `backend/services/websocket_manager.py`
- **类**: `WebSocketManager`
- **方法**: `connect(websocket: WebSocket)`
- **行号**: `websocket_manager.py:23-42`
- **功能**: 
  - 接受 WebSocket 连接
  - 生成唯一的 `client_id`
  - 管理活跃连接列表
  - 存储连接元数据

---

### 2. 消息处理层

#### 2.1 消息处理器入口
- **文件**: `backend/services/message_handler.py`
- **类**: `MessageHandler`
- **方法**: `handle_message(message: Message)`
- **行号**: `message_handler.py:35-69`
- **功能**: 
  - 根据消息类型（`MessageType`）分发到对应的处理器
  - 处理异常和错误情况
  - 统计消息总数

#### 2.2 音频数据处理
- **文件**: `backend/services/message_handler.py`
- **类**: `MessageHandler`
- **方法**: `_handle_audio_data(message: Message)`
- **行号**: `message_handler.py:180-214`
- **功能**: 
  - 从消息的 `data` 字段中提取 `audio_data`（base64 编码）
  - 使用 `base64.b64decode()` 解码音频数据
  - 提取语言参数和 `is_final` 标志
  - 调用 `ASRService.transcribe_audio()` 进行转录
  - 处理识别结果（当前版本会转换为聊天消息调用 LLM）

---

### 3. ASR 服务层

#### 3.1 ASR 服务初始化（启动时执行）
- **文件**: `backend/core/asr/asr_service.py`
- **类**: `ASRService`
- **方法**: `__init__(settings: Settings)`
- **行号**: `asr_service.py:20-30`
- **功能**: 
  - 初始化 ASR 服务配置
  - 创建临时目录用于存储音频文件
  - 调用 `_initialize_providers()` 初始化提供商

#### 3.2 初始化提供商（启动时执行）
- **文件**: `backend/core/asr/asr_service.py`
- **类**: `ASRService`
- **方法**: `_initialize_providers()`
- **行号**: `asr_service.py:32-39`
- **功能**: 
  - 从配置中获取 ASR 配置
  - 调用 `ASRProviderFactory.create_providers_from_config()` 创建提供商实例
  - 记录已初始化的提供商列表

#### 3.3 提供商工厂（启动时执行）
- **文件**: `backend/core/asr/providers/factory.py`
- **类**: `ASRProviderFactory`
- **方法**: `create_providers_from_config(config: Dict[str, Any])`
- **行号**: `factory.py:65-102`
- **功能**: 
  - 根据配置创建多个 ASR 提供商实例
  - 支持的提供商：`whisper`、`speech_recognition`、`sensevoice`、`mock`
  - 返回提供商字典

#### 3.4 创建提供商实例（启动时执行）
- **文件**: `backend/core/asr/providers/factory.py`
- **类**: `ASRProviderFactory`
- **方法**: `create_provider(provider_type: str, config: Dict[str, Any])`
- **行号**: `factory.py:40-62`
- **功能**: 
  - 根据提供商类型创建对应的提供商实例
  - 例如：创建 `SenseVoiceSmallProvider` 实例
  - 返回提供商对象或 `None`（如果创建失败）

#### 3.5 转录音频（运行时执行）
- **文件**: `backend/core/asr/asr_service.py`
- **类**: `ASRService`
- **方法**: `transcribe_audio(audio_data: bytes, **kwargs)`
- **行号**: `asr_service.py:63-93`
- **功能**: 
  - 验证音频数据是否为空
  - 调用 `select_best_provider()` 选择最佳可用的提供商
  - 调用提供商的 `transcribe_audio()` 方法执行转录
  - 添加处理时间、服务信息等元数据
  - 返回识别结果字典

#### 3.6 选择最佳提供商（运行时执行）
- **文件**: `backend/core/asr/asr_service.py`
- **类**: `ASRService`
- **方法**: `select_best_provider()`
- **行号**: `asr_service.py:41-61`
- **功能**: 
  - 按优先级顺序选择可用的 ASR 提供商
  - 优先级：`sensevoice` > `whisper` > `speech_recognition` > `mock`
  - 调用每个提供商的 `is_available()` 检查可用性
  - 返回第一个可用的提供商

---

### 4. ASR 提供商层（以 SenseVoice 为例）

#### 4.1 提供商初始化（启动时执行）
- **文件**: `backend/core/asr/providers/sensevoice_provider.py`
- **类**: `SenseVoiceSmallProvider`
- **方法**: `__init__(config: Dict[str, Any])`
- **行号**: `sensevoice_provider.py:20-35`
- **功能**: 
  - 初始化模型配置（模型名称、设备、hub 等）
  - 初始化 VAD（语音活动检测）配置
  - 设置 `self._model = None`（延迟加载）
  - 初始化会话字典 `self._sessions`

#### 4.2 检查可用性（运行时执行）
- **文件**: `backend/core/asr/providers/sensevoice_provider.py`
- **类**: `SenseVoiceSmallProvider`
- **方法**: `is_available()`
- **行号**: `sensevoice_provider.py:37-44`
- **功能**: 
  - 尝试导入 `funasr` 库
  - 返回 `True` 如果库可用，否则返回 `False`

#### 4.3 转录音频（运行时执行）
- **文件**: `backend/core/asr/providers/sensevoice_provider.py`
- **类**: `SenseVoiceSmallProvider`
- **方法**: `transcribe_audio(audio_data: bytes, **kwargs)`
- **行号**: `sensevoice_provider.py:93-146`
- **功能**: 
  - 解析参数（`client_id`、`language`、`is_final`）
  - 调用 `_ensure_model()` 确保模型已加载
  - 调用 `_get_session()` 获取或创建会话上下文
  - 将音频数据累积到会话的 `buffer` 中
  - 调用 `_model.generate()` 执行推理
  - 解析识别结果并返回

#### 4.4 确保模型已加载（运行时执行，首次调用时）
- **文件**: `backend/core/asr/providers/sensevoice_provider.py`
- **类**: `SenseVoiceSmallProvider`
- **方法**: `_ensure_model()`
- **行号**: `sensevoice_provider.py:46-74`
- **功能**: 
  - 检查 `self._model` 是否为 `None`
  - 如果为 `None`，则加载模型：
    - 导入 `funasr.AutoModel`
    - 构建配置参数（模型、设备、hub、VAD 等）
    - 创建 `AutoModel` 实例（模型加载到 GPU）
    - 保存到 `self._model`
  - 如果已加载，直接返回

#### 4.5 获取会话上下文（运行时执行）
- **文件**: `backend/core/asr/providers/sensevoice_provider.py`
- **类**: `SenseVoiceSmallProvider`
- **方法**: `_get_session(client_id: Optional[str])`
- **行号**: `sensevoice_provider.py:76-85`
- **功能**: 
  - 根据 `client_id` 获取或创建会话
  - 每个会话包含：
    - `buffer`: 累积的音频字节数据
    - `cache`: 传递给模型的缓存对象（用于增量识别）
    - `last_text`: 上次识别的文本
  - 返回会话字典

#### 4.6 模型推理（运行时执行）
- **文件**: `backend/core/asr/providers/sensevoice_provider.py`
- **类**: `AutoModel` (FunASR 库)
- **方法**: `generate(input, cache, language, use_itn)`
- **行号**: `sensevoice_provider.py:114-119`
- **功能**: 
  - 使用 FunASR 的 `AutoModel.generate()` 方法
  - 输入：累积的音频字节数据
  - 使用会话缓存进行增量识别
  - 返回识别结果（文本）

---

### 5. 返回结果链路

#### 5.1 结果逐层返回
- **路径**: `SenseVoiceSmallProvider` → `ASRService` → `MessageHandler`
- **方法**: 
  - `transcribe_audio()` → `transcribe_audio()` → `_handle_audio_data()`
- **功能**: 识别结果逐层返回，每层添加相应的元数据

#### 5.2 发送响应
- **文件**: `backend/services/websocket_manager.py`
- **类**: `WebSocketManager`
- **方法**: `send_personal_message(message: dict, websocket: WebSocket)`
- **行号**: `websocket_manager.py:62-69`
- **功能**: 
  - 将识别结果转换为 JSON 字符串
  - 通过 WebSocket 发送给客户端

---

## 完整调用流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                    客户端发送音频数据 (WebSocket)                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [1] main.py::websocket_endpoint()                               │
│     ├─ WebSocket.receive_text() 接收消息                        │
│     ├─ json.loads() 解析 JSON                                    │
│     └─ Message(**message_data) 创建消息对象                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [2] MessageHandler::handle_message()                            │
│     ├─ 根据消息类型分发                                          │
│     └─ _handle_audio_data() 处理音频数据                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [3] MessageHandler::_handle_audio_data()                       │
│     ├─ base64.b64decode() 解码音频数据                          │
│     ├─ 提取 language、is_final 参数                             │
│     └─ ASRService.transcribe_audio() 调用 ASR 服务             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [4] ASRService::transcribe_audio()                              │
│     ├─ 验证音频数据                                              │
│     ├─ select_best_provider() 选择提供商                         │
│     └─ provider.transcribe_audio() 调用提供商                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [5] ASRService::select_best_provider()                          │
│     ├─ 遍历优先级列表 (sensevoice > whisper > ...)              │
│     ├─ provider.is_available() 检查可用性                       │
│     └─ 返回可用的提供商                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [6] SenseVoiceSmallProvider::transcribe_audio()                 │
│     ├─ _ensure_model() 确保模型已加载（首次调用）                 │
│     ├─ _get_session() 获取会话上下文                             │
│     ├─ session["buffer"].extend() 累积音频数据                  │
│     └─ _model.generate() 执行推理                              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [7] SenseVoiceSmallProvider::_ensure_model()                     │
│     ├─ 检查 self._model 是否为 None                            │
│     └─ AutoModel(**kwargs) 加载模型到 GPU（首次）               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [8] SenseVoiceSmallProvider::_get_session()                      │
│     ├─ 检查会话是否存在                                          │
│     └─ 创建或返回会话（包含 buffer 和 cache）                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [9] AutoModel::generate() (FunASR 库)                           │
│     ├─ 使用累积的音频数据                                        │
│     ├─ 使用会话缓存进行增量识别                                   │
│     └─ 返回识别结果（文本）                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [10] 结果逐层返回                                                │
│      SenseVoiceSmallProvider → ASRService → MessageHandler      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ [11] WebSocketManager::send_personal_message()                  │
│      └─ websocket.send_text() 发送结果给客户端                   │
└─────────────────────────────────────────────────────────────────┘
```

## 关键设计点

### 1. 模型加载机制

- **延迟加载（Lazy Loading）**: 模型在初始化时不加载，避免启动时阻塞
- **单次加载**: 模型在首次使用时加载，之后常驻 GPU 显存
- **设备配置**: 根据 `device="cuda"` 配置，模型加载到 GPU 上

```python
# 延迟加载实现
self._model = None  # 初始化时

def _ensure_model(self):
    if self._model is not None:
        return  # 已加载，直接返回
    # 首次调用时加载模型
    self._model = AutoModel(**kwargs)
```

### 2. 会话管理

- **客户端隔离**: 每个客户端维护独立的会话上下文
- **流式处理**: 音频数据累积在 `buffer` 中，支持增量识别
- **缓存复用**: 使用 `cache` 对象实现增量识别，提高效率

```python
# 会话结构
session = {
    "buffer": bytearray(),  # 累积的音频数据
    "cache": {},            # 模型缓存
    "last_text": ""         # 上次识别结果
}
```

### 3. 提供商选择策略

- **优先级顺序**: `sensevoice` > `whisper` > `speech_recognition` > `mock`
- **可用性检查**: 每个提供商必须通过 `is_available()` 检查
- **动态选择**: 运行时根据可用性动态选择最佳提供商

### 4. 流式识别处理

- **数据累积**: 每次收到的音频块都会累积到会话的 `buffer` 中
- **增量识别**: 每次调用都对累积的音频进行识别
- **实时反馈**: 前端可以实时显示识别结果

### 5. 错误处理

- **多层异常捕获**: 每层都有异常处理机制
- **错误消息返回**: 错误信息通过 WebSocket 返回给客户端
- **日志记录**: 所有关键操作都有日志记录

## 相关文档

- [前端音频传输流程](FRONTEND_AUDIO_FLOW.md) - 前端录音到 WebSocket 发送的完整流程
- [API 文档](API.md) - WebSocket 接口详细说明
- [通信协议](../shared/protocols.md) - 前后端通信协议定义

---

**最后更新**: 2024年12月  
**版本**: 1.0.0

