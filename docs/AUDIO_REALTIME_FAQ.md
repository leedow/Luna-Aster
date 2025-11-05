# 音频实时采集与传输 FAQ

面向本项目的音频实时链路（前端采集、WebSocket 传输、后端 ASR）常见问题与实践建议，结合现有代码结构进行说明。

## 目录

1. 为什么 `audio-worklet-processor.js` 放在 `public/` 而不是 `src/`？
2. MediaRecorder 是否支持实时监听？适配与局限
3. 项目中拿到的是 PCM 吗？什么是 PCM？
4. 服务端如何通过 WebSocket 接收音频，并进行 ASR 处理？
5. 常见坑与建议

---

## 1. 为什么放在 `public/` 而不是 `src/`

- 运行时按 URL 加载：`AudioWorklet` 通过 `audioContext.audioWorklet.addModule('<url>')` 动态加载脚本，不走 React/TS 的静态 `import`。放在 `public/` 可保证其始终按 URL 直接访问（如 `'/audio-worklet-processor.js'`）。
- 独立执行环境：Worklet 运行在独立上下文，没有 `window`、DOM、React，也不能依赖应用 bundle。若被打包器改写/注入包装代码，可能破坏 `registerProcessor(...)` 的环境假设。
- 构建与路径稳定性：`public/` 资源路径稳定（通常不哈希、不树摇），生产/开发环境一致，避免 `addModule()` 因重命名/路径变化而 404。
- 安全与同源：Worklet 需同源且安全上下文（HTTPS 或 `localhost`）。`public/` 静态资源最容易满足。

可选做法（放在 `src/`）：需确保打包后可用 URL，并保持纯 JS、自包含。

```ts
// 推荐在子路径部署时用 BASE_URL，避免根路径差异：
await audioContext.audioWorklet.addModule(
  import.meta.env.BASE_URL + 'audio-worklet-processor.js'
);
```

关联代码：
- `frontend/public/audio-worklet-processor.js`
- `frontend/src/utils/audioWorkletRecorder.ts`: `audioContext.audioWorklet.addModule('/audio-worklet-processor.js')`

---

## 2. MediaRecorder 是否支持实时监听

- 片段级实时：`MediaRecorder.start(timeslice)` 可周期触发 `ondataavailable`，实时拿到编码后的 Blob（常见 `webm/opus`、`ogg`）。适合“边录边发”，但延迟和片段间隔在不同浏览器下不稳定。
- 不适合低延迟原始处理：无法直接获得原始 PCM（需解码），编码容器与后端期望不一致会增加延迟与复杂性。
- 本项目需求偏向“低延迟、格式可控（WAV@16kHz/mono）”，因此默认优先使用 `AudioWorklet`。

示例（若坚持使用）：

```ts
const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
mr.ondataavailable = e => websocket.send(e.data); // 服务端需能解码 webm/opus
mr.start(200); // 200ms 分片，视延迟与稳定性调整
```

关联代码：
- `frontend/src/utils/audioUtils.ts`: 自动选择优先使用 `AudioWorklet`

---

## 3. 项目中拿到的是 PCM 吗？什么是 PCM

- 当前实现：实时监听模式下，`audio-worklet-processor.js` 将重采样后的音频以小块 `WAV` 封装（负载为 `PCM16 LE`），通过 `postMessage({ type: 'realtime-audio-chunk', audioData })` 传回主线程。
- 也就是说，前后端拿到的是“小型 WAV 文件”的 `ArrayBuffer`，其音频负载是线性 PCM（16 位、`little-endian`、单声道、默认 16kHz）。

什么是 PCM：
- 脉冲编码调制（Pulse Code Modulation），未压缩的音频表示，每个样本是瞬时幅度的数值。
- 关键参数：采样率（如 `16000Hz`）、位深（如 `16-bit`）、通道（mono/stereo）、端序（WAV 常用小端）。
- `WAV` 是容器格式，常见负载就是 PCM。因此“WAV@16kHz/mono/16-bit”本质上是“PCM16 小块 + WAV 头”。

若后端需要“裸 PCM”而非 WAV：
- 直接跳过前 44 字节的 WAV 头；后续数据为连续的 `Int16 LE` 样本。
- 或修改 Worklet，将 `convertToWAV` 替换为输出裸 `Int16Array`/`ArrayBuffer`。

关联代码：
- `frontend/public/audio-worklet-processor.js`: `convertToWAV` 写 WAV 头并 `Int16` 量化
- `frontend/src/utils/audioWorkletRecorder.ts`: `realtime-audio-chunk` 回调转发

---

## 4. 服务端如何通过 WebSocket 接收音频，并进行 ASR 处理

消息与流程：
- 前端连接后，先发 `START_LISTENING`；监听时持续发送 `AUDIO_DATA`（Base64 的小型 WAV）。协议示例见 `shared/protocols.md`。
- 后端 `backend/main.py` 的 `@app.websocket('/ws')` 接收消息，解析为 `Message` 并交给 `MessageHandler.handle_message`。
- `AUDIO_DATA` 处理：
  - `backend/services/message_handler.py::_handle_audio_data` 中：`base64.b64decode(message.data['audio_data'])` 得到字节；
  - 调用 `ASRService.transcribe_audio(audio_bytes)`。
- ASR 选择与实现：
  - `backend/core/asr/asr_service.py` 选择 provider（Whisper、SpeechRecognition 等），并汇总结果与耗时；
  - `backend/core/asr/providers/whisper_provider.py`：写临时 `.wav` 后调用 OpenAI Whisper API；
  - `backend/core/asr/providers/speech_recognition_provider.py`：写临时 `.wav` 并用 `speech_recognition` 识别；
  - `backend/core/asr/providers/base.py::validate_audio_format` 做基本 WAV 格式校验（长度 ≥ 44）。
- 后续：若识别到文本，构造 `CHAT` 消息交给 LLM 流，并返回响应给前端。

配置参考：
- `backend/config/settings.py::asr_config` 指定默认采样率、模型、语言等；与前端 `16kHz/mono` 保持一致更佳。

---

## 5. 常见坑与建议

- `addModule()` 路径错误：生产部署在子路径时用 `import.meta.env.BASE_URL` 生成 URL，避免 404。
- 非安全上下文：除 `localhost` 外务必用 HTTPS，否则部分浏览器拒绝加载 Worklet。
- 容器/编解码不匹配：`MediaRecorder` 产物通常为压缩容器（webm/ogg/opus）；后端若期望 `WAV/PCM` 会增加解码复杂度与延迟。
- 采样率/通道不一致：前后端参数不一致会影响识别质量；本项目默认 `16kHz/mono/16-bit`，建议保持一致。
- 分片策略：当前为“小型 WAV 片段逐块识别”；如需更低延迟/更高质量，需在后端累计分片或使用支持流式识别的 provider/API。

---

## 关联文件速览

- 前端
  - `frontend/public/audio-worklet-processor.js`：Worklet 采集、重采样、WAV 封装与分片传输。
  - `frontend/src/utils/audioWorkletRecorder.ts`：加载 Worklet、桥接消息与回调、开始/停止监听。
  - `frontend/src/utils/audioUtils.ts`：统一录音器（优先 `AudioWorklet`），设置实时回调与监听状态。
  - `frontend/src/contexts/WebSocketContext.tsx` 与 `frontend/src/utils/websocketUtils.ts`：WebSocket 管理、`AUDIO_DATA` 发送与状态控制。
- 后端
  - `backend/main.py`：WebSocket 端点、消息接收循环。
  - `backend/services/message_handler.py`：消息分发，`AUDIO_DATA` 解码与调用 ASR 服务。
  - `backend/core/asr/*`：ASR 服务总线与 provider 实现（Whisper、SpeechRecognition）。
  - `shared/protocols.md`：消息协议定义（`START_LISTENING`、`AUDIO_DATA`、`SPEECH_RECOGNITION` 等）。