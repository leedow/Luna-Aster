# Luna-Aster 故障排除指南

本指南帮助您诊断和解决 Luna-Aster 应用中的常见问题。

## 📋 目录

- [快速诊断](#快速诊断)
- [安装问题](#安装问题)
- [连接问题](#连接问题)
- [音频问题](#音频问题)
- [AI服务问题](#ai服务问题)
- [性能问题](#性能问题)
- [浏览器兼容性](#浏览器兼容性)
- [日志分析](#日志分析)
- [高级调试](#高级调试)

## 🔍 快速诊断

### 系统健康检查

运行以下命令进行快速诊断：

```bash
# 检查后端服务状态
curl http://localhost:8000/health

# 检查前端是否正常运行
curl http://localhost:5173

# 检查 WebSocket 连接
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:8000/ws
```

### 常见状态码

| 状态码 | 含义 | 解决方案 |
|--------|------|----------|
| 200 | 正常 | 服务运行正常 |
| 404 | 未找到 | 检查URL路径和服务是否启动 |
| 500 | 服务器错误 | 查看后端日志 |
| 502 | 网关错误 | 检查后端服务是否运行 |
| 503 | 服务不可用 | 检查服务配置和依赖 |

## 🛠️ 安装问题

### 问题1: Node.js 版本不兼容

**症状**:
```
error This project requires Node.js version 18.0.0 or higher
```

**解决方案**:
```bash
# 检查当前版本
node --version

# 使用 nvm 安装正确版本 (macOS/Linux)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Windows 用户下载最新版本
# 访问 https://nodejs.org/
```

### 问题2: Python 依赖安装失败

**症状**:
```
ERROR: Failed building wheel for pyaudio
```

**解决方案**:

#### Windows
```bash
# 方法1: 使用预编译包
pip install pipwin
pipwin install pyaudio

# 方法2: 安装 Visual Studio Build Tools
# 下载并安装 Microsoft C++ Build Tools
# 然后重新安装
pip install pyaudio

# 方法3: 使用 conda
conda install pyaudio
```

#### macOS
```bash
# 安装 Homebrew 依赖
brew install portaudio
export LDFLAGS="-L$(brew --prefix portaudio)/lib"
export CPPFLAGS="-I$(brew --prefix portaudio)/include"
pip install pyaudio
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

### 问题3: 权限错误

**症状**:
```
PermissionError: [Errno 13] Permission denied
```

**解决方案**:
```bash
# 使用用户安装
pip install --user -r requirements.txt

# 或使用虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### 问题4: 网络连接问题

**症状**:
```
ReadTimeoutError: HTTPSConnectionPool
```

**解决方案**:
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
npm install --registry=https://registry.npmmirror.com

# 配置代理
pip install --proxy http://proxy.company.com:8080 -r requirements.txt
npm config set proxy http://proxy.company.com:8080
```

## 🔌 连接问题

### 问题1: WebSocket 连接失败

**症状**:
- 前端显示 "连接失败"
- 控制台错误: `WebSocket connection to 'ws://localhost:8000/ws' failed`

**诊断步骤**:
```bash
# 1. 检查后端是否运行
curl http://localhost:8000/health

# 2. 检查端口是否被占用
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# 3. 测试 WebSocket 连接
wscat -c ws://localhost:8000/ws
```

**解决方案**:
```bash
# 1. 重启后端服务
cd backend
python main.py

# 2. 检查防火墙设置
# Windows: 允许应用通过防火墙
# macOS: 系统偏好设置 > 安全性与隐私 > 防火墙
# Linux: sudo ufw allow 8000

# 3. 更改端口（如果被占用）
# 在 .env 文件中修改 PORT=8001
```

### 问题2: CORS 错误

**症状**:
```
Access to XMLHttpRequest at 'http://localhost:8000' from origin 'http://localhost:5173' has been blocked by CORS policy
```

**解决方案**:
```python
# 在 backend/main.py 中检查 CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题3: 连接频繁断开

**症状**:
- WebSocket 连接不稳定
- 频繁重连

**解决方案**:
```typescript
// 在前端调整重连策略
const wsConfig: WebSocketConfig = {
  url: 'ws://localhost:8000/ws',
  reconnectInterval: 3000,    // 增加重连间隔
  maxReconnectAttempts: 10,   // 增加重连次数
  heartbeatInterval: 30000,   // 增加心跳间隔
  connectionTimeout: 10000,   // 增加连接超时
};
```

## 🎵 音频问题

### 问题1: 麦克风权限被拒绝

**症状**:
```
DOMException: Permission denied
```

**解决方案**:
1. **Chrome**: 点击地址栏左侧的锁图标 → 允许麦克风
2. **Firefox**: 点击地址栏左侧的盾牌图标 → 允许麦克风
3. **Safari**: Safari → 偏好设置 → 网站 → 麦克风 → 允许
4. **Edge**: 点击地址栏右侧的锁图标 → 麦克风权限

### 问题2: 音频录制失败

**症状**:
- 无法开始录音
- 录音数据为空

**诊断步骤**:
```javascript
// 在浏览器控制台中测试
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(stream => {
    console.log('音频设备可用:', stream);
    stream.getTracks().forEach(track => track.stop());
  })
  .catch(err => console.error('音频设备错误:', err));
```

**解决方案**:
```javascript
// 检查音频设备
navigator.mediaDevices.enumerateDevices()
  .then(devices => {
    const audioInputs = devices.filter(device => device.kind === 'audioinput');
    console.log('可用音频输入设备:', audioInputs);
  });

// 使用特定设备
const constraints = {
  audio: {
    deviceId: 'specific-device-id',
    sampleRate: 16000,
    channelCount: 1
  }
};
```

### 问题3: 音频播放失败

**症状**:
- TTS 音频无法播放
- 音频格式错误

**解决方案**:
```typescript
// 检查音频支持
const audio = new Audio();
console.log('支持的音频格式:');
console.log('MP3:', audio.canPlayType('audio/mpeg'));
console.log('WAV:', audio.canPlayType('audio/wav'));
console.log('OGG:', audio.canPlayType('audio/ogg'));

// 使用 AudioContext
const audioContext = new (window.AudioContext || window.webkitAudioContext)();
if (audioContext.state === 'suspended') {
  audioContext.resume();
}
```

### 问题4: 音频质量差

**症状**:
- 录音音质模糊
- 识别准确率低

**解决方案**:
```env
# 调整音频配置
AUDIO_SAMPLE_RATE=44100  # 提高采样率
AUDIO_CHANNELS=1         # 使用单声道
AUDIO_FORMAT=wav         # 使用无损格式

# Whisper 配置优化
WHISPER_MODEL=whisper-1
WHISPER_LANGUAGE=zh      # 指定语言
WHISPER_TEMPERATURE=0    # 降低随机性
```

## 🤖 AI服务问题

### 问题1: OpenAI API 错误

**症状**:
```
openai.error.AuthenticationError: Incorrect API key provided
```

**解决方案**:
```bash
# 1. 检查 API 密钥格式
echo $OPENAI_API_KEY  # 应以 sk- 开头

# 2. 测试 API 密钥
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# 3. 检查配额
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### 问题2: API 请求超时

**症状**:
```
ReadTimeout: The read operation timed out
```

**解决方案**:
```env
# 增加超时时间
OPENAI_TIMEOUT=60
ANTHROPIC_TIMEOUT=60

# 减少请求大小
OPENAI_MAX_TOKENS=500
ANTHROPIC_MAX_TOKENS=500
```

### 问题3: 语音识别准确率低

**症状**:
- 识别结果不准确
- 无法识别中文

**解决方案**:
```env
# Whisper 优化配置
WHISPER_MODEL=whisper-1
WHISPER_LANGUAGE=zh
WHISPER_TEMPERATURE=0
WHISPER_PROMPT="以下是中文对话"

# SpeechRecognition 优化
SPEECH_RECOGNITION_LANGUAGE=zh-CN
SPEECH_RECOGNITION_TIMEOUT=10.0
SPEECH_RECOGNITION_PHRASE_TIMEOUT=2.0
```

### 问题4: TTS 语音不自然

**症状**:
- 合成语音机械化
- 发音不准确

**解决方案**:
```env
# Edge-TTS 优化
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural  # 使用更自然的声音
EDGE_TTS_RATE=+10%                   # 调整语速
EDGE_TTS_PITCH=+5Hz                  # 调整音调

# 或使用其他声音
EDGE_TTS_VOICE=zh-CN-YunxiNeural     # 男声
EDGE_TTS_VOICE=zh-CN-XiaoyiNeural    # 女声
```

## ⚡ 性能问题

### 问题1: 响应速度慢

**症状**:
- AI 回复延迟高
- 音频处理缓慢

**诊断工具**:
```bash
# 检查系统资源
top                    # Linux/macOS
taskmgr               # Windows

# 检查网络延迟
ping api.openai.com
ping api.anthropic.com

# 检查磁盘IO
iostat -x 1           # Linux
```

**解决方案**:
```env
# 优化配置
WORKERS=4                    # 增加工作进程
OPENAI_MAX_TOKENS=300       # 减少生成长度
AUDIO_MAX_DURATION=15       # 限制音频长度

# 启用缓存
ENABLE_CACHE=true
CACHE_TTL=3600
```

### 问题2: 内存使用过高

**症状**:
- 系统内存不足
- 应用崩溃

**解决方案**:
```python
# 在 backend/main.py 中添加内存限制
import resource

# 限制内存使用（单位：字节）
resource.setrlimit(resource.RLIMIT_AS, (1024*1024*1024, -1))  # 1GB

# 定期清理
import gc
gc.collect()
```

### 问题3: CPU 使用率高

**症状**:
- CPU 占用率持续高于 80%
- 系统响应缓慢

**解决方案**:
```env
# 减少并发处理
MAX_CONCURRENT_REQUESTS=5
AUDIO_PROCESSING_THREADS=2

# 优化音频处理
AUDIO_SAMPLE_RATE=16000    # 降低采样率
AUDIO_CHUNK_SIZE=1024      # 调整块大小
```

## 🌐 浏览器兼容性

### 支持的浏览器版本

| 浏览器 | 最低版本 | 推荐版本 | 注意事项 |
|--------|----------|----------|----------|
| Chrome | 88+ | 最新版 | 最佳兼容性 |
| Firefox | 85+ | 最新版 | 需启用音频权限 |
| Safari | 14+ | 最新版 | 部分 WebRTC 限制 |
| Edge | 88+ | 最新版 | 基于 Chromium |

### 常见兼容性问题

#### Safari 音频问题
```javascript
// Safari 需要用户交互才能播放音频
document.addEventListener('click', () => {
  const audioContext = new AudioContext();
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }
}, { once: true });
```

#### Firefox WebSocket 问题
```javascript
// Firefox 可能需要特殊的 WebSocket 配置
const ws = new WebSocket('ws://localhost:8000/ws', [], {
  perMessageDeflate: false
});
```

#### 移动端适配
```css
/* 移动端样式调整 */
@media (max-width: 768px) {
  .chat-interface {
    font-size: 14px;
    padding: 10px;
  }
  
  .control-panel {
    flex-direction: column;
  }
}
```

## 📊 日志分析

### 启用详细日志

```env
# 在 .env 文件中启用调试日志
LOG_LEVEL=DEBUG
LOG_FILE=logs/luna_aster.log
ENABLE_REQUEST_LOGGING=true
```

### 常见日志错误

#### 连接错误
```
ERROR: WebSocket connection failed: Connection refused
```
**解决**: 检查后端服务是否运行

#### 认证错误
```
ERROR: OpenAI API authentication failed
```
**解决**: 检查 API 密钥是否正确

#### 音频错误
```
ERROR: Audio device not found
```
**解决**: 检查音频设备和权限

### 日志分析工具

```bash
# 实时查看日志
tail -f logs/luna_aster.log

# 搜索错误
grep "ERROR" logs/luna_aster.log

# 统计错误类型
grep "ERROR" logs/luna_aster.log | cut -d':' -f3 | sort | uniq -c
```

## 🔧 高级调试

### 网络调试

```bash
# 使用 tcpdump 监控网络流量
sudo tcpdump -i any port 8000

# 使用 Wireshark 分析 WebSocket 流量
# 过滤器: tcp.port == 8000 and websocket
```

### 性能分析

```python
# 在代码中添加性能监控
import time
import functools

def timing_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} took {end - start:.2f} seconds")
        return result
    return wrapper

@timing_decorator
def process_audio(audio_data):
    # 音频处理逻辑
    pass
```

### 内存分析

```python
# 使用 memory_profiler 分析内存使用
pip install memory-profiler

# 在代码中添加
from memory_profiler import profile

@profile
def memory_intensive_function():
    # 内存密集型操作
    pass
```

### 数据库调试

```python
# 启用 SQLAlchemy 日志
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## 🆘 获取帮助

如果以上解决方案都无法解决您的问题：

### 1. 收集诊断信息

```bash
# 创建诊断报告
echo "=== 系统信息 ===" > diagnosis.txt
uname -a >> diagnosis.txt
echo "=== Python 版本 ===" >> diagnosis.txt
python --version >> diagnosis.txt
echo "=== Node.js 版本 ===" >> diagnosis.txt
node --version >> diagnosis.txt
echo "=== 服务状态 ===" >> diagnosis.txt
curl -s http://localhost:8000/health >> diagnosis.txt
echo "=== 错误日志 ===" >> diagnosis.txt
tail -50 logs/luna_aster.log >> diagnosis.txt
```

### 2. 提交 Issue

访问 [GitHub Issues](https://github.com/your-username/Luna-Aster/issues) 并包含：

- 问题描述
- 重现步骤
- 期望行为
- 实际行为
- 环境信息
- 错误日志
- 诊断报告

### 3. 社区支持

- [Discord 社区](https://discord.gg/your-invite)
- [GitHub Discussions](https://github.com/your-username/Luna-Aster/discussions)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/luna-aster)

### 4. 专业支持

如需专业技术支持，请联系：
- 邮箱: support@luna-aster.com
- 企业支持: enterprise@luna-aster.com

---

希望这个故障排除指南能帮助您快速解决问题！🔧✨