# Luna-Aster 文档

欢迎来到 Luna-Aster 项目文档！这里包含了项目的完整文档，帮助您快速了解和使用这个智能语音助手系统。

## 📚 文档目录

### 快速开始
- **[安装指南](SETUP.md)** - 环境配置和项目安装步骤
- **[故障排除](TROUBLESHOOTING.md)** - 常见问题诊断和解决方案

### 开发文档
- **[开发指南](DEVELOPMENT.md)** - 开发环境配置和工作流程
- **[API 文档](API.md)** - REST API 和 WebSocket 接口说明

### 技术规范
- **[通信协议](../shared/protocols.md)** - 前后端通信协议定义

## 🚀 项目概览

Luna-Aster 是一个现代化的智能语音助手系统，具有以下特性：

### 核心功能
- **🎤 语音识别 (ASR)** - 支持多种语音识别引擎
- **🧠 智能对话 (LLM)** - 集成多个大语言模型
- **🔊 语音合成 (TTS)** - 高质量的语音输出
- **💬 实时通信** - WebSocket 实时双向通信
- **🎭 虚拟角色** - 可自定义的虚拟助手形象

### 技术架构
- **前端**: React + TypeScript + Styled Components
- **后端**: FastAPI + Python + WebSocket
- **AI 服务**: OpenAI, Anthropic, Whisper, Edge-TTS
- **实时通信**: WebSocket 协议
- **部署**: Docker + Docker Compose

## 📖 使用指南

### 1. 快速开始
如果您是第一次使用，请按以下顺序阅读：

1. [安装指南](SETUP.md) - 配置开发环境
2. [开发指南](DEVELOPMENT.md) - 了解项目结构和开发流程
3. [API 文档](API.md) - 学习接口使用方法

### 2. 开发者指南
如果您想参与开发或自定义功能：

1. [开发指南](DEVELOPMENT.md) - 开发环境和工作流程
2. [通信协议](../shared/protocols.md) - 了解系统通信机制
3. [故障排除](TROUBLESHOOTING.md) - 解决开发中的问题

### 3. 部署指南
如果您想部署到生产环境：

1. [安装指南](SETUP.md) - 生产环境配置
2. [故障排除](TROUBLESHOOTING.md) - 部署问题解决

## 🔧 配置说明

### 环境变量
项目使用环境变量进行配置，主要配置项包括：

- **服务器配置**: HOST, PORT, DEBUG
- **LLM 配置**: API 密钥、模型选择
- **ASR 配置**: 语音识别引擎设置
- **TTS 配置**: 语音合成参数
- **音频配置**: 采样率、格式等

详细配置说明请参考 [安装指南](SETUP.md)。

### 服务提供商
系统支持多个 AI 服务提供商：

- **LLM**: OpenAI GPT, Anthropic Claude
- **ASR**: OpenAI Whisper, SpeechRecognition
- **TTS**: Edge-TTS, Google TTS, pyttsx3

## 🤝 贡献指南

我们欢迎社区贡献！请参考以下资源：

1. [开发指南](DEVELOPMENT.md) - 了解开发规范和流程
2. [GitHub Issues](https://github.com/your-repo/Luna-Aster/issues) - 报告问题或建议功能
3. [Pull Requests](https://github.com/your-repo/Luna-Aster/pulls) - 提交代码贡献

### 贡献类型
- 🐛 Bug 修复
- ✨ 新功能开发
- 📝 文档改进
- 🎨 UI/UX 优化
- ⚡ 性能优化

## 📞 获取帮助

如果您在使用过程中遇到问题：

1. **查看文档** - 首先查看相关文档
2. **故障排除** - 参考 [故障排除指南](TROUBLESHOOTING.md)
3. **搜索问题** - 在 GitHub Issues 中搜索类似问题
4. **提交问题** - 如果问题未解决，请创建新的 Issue

## 📄 许可证

本项目采用 MIT 许可证，详情请参考项目根目录的 LICENSE 文件。

## 🙏 致谢

感谢所有为 Luna-Aster 项目做出贡献的开发者和用户！

---

**最后更新**: 2024年12月
**版本**: 1.0.0