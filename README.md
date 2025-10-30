# Luna-Aster 🌙✨

一个基于 React + TypeScript + Electron 的桌面虚拟角色应用，集成了 LLM、ASR（语音识别）和 TTS（语音合成）功能，为用户提供沉浸式的AI虚拟角色交互体验。

## 🎯 功能特性

- 🎭 **虚拟角色交互** - 具有个性化的AI虚拟角色Luna
- 💬 **智能对话** - 集成多种LLM提供商（OpenAI、Anthropic）
- 🎤 **语音识别** - 支持实时语音输入（Whisper、SpeechRecognition）
- 🔊 **语音合成** - 多种TTS引擎（Edge-TTS、gTTS、pyttsx3）
- 🌐 **实时通信** - WebSocket双向通信，低延迟响应
- 🎨 **现代化UI** - 精美的界面设计，流畅的动画效果
- 🔧 **高度可配置** - 灵活的配置系统，支持多种服务提供商
- 📊 **实时状态** - 连接状态、服务状态实时监控
- 🛡️ **安全可靠** - 完善的错误处理和数据验证

## 🛠️ 技术栈

### 前端技术
- **React 18** - 现代化React框架
- **TypeScript** - 类型安全的JavaScript
- **Styled Components** - CSS-in-JS样式解决方案
- **Framer Motion** - 流畅的动画库
- **Vite** - 快速的构建工具
- **Electron** - 跨平台桌面应用框架

### 后端技术
- **FastAPI** - 高性能Python Web框架
- **WebSocket** - 实时双向通信
- **Pydantic** - 数据验证和序列化
- **Uvicorn** - ASGI服务器
- **Asyncio** - 异步编程支持

### AI服务集成
- **LLM**: OpenAI GPT、Anthropic Claude
- **ASR**: OpenAI Whisper、Google Speech Recognition
- **TTS**: Microsoft Edge-TTS、Google gTTS、pyttsx3

## 项目架构

```
Luna-Aster/
├── frontend/                 # Electron + React 前端应用
│   ├── public/              # 静态资源和 Electron 主进程
│   ├── src/                 # React 源代码
│   │   ├── components/      # React 组件
│   │   ├── services/        # 服务层（WebSocket 通信等）
│   │   ├── hooks/           # 自定义 React Hooks
│   │   ├── utils/           # 工具函数
│   │   └── styles/          # 样式文件
│   └── package.json         # 前端依赖配置
├── backend/                 # Python WebSocket 后端服务
│   ├── core/                # 核心业务逻辑
│   │   ├── llm/             # LLM 集成模块
│   │   ├── asr/             # 语音识别模块
│   │   └── tts/             # 语音合成模块
│   ├── services/            # 服务层
│   ├── models/              # 数据模型
│   ├── utils/               # 工具函数
│   ├── config/              # 配置文件
│   ├── main.py              # 应用入口
│   └── requirements.txt     # Python 依赖
├── shared/                  # 前后端共享的类型定义和协议
├── docs/                    # 项目文档
└── scripts/                 # 构建和部署脚本
```

## 技术栈

### 前端
- **Electron**: 桌面应用框架
- **React**: UI 框架
- **TypeScript**: 类型安全的 JavaScript
- **WebSocket**: 与后端实时通信

### 后端
- **Python**: 主要开发语言
- **FastAPI + WebSocket**: Web 框架和实时通信
- **LLM**: 大语言模型集成
- **ASR**: 自动语音识别
- **TTS**: 文本转语音

## 快速开始

### 环境要求
- Node.js >= 16.0.0
- Python >= 3.8
- npm 或 yarn

### 安装依赖
```bash
# 安装所有依赖
npm run install:all
```

### 开发模式
```bash
# 同时启动前端和后端开发服务器
npm run dev
```

### 单独启动
```bash
# 仅启动前端
npm run frontend:dev

# 仅启动后端
npm run backend:dev

# 启动 Electron 应用
npm run electron:dev
```

### 构建
```bash
# 构建整个项目
npm run build
```

## 功能特性

- 🎭 虚拟角色展示和交互
- 🗣️ 语音识别 (ASR)
- 🔊 语音合成 (TTS)
- 🤖 大语言模型对话
- 💬 实时通信
- 🎨 现代化 UI 界面
- 🔧 模块化架构设计

## 开发指南

详细的开发指南请参考 [docs/development.md](docs/development.md)

## 许可证

MIT License