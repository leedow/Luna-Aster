#!/usr/bin/env python3
"""
Luna-Aster 项目验证脚本
测试项目的基本功能和依赖是否正常
"""

import sys
import os
import asyncio
import json
from pathlib import Path

# 添加后端路径到 Python 路径
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def test_imports():
    """测试关键模块导入"""
    print("🔍 测试模块导入...")
    
    try:
        # 测试 FastAPI 相关
        import fastapi
        import uvicorn
        print("✅ FastAPI 和 Uvicorn 导入成功")
        
        # 测试 WebSocket
        import websockets
        print("✅ WebSocket 库导入成功")
        
        # 测试数据处理
        import pydantic
        print("✅ Pydantic 导入成功")
        
        # 测试配置管理
        from dotenv import load_dotenv
        print("✅ python-dotenv 导入成功")
        
        # 测试日志
        from loguru import logger
        print("✅ Loguru 导入成功")
        
        return True
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_project_structure():
    """测试项目结构"""
    print("\n🏗️ 测试项目结构...")
    
    required_files = [
        "backend/main.py",
        "backend/requirements.txt",
        "backend/.env.example",
        "backend/config/settings.py",
        "backend/models/message.py",
        "backend/services/websocket_manager.py",
        "backend/services/message_handler.py",
        "frontend/package.json",
        "frontend/src/App.tsx",
        "frontend/src/contexts/WebSocketContext.tsx",
        "docs/README.md",
        "docs/API.md",
        "docs/SETUP.md",
        "shared/protocols.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        if not full_path.exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"\n❌ 缺少文件:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ 项目结构完整")
    return True

def test_backend_modules():
    """测试后端模块"""
    print("\n🔧 测试后端模块...")
    
    try:
        # 测试配置
        from config.settings import Settings
        settings = Settings()
        print("✅ 配置模块正常")
        
        # 测试消息模型
        from models.message import Message, MessageType, create_chat_message
        test_message = create_chat_message("测试消息", "test-client")
        print("✅ 消息模型正常")
        
        # 测试 WebSocket 管理器
        from services.websocket_manager import WebSocketManager
        ws_manager = WebSocketManager()
        print("✅ WebSocket 管理器正常")
        
        # 测试服务
        from core.llm.llm_service import LLMService
        from core.asr.asr_service import ASRService
        from core.tts.tts_service import TTSService
        
        # 使用测试配置 - 创建 Settings 对象
        test_settings = Settings()
        test_settings.llm_provider = "mock"
        test_settings.asr_provider = "mock"
        test_settings.tts_provider = "mock"
        
        llm_service = LLMService(test_settings)
        asr_service = ASRService(test_settings)
        tts_service = TTSService(test_settings)
        print("✅ AI 服务模块正常")
        
        # 测试消息处理器
        from services.message_handler import MessageHandler
        message_handler = MessageHandler(llm_service, asr_service, tts_service)
        print("✅ 消息处理器正常")
        
        return True
    except Exception as e:
        print(f"❌ 后端模块测试失败: {e}")
        return False

async def test_async_functionality():
    """测试异步功能"""
    print("\n⚡ 测试异步功能...")
    
    try:
        from services.message_handler import MessageHandler
        from core.llm.llm_service import LLMService
        from core.asr.asr_service import ASRService
        from core.tts.tts_service import TTSService
        from models.message import create_chat_message
        
        # 创建测试服务 - 使用 Settings 对象
        from config.settings import Settings
        test_settings = Settings()
        test_settings.llm_provider = "mock"
        test_settings.asr_provider = "mock"
        test_settings.tts_provider = "mock"
        
        llm_service = LLMService(test_settings)
        asr_service = ASRService(test_settings)
        tts_service = TTSService(test_settings)
        message_handler = MessageHandler(llm_service, asr_service, tts_service)
        
        # 测试消息处理
        test_message = create_chat_message("你好", "test-client")
        response = await message_handler.handle_message(test_message)
        
        if response:
            print("✅ 异步消息处理正常")
            print(f"   响应类型: {response.type}")
            print(f"   响应内容: {response.content[:50]}...")
        else:
            print("⚠️ 消息处理返回空响应")
        
        return True
    except Exception as e:
        print(f"❌ 异步功能测试失败: {e}")
        return False

def test_configuration():
    """测试配置"""
    print("\n⚙️ 测试配置...")
    
    try:
        from config.settings import Settings
        
        # 测试默认配置
        settings = Settings()
        print(f"✅ 服务器配置: {settings.host}:{settings.port}")
        print(f"✅ 调试模式: {settings.debug}")
        print(f"✅ LLM 提供商: {getattr(settings, 'llm_provider', 'mock')}")
        
        # 测试环境变量文件
        env_example = Path(__file__).parent / "backend" / ".env.example"
        if env_example.exists():
            print("✅ 环境配置示例文件存在")
        else:
            print("❌ 环境配置示例文件缺失")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        return False

def test_documentation():
    """测试文档"""
    print("\n📚 测试文档...")
    
    docs_files = [
        ("README.md", "项目说明"),
        ("docs/API.md", "API文档"),
        ("docs/SETUP.md", "安装指南"),
        ("docs/DEVELOPMENT.md", "开发指南"),
        ("docs/TROUBLESHOOTING.md", "故障排除"),
        ("shared/protocols.md", "通信协议")
    ]
    
    for file_path, description in docs_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists() and full_path.stat().st_size > 100:
            print(f"✅ {description}: {file_path}")
        else:
            print(f"❌ {description}缺失或内容不足: {file_path}")
            return False
    
    return True

def generate_report(results):
    """生成测试报告"""
    print("\n" + "="*50)
    print("📊 Luna-Aster 项目验证报告")
    print("="*50)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"总测试项: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n详细结果:")
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！项目配置正确，可以开始使用。")
        print("\n下一步:")
        print("1. 复制 backend/.env.example 到 backend/.env")
        print("2. 配置 API 密钥（或使用 mock 模式测试）")
        print("3. 安装依赖: cd backend && pip install -r requirements.txt")
        print("4. 安装前端依赖: cd frontend && npm install")
        print("5. 启动后端: cd backend && python main.py")
        print("6. 启动前端: cd frontend && npm start")
    else:
        print("\n⚠️ 部分测试失败，请检查上述错误信息并修复。")
    
    return passed_tests == total_tests

async def main():
    """主测试函数"""
    print("🚀 开始 Luna-Aster 项目验证...")
    print("="*50)
    
    # 运行所有测试
    results = {}
    
    results["模块导入"] = test_imports()
    results["项目结构"] = test_project_structure()
    results["后端模块"] = test_backend_modules()
    results["异步功能"] = await test_async_functionality()
    results["配置管理"] = test_configuration()
    results["文档完整性"] = test_documentation()
    
    # 生成报告
    success = generate_report(results)
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 测试过程中发生错误: {e}")
        sys.exit(1)