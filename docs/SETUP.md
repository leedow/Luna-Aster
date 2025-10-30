# Luna-Aster 安装和配置指南

本指南将帮助您从零开始安装和配置 Luna-Aster 虚拟角色应用。

## 📋 目录

- [系统要求](#系统要求)
- [环境准备](#环境准备)
- [项目安装](#项目安装)
- [服务配置](#服务配置)
- [启动应用](#启动应用)
- [验证安装](#验证安装)
- [常见问题](#常见问题)
- [高级配置](#高级配置)

## 💻 系统要求

### 最低要求

- **操作系统**: Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- **内存**: 4GB RAM
- **存储**: 2GB 可用空间
- **网络**: 稳定的互联网连接（用于AI服务）

### 推荐配置

- **操作系统**: Windows 11, macOS 12+, Ubuntu 20.04+
- **内存**: 8GB+ RAM
- **存储**: 5GB+ 可用空间
- **处理器**: 多核处理器
- **音频**: 支持麦克风和扬声器

## 🛠️ 环境准备

### 1. 安装 Node.js

访问 [Node.js 官网](https://nodejs.org/) 下载并安装最新的 LTS 版本（18.0.0+）。

**验证安装**:
```bash
node --version  # 应显示 v18.0.0 或更高版本
npm --version   # 应显示 9.0.0 或更高版本
```

### 2. 安装 Python

访问 [Python 官网](https://www.python.org/) 下载并安装 Python 3.8 或更高版本。

**验证安装**:
```bash
python --version  # 应显示 Python 3.8.0 或更高版本
pip --version      # 确认 pip 已安装
```

**注意**: 在某些系统上，可能需要使用 `python3` 和 `pip3` 命令。

### 3. 安装 Git

访问 [Git 官网](https://git-scm.com/) 下载并安装 Git。

**验证安装**:
```bash
git --version  # 确认 Git 已安装
```

## 📦 项目安装

### 1. 克隆项目

```bash
git clone https://github.com/your-username/Luna-Aster.git
cd Luna-Aster
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
```

如果遇到网络问题，可以使用国内镜像：
```bash
npm install --registry=https://registry.npmmirror.com
```

### 3. 安装后端依赖

```bash
cd ../backend
pip install -r requirements.txt
```

如果遇到网络问题，可以使用国内镜像：
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 4. 处理可能的依赖问题

#### Windows 系统

如果在安装 `pyaudio` 时遇到问题：
```bash
# 方法1: 使用预编译包
pip install pipwin
pipwin install pyaudio

# 方法2: 下载 wheel 文件
# 访问 https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# 下载对应版本的 .whl 文件，然后安装
pip install PyAudio-0.2.11-cp39-cp39-win_amd64.whl
```

#### macOS 系统

```bash
# 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装音频依赖
brew install portaudio
pip install pyaudio
```

#### Ubuntu/Debian 系统

```bash
# 安装系统依赖
sudo apt update
sudo apt install python3-dev python3-pip portaudio19-dev

# 安装 Python 依赖
pip install pyaudio
```

## ⚙️ 服务配置

### 1. 创建环境配置文件

```bash
cd backend
cp .env.example .env
```

### 2. 编辑配置文件

使用文本编辑器打开 `.env` 文件，配置以下内容：

#### 基础配置

```env
# 服务器配置
HOST=localhost
PORT=8000
DEBUG=true

# 安全配置
SECRET_KEY=your-secret-key-here-change-in-production
```

#### LLM 服务配置

选择并配置至少一个 LLM 提供商：

**OpenAI 配置**:
```env
# OpenAI 配置
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7
```

**Anthropic 配置**:
```env
# Anthropic 配置
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-sonnet-20240229
ANTHROPIC_MAX_TOKENS=1000
```

**测试配置**（无需API密钥）:
```env
# 测试配置
LLM_PROVIDER=mock
```

#### ASR 服务配置

**Whisper 配置**（推荐）:
```env
ASR_PROVIDER=whisper
WHISPER_API_KEY=sk-your-openai-api-key-here
WHISPER_MODEL=whisper-1
WHISPER_LANGUAGE=zh
```

**SpeechRecognition 配置**（免费）:
```env
ASR_PROVIDER=speech_recognition
SPEECH_RECOGNITION_TIMEOUT=5.0
SPEECH_RECOGNITION_PHRASE_TIMEOUT=1.0
```

**测试配置**:
```env
ASR_PROVIDER=mock
```

#### TTS 服务配置

**Edge-TTS 配置**（推荐，免费）:
```env
TTS_PROVIDER=edge_tts
EDGE_TTS_VOICE=zh-CN-XiaoxiaoNeural
EDGE_TTS_RATE=+0%
EDGE_TTS_PITCH=+0Hz
```

**gTTS 配置**（免费）:
```env
TTS_PROVIDER=gtts
GTTS_LANGUAGE=zh
GTTS_SLOW=false
```

**pyttsx3 配置**（离线）:
```env
TTS_PROVIDER=pyttsx3
PYTTSX3_RATE=200
PYTTSX3_VOLUME=0.9
```

#### 虚拟角色配置

```env
CHARACTER_NAME=Luna
CHARACTER_PERSONALITY=友善、聪明、乐于助人的AI助手
CHARACTER_LANGUAGE=zh-CN
```

#### 音频配置

```env
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_FORMAT=wav
AUDIO_MAX_DURATION=30
```

### 3. 获取 API 密钥

#### OpenAI API 密钥

1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册或登录账户
3. 进入 [API Keys](https://platform.openai.com/api-keys) 页面
4. 点击 "Create new secret key"
5. 复制生成的密钥到 `.env` 文件

#### Anthropic API 密钥

1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 注册或登录账户
3. 进入 API Keys 页面
4. 创建新的 API 密钥
5. 复制密钥到 `.env` 文件

## 🚀 启动应用

### 1. 启动后端服务

```bash
cd backend
python main.py
```

成功启动后，您应该看到类似输出：
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

### 2. 启动前端应用

打开新的终端窗口：

```bash
cd frontend
npm run dev
```

成功启动后，您应该看到类似输出：
```
  VITE v4.5.0  ready in 1234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

### 3. 访问应用

在浏览器中访问 `http://localhost:5173`

## ✅ 验证安装

### 1. 检查后端服务

访问 `http://localhost:8000/health` 检查服务状态：

```json
{
  "status": "healthy",
  "services": {
    "llm": {"status": "healthy"},
    "asr": {"status": "healthy"},
    "tts": {"status": "healthy"},
    "websocket": {"status": "healthy"}
  }
}
```

### 2. 测试前端连接

1. 打开应用界面
2. 检查状态栏显示 "已连接"
3. 尝试发送测试消息
4. 验证是否收到回复

### 3. 测试语音功能

1. 点击 "开始录音" 按钮
2. 说话测试语音识别
3. 检查是否正确识别语音
4. 测试语音合成播放

## 🔧 常见问题

### 问题1: 端口被占用

**错误信息**: `Address already in use`

**解决方案**:
```bash
# 查找占用端口的进程
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # macOS/Linux

# 终止进程或更改端口
# 在 .env 文件中修改 PORT=8001
```

### 问题2: Python 依赖安装失败

**错误信息**: `Failed building wheel for pyaudio`

**解决方案**:
参考 [项目安装](#项目安装) 中的依赖问题处理部分。

### 问题3: API 密钥无效

**错误信息**: `Invalid API key`

**解决方案**:
1. 检查 `.env` 文件中的 API 密钥是否正确
2. 确认 API 密钥有足够的配额
3. 检查网络连接是否正常

### 问题4: 语音功能不工作

**可能原因**:
- 麦克风权限未授予
- 音频设备驱动问题
- 浏览器安全策略限制

**解决方案**:
1. 检查浏览器麦克风权限
2. 更新音频设备驱动
3. 使用 HTTPS 或 localhost 访问

### 问题5: WebSocket 连接失败

**错误信息**: `WebSocket connection failed`

**解决方案**:
1. 确认后端服务正在运行
2. 检查防火墙设置
3. 验证端口配置是否正确

## 🔧 高级配置

### 1. 生产环境部署

#### 后端部署

使用 Gunicorn 部署：
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

使用 Docker 部署：
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

#### 前端部署

构建生产版本：
```bash
cd frontend
npm run build
```

使用 Nginx 部署：
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 2. 性能优化

#### 后端优化

```env
# 增加工作进程数
WORKERS=4

# 启用连接池
DATABASE_POOL_SIZE=20

# 配置缓存
REDIS_URL=redis://localhost:6379

# 启用压缩
ENABLE_GZIP=true
```

#### 前端优化

```typescript
// 启用代码分割
const ChatInterface = lazy(() => import('./components/ChatInterface'));

// 使用 Web Workers 处理音频
const audioWorker = new Worker('/audio-worker.js');
```

### 3. 监控和日志

#### 配置日志

```env
LOG_LEVEL=INFO
LOG_FILE=logs/luna_aster.log
LOG_ROTATION=1 day
LOG_RETENTION=7 days
```

#### 添加监控

```bash
# 安装监控工具
pip install prometheus-client psutil

# 启用指标收集
ENABLE_METRICS=true
METRICS_PORT=9090
```

### 4. 安全配置

#### 启用 HTTPS

```env
# 使用 SSL 证书
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem

# 启用安全头
ENABLE_SECURITY_HEADERS=true
```

#### 配置 CORS

```env
# 限制允许的源
ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com

# 启用认证
ENABLE_AUTH=true
JWT_SECRET=your-jwt-secret-here
```

## 📚 下一步

安装完成后，您可以：

1. 阅读 [API 文档](./API.md) 了解详细的接口说明
2. 查看 [开发指南](../README.md#开发指南) 学习如何自定义功能
3. 参考 [故障排除指南](./TROUBLESHOOTING.md) 解决常见问题
4. 加入 [社区讨论](https://github.com/your-username/Luna-Aster/discussions) 获取帮助

## 🆘 获取帮助

如果您在安装过程中遇到问题：

1. 查看 [常见问题](#常见问题) 部分
2. 搜索 [GitHub Issues](https://github.com/your-username/Luna-Aster/issues)
3. 创建新的 Issue 描述您的问题
4. 加入我们的 [Discord 社区](https://discord.gg/your-invite)

---

祝您使用愉快！🌙✨