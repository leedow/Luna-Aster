# 流水线模式重构说明

## 概述

参考标准的异步流水线模式，重构了 `message_handler.py` 的消息处理流程，使其更加清晰、简洁和高效。

## 核心改进

### 1. 流水线结构

**重构前：**
- 使用多个独立的 Task 分别管理每个 Worker
- 需要逐个取消和等待任务
- 代码结构相对复杂

**重构后：**
```python
# 创建三个队列连接四个阶段
q1 = asyncio.Queue()  # Audio -> ASR
q2 = asyncio.Queue()  # ASR -> LLM  
q3 = asyncio.Queue()  # LLM -> TTS

# 使用 asyncio.gather 并行启动所有 Worker
pipeline_task = asyncio.create_task(
    asyncio.gather(
        self._asr_worker(client_id, q1, q2),
        self._llm_worker(client_id, q2, q3),
        self._tts_worker(client_id, q3),
        return_exceptions=True
    )
)
```

### 2. Worker 函数简化

**统一的 Worker 模式：**

```python
async def _xxx_worker(self, client_id: str, queue_in: asyncio.Queue, queue_out: asyncio.Queue):
    """Worker: 从 queue_in 获取数据 -> 处理 -> 放入 queue_out"""
    try:
        while True:
            # 获取输入数据
            item = await queue_in.get()
            
            # None 作为结束信号
            if item is None:
                await queue_out.put(None)  # 传递结束信号
                break
            
            # 处理数据
            result = await self.service.process(item)
            
            # 发送结果到前端
            await self._send_result(client_id, result)
            
            # 传递给下一阶段
            await queue_out.put(result)
            
    finally:
        logger.info(f"Worker 已停止")
```

### 3. 消息发送逻辑封装

将重复的 WebSocket 消息发送逻辑封装为独立方法：

- `_send_asr_result()` - 发送 ASR 识别结果
- `_send_llm_result()` - 发送 LLM 回复
- `_send_tts_result()` - 发送 TTS 音频
- `_send_error()` - 发送错误消息

### 4. 流水线生命周期管理

**启动流水线：**
```python
await self._create_pipeline(client_id)
# 自动创建队列和启动所有 Worker
```

**停止流水线：**
```python
await self._destroy_pipeline(client_id)
# 发送 None 信号 -> 等待流水线完成 -> 清理资源
```

## 流水线工作流程

```
┌─────────┐
│ 音频数据 │
└────┬────┘
     │
     ▼
┌─────────────────────────────────┐
│  Audio Queue (q1)               │
└────┬────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  ASR Worker                     │
│  - 识别音频                      │
│  - 发送识别结果到前端             │
│  - 传递文本到下一阶段             │
└────┬────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  Text Queue (q2)                │
└────┬────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  LLM Worker                     │
│  - 生成回复                      │
│  - 发送回复到前端                 │
│  - 传递回复到下一阶段             │
└────┬────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  Reply Queue (q3)               │
└────┬────────────────────────────┘
     │
     ▼
┌─────────────────────────────────┐
│  TTS Worker                     │
│  - 合成语音                      │
│  - 发送音频到前端                 │
└─────────────────────────────────┘
```

## 优势

1. **代码更简洁**：Worker 函数专注于核心逻辑，辅助功能提取到独立方法
2. **结构更清晰**：使用统一的 `queue_in` -> `process` -> `queue_out` 模式
3. **易于维护**：所有 Worker 遵循相同的模式，便于理解和修改
4. **优雅终止**：使用 `None` 信号在流水线中传递，确保所有阶段正确关闭
5. **并行高效**：使用 `asyncio.gather` 并发运行所有 Worker，充分利用异步特性

## 参考代码

重构基于以下流水线模式示例：

```python
async def main():
    q1, q2, q3 = asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
    
    await asyncio.gather(
        vad(q1),           # 阶段1：VAD -> q1
        asr(q1, q2),       # 阶段2：q1 -> ASR -> q2
        llm(q2, q3),       # 阶段3：q2 -> LLM -> q3
        tts(q3)            # 阶段4：q3 -> TTS
    )
```

## 使用示例

```python
# 创建消息处理器
handler = MessageHandler(llm_service, asr_service, tts_service)
handler.set_websocket_manager(ws_manager)

# 启动流水线
await handler._create_pipeline(client_id)

# 发送音频数据到流水线
await handler.pipelines[client_id]["audio_queue"].put({
    "audio_data": audio_bytes,
    "language": "zh",
    "is_final": False
})

# 停止流水线
await handler._destroy_pipeline(client_id)
```

## 注意事项

1. **结束信号**：必须使用 `None` 作为结束信号，确保流水线正确终止
2. **异常处理**：每个 Worker 内部处理异常，避免影响流水线其他阶段
3. **超时控制**：销毁流水线时设置 5 秒超时，避免无限等待
4. **资源清理**：流水线停止时自动清理所有队列和任务

## 测试建议

1. 测试正常流程：音频 -> 识别 -> 生成 -> 合成
2. 测试中断场景：在各个阶段中断，确保流水线正确停止
3. 测试并发场景：多个客户端同时使用流水线
4. 测试错误处理：模拟各个阶段的错误，确保不影响其他客户端

