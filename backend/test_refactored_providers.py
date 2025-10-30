#!/usr/bin/env python3
"""
测试重构后的 Provider 系统
验证 LLM、ASR 和 TTS 服务的基本功能
"""

import sys
import traceback
import asyncio
from config.settings import Settings

def test_llm_providers():
    """测试 LLM providers"""
    print("=== 测试 LLM Providers ===")
    try:
        from core.llm.providers import LLMProviderFactory
        from core.llm.llm_service import LLMService
        
        # 测试工厂创建
        factory = LLMProviderFactory()
        available_types = factory.get_available_providers()
        print(f"可用的 LLM provider 类型: {available_types}")
        
        # 测试创建 providers
        config = Settings()
        llm_config = {
            "openai": {"api_key": config.openai_api_key, "model": config.openai_model},
            "anthropic": {"api_key": config.anthropic_api_key, "model": config.anthropic_model},
            "mock": {"model": "mock-model"}
        }
        providers = factory.create_providers_from_config(llm_config)
        print(f"创建了 {len(providers)} 个 LLM providers")
        
        for name, provider in providers.items():
            print(f"  - {provider.get_provider_name()}: 可用={provider.is_available()}")
        
        # 测试 LLM 服务
        llm_service = LLMService(config)
        print(f"LLM 服务初始化成功，providers: {len(llm_service.providers)}")
        
        print("✅ LLM providers 测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ LLM providers 测试失败: {e}")
        traceback.print_exc()
        return False

def test_asr_providers():
    """测试 ASR providers"""
    print("=== 测试 ASR Providers ===")
    try:
        from core.asr.providers import ASRProviderFactory
        from core.asr.asr_service import ASRService
        
        # 测试工厂创建
        factory = ASRProviderFactory()
        available_types = factory.get_available_providers()
        print(f"可用的 ASR provider 类型: {available_types}")
        
        # 测试创建 providers
        config = Settings()
        asr_config = {
            "whisper": {"api_key": config.openai_api_key, "model": config.whisper_model},
            "speech_recognition": {"engine": "google"},
            "mock": {"model": "mock-model"}
        }
        providers = factory.create_providers_from_config(asr_config)
        print(f"创建了 {len(providers)} 个 ASR providers")
        
        for name, provider in providers.items():
            print(f"  - {provider.get_provider_name()}: 可用={provider.is_available()}")
        
        # 测试 ASR 服务
        asr_service = ASRService(config)
        print(f"ASR 服务初始化成功，providers: {len(asr_service.providers)}")
        
        print("✅ ASR providers 测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ ASR providers 测试失败: {e}")
        traceback.print_exc()
        return False

def test_tts_providers():
    """测试 TTS providers"""
    print("=== 测试 TTS Providers ===")
    try:
        from core.tts.providers import TTSProviderFactory
        from core.tts.tts_service import TTSService
        
        # 测试工厂创建
        factory = TTSProviderFactory()
        available_types = factory.get_available_providers()
        print(f"可用的 TTS provider 类型: {available_types}")
        
        # 测试创建 providers
        config = Settings()
        tts_configs = [
            {"type": "edge_tts", "voice": config.tts_voice, "rate": config.tts_rate, "pitch": config.tts_pitch},
            {"type": "gtts", "language": "zh-cn"},
            {"type": "pyttsx3", "voice": "default", "rate": 200},
            {"type": "mock", "voice": "default", "language": "zh-CN", "rate": 1.0}
        ]
        providers = factory.create_providers(tts_configs)
        print(f"创建了 {len(providers)} 个 TTS providers")
        
        for provider in providers:
            is_available = asyncio.run(provider.is_available())
            print(f"  - {provider.get_provider_name()}: 可用={is_available}")
        
        # 测试 TTS 服务
        tts_service = TTSService(config)
        print(f"TTS 服务初始化成功，providers: {len(tts_service.providers)}")
        
        print("✅ TTS providers 测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ TTS providers 测试失败: {e}")
        traceback.print_exc()
        return False

def test_provider_info():
    """测试 provider 信息获取"""
    print("=== 测试 Provider 信息 ===")
    try:
        from core.llm.providers import LLMProviderFactory
        from core.asr.providers import ASRProviderFactory
        from core.tts.providers import TTSProviderFactory
        
        # 测试 LLM provider 信息
        llm_factory = LLMProviderFactory()
        llm_types = llm_factory.get_available_providers()
        print(f"LLM Provider 类型: {llm_types}")
        
        # 测试 ASR provider 信息
        asr_factory = ASRProviderFactory()
        asr_types = asr_factory.get_available_providers()
        print(f"ASR Provider 类型: {asr_types}")
        
        # 测试 TTS provider 信息
        tts_factory = TTSProviderFactory()
        tts_types = tts_factory.get_available_providers()
        print(f"TTS Provider 类型: {tts_types}")
        
        print("✅ Provider 信息测试通过\n")
        return True
        
    except Exception as e:
        print(f"❌ Provider 信息测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("开始测试重构后的 Provider 系统...\n")
    
    results = []
    results.append(test_llm_providers())
    results.append(test_asr_providers())
    results.append(test_tts_providers())
    results.append(test_provider_info())
    
    # 总结结果
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试都通过了！重构成功！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())