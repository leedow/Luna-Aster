# 前端录音到 Socket 传输流程

本文档整理前端从麦克风录音到通过 WebSocket 发送到服务端的端到端流程，以及涉及的核心文件与关键函数，便于开发调试与扩展。

## 适用范围
- 前端：React + TypeScript（`frontend/`）
- 实时音频：AudioWorklet（首选）/ MediaRecorder（回退）
- 传输协议：WebSocket（`ws://localhost:8000/ws`）

## 涉及文件
- `frontend/src/components/ControlPanel/ControlPanel.tsx`
  - UI 入口；启动/停止持续监听；接收实时音频块并发往服务端。
- `frontend/src/contexts/WebSocketContext.tsx`
  - React Context 封装 WebSocket 管理与发送 API（含语音控制状态）。
- `frontend/src/utils/websocketUtils.ts`
  - `WebSocketManager` 实现连接、重连、心跳与消息发送（含 `sendAudioData`）。
- `frontend/src/types/message.ts`
  - 消息类型与工厂（`MessageType.AUDIO_DATA`、`createMessage.audioData`）。
- `frontend/src/utils/audioUtils.ts`
  - `AudioRecorder` 上层封装：选择 AudioWorklet/MediaRecorder；提供持续监听与实时音频块回调。
- `frontend/src/utils/audioWorkletRecorder.ts`
  - `AudioWorkletRecorder`：初始化 `AudioContext`/`AudioWorklet`；桥接 Worklet 消息到主线程回调。
- `frontend/public/audio-worklet-processor.js`
  - `AudioWorkletProcessor`：重采样、分块、封装 WAV，并通过 `port.postMessage` 回传实时音频块。
- `frontend/src/App.tsx`、`frontend/src/index.tsx`
  - 在应用根部挂载 `WebSocketProvider`，提供全局 WebSocket 能力。

## 端到端流程
- 入口（用户操作）
  - `ControlPanel.tsx` 调用 `audioRecorder.startListening()` 启动“持续监听”。
  - 同步发送控制消息：`setListening(true)` → `MessageType.START_LISTENING`，通知后端语音状态。

- 麦克风采集与 Worklet 初始化
  - `AudioRecorder.startListening()` 优先使用 `AudioWorklet`，内部调用 `AudioWorkletRecorder.startListening()`。
  - `AudioWorkletRecorder.initializeAudioWorklet()`：
    - 创建 `AudioContext`（采样率 16k）。
    - 加载模块：`audioContext.audioWorklet.addModule('/audio-worklet-processor.js')`。
    - 建立 `MediaStreamAudioSourceNode` → `AudioWorkletNode` 连接；监听 `audioWorkletNode.port.onmessage`。

- 实时处理与分块
  - `audio-worklet-processor.js/process()`：
    - 从输入通道读取并重采样到 `16000 Hz`（单声道）。
    - 累积到 `realtimeBuffer`，达到 `chunkSize`（默认 1024）时：
      - 将该块封装为 `wav`（`ArrayBuffer`）。
      - 发送 `postMessage({ type: 'realtime-audio-chunk', audioData, timestamp, chunkSize })` 到主线程。

- 主线程接收与业务回调
  - `AudioWorkletRecorder.handleWorkletMessage()` 捕获 `realtime-audio-chunk`，触发上层注册的 `onRealtimeAudioChunk`。
  - `AudioRecorder.setRealtimeAudioChunkCallback()` 将 Worklet 回调上抛给业务层。

- Base64 编码与 WebSocket 发送
  - `ControlPanel.tsx` 将 `ArrayBuffer` → Base64（`arrayBufferToBase64`），随后调用：
    - `sendRealtimeAudioChunk(base64Data, 'wav', 16000, 1)`。
  - `WebSocketContext.tsx` 转发到 `websocketManager.sendAudioData(...)`。

- WebSocket 打包与传输
  - `websocketUtils.ts` 的 `WebSocketManager.sendAudioData(...)`：
    - 使用 `types/message.ts` 的 `createMessage.audioData(...)` 构造 `MessageType.AUDIO_DATA`。
    - 通过 `ws.send(JSON.stringify(messageWithClientId))` 发送到后端（默认 `ws://localhost:8000/ws`）。

## 关键函数与职责
- 录音侧
  - `AudioRecorder.startListening()`：启动持续监听；优先选用 AudioWorklet。
  - `AudioWorkletRecorder.initializeAudioWorklet()`：加载 Worklet 脚本与节点绑定。
  - `audio-worklet-processor.js/process()`：重采样、分块、封装 WAV、`postMessage` 回传。
  - `AudioWorkletRecorder.handleWorkletMessage()`：分发 `realtime-audio-chunk` 到上层回调。
  - `AudioRecorder.setRealtimeAudioChunkCallback()`：上层接收实时音频块。

- 发送侧
  - `ControlPanel.arrayBufferToBase64()`：将 `ArrayBuffer` 转 Base64。
  - `WebSocketContext.sendRealtimeAudioChunk()`：统一封装参数并转发给 Manager。
  - `WebSocketManager.sendAudioData()`：构建并发送 `MessageType.AUDIO_DATA`。

## 消息结构（AUDIO_DATA）
- 类型：`MessageType.AUDIO_DATA`
- 字段（参考 `frontend/src/types/message.ts`）：
```json
{
  "type": "AUDIO_DATA",
  "timestamp": "ISO-8601",
  "client_id": "<client-id>",
  "data": {
    "audio_data": "<base64>",
    "format": "wav",
    "sample_rate": 16000,
    "channels": 1
  }
}
```

## 默认参数与约定
- 采样率：`16000 Hz`
- 通道：`1`（单声道）
- 格式：`wav`（小块实时传输）
- 分块大小：`chunkSize = 1024`
- WebSocket 端点：`ws://localhost:8000/ws`

## 常见注意事项
- 浏览器权限：`getUserMedia` 需麦克风授权；HTTPS 环境或本地开发。
- Worklet 路径：确保 `addModule('/audio-worklet-processor.js')` 能正确访问 `public/` 下脚本。
- 连接状态：仅在 `WebSocket CONNECTED` 时发送；通过 `WebSocketContext.isConnected` 判断。
- 数据大小：Base64 较原始二进制更大；分块发送避免一次性过大消息。
- 回退策略：不支持 AudioWorklet 时，录音功能会回退到 MediaRecorder（整段录音），实时 ASR 场景以 AudioWorklet 为主。

## 关联文档
- `docs/API.md`：WebSocket 消息协议与类型说明
- `shared/protocols.md`：前后端通信协议定义
- `docs/DEVELOPMENT.md`：项目结构与前端开发指南

