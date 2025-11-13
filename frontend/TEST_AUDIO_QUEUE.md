# 音频队列播放功能测试说明

## 功能概述
实现了前端音频队列自动播放功能，当后端通过WebSocket发送`AUDIO_GENERATED`消息时，前端会自动将音频加入播放队列并按顺序播放。

## 实现的功能

### 1. 音频队列播放器 (`audioQueuePlayer.ts`)
- ✅ 自动队列管理：音频自动加入队列
- ✅ 顺序播放：按FIFO顺序播放音频
- ✅ 状态管理：IDLE、PLAYING、PAUSED、STOPPED
- ✅ 回调支持：播放开始、结束、队列更新、错误处理

### 2. WebSocket上下文增强 (`WebSocketContext.tsx`)
- ✅ 监听`AUDIO_GENERATED`消息
- ✅ 自动将音频数据加入播放队列
- ✅ 提供队列状态信息（队列长度、当前播放项、播放状态）
- ✅ 提供控制方法（停止、跳过、清空队列）
- ✅ 与`isSpeaking`状态同步

### 3. 状态栏显示更新 (`StatusBar.tsx`)
- ✅ 显示音频队列长度
- ✅ 显示当前播放的音频文本
- ✅ 队列状态指示器

## 使用方式

### 后端发送音频
后端通过WebSocket发送如下格式的消息：
```json
{
  "type": "audio_generated",
  "client_id": "xxx",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    "audio_data": "base64编码的音频数据",
    "format": "mp3",
    "text": "要播放的文本内容",
    "voice": "zh-CN-XiaoxiaoNeural"
  }
}
```

### 前端自动处理
1. WebSocketContext接收消息
2. 解析音频数据
3. 加入播放队列
4. 自动开始播放（如果当前空闲）
5. 播放完成后自动播放下一条

### 在组件中使用
```tsx
import { useWebSocket } from '../../contexts/WebSocketContext';

const MyComponent = () => {
  const { 
    audioQueueLength,      // 队列长度
    currentAudioItem,      // 当前播放项
    audioPlayerState,      // 播放状态
    stopAudioPlayback,     // 停止播放
    skipCurrentAudio,      // 跳过当前
    clearAudioQueue        // 清空队列
  } = useWebSocket();
  
  return (
    <div>
      <p>队列: {audioQueueLength}</p>
      <p>状态: {audioPlayerState}</p>
      {currentAudioItem && <p>播放: {currentAudioItem.text}</p>}
      <button onClick={stopAudioPlayback}>停止</button>
      <button onClick={skipCurrentAudio}>跳过</button>
      <button onClick={clearAudioQueue}>清空</button>
    </div>
  );
};
```

## 测试步骤

### 1. 启动前后端
```bash
# 终端1: 启动后端
cd backend
python main.py

# 终端2: 启动前端
cd frontend
npm run dev
```

### 2. 测试单条音频
1. 在聊天界面发送消息
2. 等待LLM回复
3. 后端自动合成语音并发送
4. 前端自动播放音频
5. 观察状态栏的队列显示

### 3. 测试多条音频队列
1. 快速连续发送多条消息
2. 观察队列长度增加
3. 观察音频按顺序播放
4. 每条播放完成后自动播放下一条

### 4. 测试控制功能
- 播放过程中点击"停止"按钮
- 播放过程中点击"跳过"按钮
- 清空队列功能

## 日志输出

### 正常播放流程
```
📥 收到音频数据: 你好，我是Luna... (格式: mp3)
🎵 音频已加入队列 [1]: 你好，我是Luna...
🔊 开始播放音频 [1]: 你好，我是Luna...
🔊 开始播放: 你好，我是Luna...
🔊 开始播放音频
✅ 音频播放完成
✅ 播放完成: 你好，我是Luna...
🎵 音频队列播放完成
```

## 注意事项

1. **音频格式支持**：确保浏览器支持后端发送的音频格式（mp3/wav）
2. **Base64编码**：音频必须是有效的Base64编码
3. **队列清理**：断开连接时会自动停止播放并清空队列
4. **状态同步**：播放状态会自动更新`isSpeaking`状态

## 已知问题

无

## 后续优化建议

1. 添加音频预加载机制
2. 支持播放进度显示
3. 支持音量控制
4. 支持播放速度调节
5. 添加播放历史记录
