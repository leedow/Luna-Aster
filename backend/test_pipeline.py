"""
流水线模式测试脚本
演示 ASR -> LLM -> TTS 流水线的工作原理
"""

import asyncio
from datetime import datetime


async def mock_asr_worker(client_id: str, audio_queue: asyncio.Queue, asr_queue: asyncio.Queue):
    """模拟 ASR Worker：处理音频 -> 识别文本"""
    print(f"🎤 [ASR Worker] 启动 - 客户端: {client_id}")
    
    try:
        while True:
            audio_item = await audio_queue.get()
            
            if audio_item is None:
                print(f"🎤 [ASR Worker] 收到结束信号")
                await asr_queue.put(None)
                break
            
            # 模拟 ASR 处理（0.2秒）
            await asyncio.sleep(0.2)
            
            text = f"识别文本({audio_item})"
            print(f"🎤 [ASR] 完成: {text}")
            
            # 传递给下一阶段
            await asr_queue.put(text)
    
    finally:
        print(f"🛑 [ASR Worker] 已停止")


async def mock_llm_worker(client_id: str, asr_queue: asyncio.Queue, llm_queue: asyncio.Queue):
    """模拟 LLM Worker：处理文本 -> 生成回复"""
    print(f"🤖 [LLM Worker] 启动 - 客户端: {client_id}")
    
    try:
        while True:
            text = await asr_queue.get()
            
            if text is None:
                print(f"🤖 [LLM Worker] 收到结束信号")
                await llm_queue.put(None)
                break
            
            # 模拟 LLM 处理（0.3秒）
            await asyncio.sleep(0.3)
            
            reply = f"AI回复({text})"
            print(f"🤖 [LLM] 完成: {reply}")
            
            # 传递给下一阶段
            await llm_queue.put(reply)
    
    finally:
        print(f"🛑 [LLM Worker] 已停止")


async def mock_tts_worker(client_id: str, llm_queue: asyncio.Queue):
    """模拟 TTS Worker：处理回复 -> 合成语音"""
    print(f"🔊 [TTS Worker] 启动 - 客户端: {client_id}")
    
    try:
        while True:
            reply = await llm_queue.get()
            
            if reply is None:
                print(f"🔊 [TTS Worker] 收到结束信号")
                break
            
            # 模拟 TTS 处理（0.1秒）
            await asyncio.sleep(0.1)
            
            print(f"🔊 [TTS] 播放: {reply}")
    
    finally:
        print(f"🛑 [TTS Worker] 已停止")


async def test_pipeline():
    """测试流水线模式"""
    print("=" * 60)
    print("流水线模式测试")
    print("=" * 60)
    
    client_id = "test-client"
    
    # 创建队列
    audio_queue = asyncio.Queue()
    asr_queue = asyncio.Queue()
    llm_queue = asyncio.Queue()
    
    # 启动 Workers
    print("\n🚀 启动流水线...")
    workers = [
        asyncio.create_task(mock_asr_worker(client_id, audio_queue, asr_queue)),
        asyncio.create_task(mock_llm_worker(client_id, asr_queue, llm_queue)),
        asyncio.create_task(mock_tts_worker(client_id, llm_queue)),
    ]
    
    # 等待一下让 workers 启动
    await asyncio.sleep(0.1)
    
    # 模拟发送音频数据
    print("\n📤 开始发送音频数据...")
    start_time = datetime.now()
    
    for i in range(5):
        audio_data = f"音频块{i}"
        print(f"\n📥 发送: {audio_data}")
        await audio_queue.put(audio_data)
        # 模拟音频采集间隔
        await asyncio.sleep(0.1)
    
    print("\n⏱️  所有音频已发送，等待流水线处理...")
    
    # 发送结束信号
    await audio_queue.put(None)
    
    # 等待所有 workers 完成
    await asyncio.gather(*workers)
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print(f"✅ 流水线测试完成")
    print(f"⏱️  总耗时: {total_time:.2f}秒")
    print("=" * 60)
    
    # 计算理论时间
    print("\n📊 性能分析：")
    print(f"   音频块数量: 5")
    print(f"   单块处理时间: ASR(0.2s) + LLM(0.3s) + TTS(0.1s) = 0.6s")
    print(f"   同步模式耗时: 5 × 0.6s = 3.0s")
    print(f"   流水线模式耗时: {total_time:.2f}s")
    print(f"   性能提升: {((3.0 - total_time) / 3.0 * 100):.1f}%")


async def test_comparison():
    """对比同步模式和流水线模式"""
    print("\n" + "=" * 60)
    print("同步模式 vs 流水线模式 对比测试")
    print("=" * 60)
    
    # 同步模式
    print("\n🔄 测试同步模式...")
    sync_start = datetime.now()
    
    for i in range(5):
        print(f"\n处理音频块{i}:")
        # ASR
        await asyncio.sleep(0.2)
        print(f"  🎤 ASR完成")
        # LLM
        await asyncio.sleep(0.3)
        print(f"  🤖 LLM完成")
        # TTS
        await asyncio.sleep(0.1)
        print(f"  🔊 TTS完成")
    
    sync_time = (datetime.now() - sync_start).total_seconds()
    print(f"\n⏱️  同步模式总耗时: {sync_time:.2f}秒")
    
    # 流水线模式
    print("\n🚀 测试流水线模式...")
    await test_pipeline()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════╗
║          Luna-Aster 流水线模式测试                        ║
║                                                          ║
║  演示 ASR -> LLM -> TTS 流水线的并行处理能力              ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # 运行测试
    asyncio.run(test_comparison())
    
    print("""
\n📝 总结:
   - 流水线模式实现了三个阶段的并行处理
   - 大幅降低端到端延迟
   - 提高系统吞吐量
   - 更好的资源利用率
""")

