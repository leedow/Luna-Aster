"""
流水线模式示例代码
展示如何使用重构后的 MessageHandler 流水线
"""

import asyncio


# ==================== 简化版示例（纯流水线） ====================

async def audio_source(queue_out):
    """模拟音频源"""
    print("📡 [音频源] 开始发送音频块...")
    for i in range(5):
        await asyncio.sleep(0.1)
        chunk = f"音频块_{i}"
        print(f"📡 [音频源] 发送: {chunk}")
        await queue_out.put(chunk)
    
    # 发送结束信号
    await queue_out.put(None)
    print("📡 [音频源] 发送完毕")


async def asr_worker(queue_in, queue_out):
    """ASR 工作协程"""
    print("🎤 [ASR] Worker 启动")
    try:
        while True:
            # 获取音频块
            chunk = await queue_in.get()
            
            # 检查结束信号
            if chunk is None:
                await queue_out.put(None)  # 传递结束信号
                break
            
            # 模拟 ASR 处理
            await asyncio.sleep(0.2)
            text = f"识别文本({chunk})"
            print(f"🎤 [ASR] 识别: {text}")
            
            # 传递给下一阶段
            await queue_out.put(text)
    finally:
        print("🎤 [ASR] Worker 停止")


async def llm_worker(queue_in, queue_out):
    """LLM 工作协程"""
    print("🤖 [LLM] Worker 启动")
    try:
        while True:
            # 获取识别文本
            text = await queue_in.get()
            
            # 检查结束信号
            if text is None:
                await queue_out.put(None)  # 传递结束信号
                break
            
            # 模拟 LLM 处理
            await asyncio.sleep(0.3)
            reply = f"AI回复({text})"
            print(f"🤖 [LLM] 回复: {reply}")
            
            # 传递给下一阶段
            await queue_out.put(reply)
    finally:
        print("🤖 [LLM] Worker 停止")


async def tts_worker(queue_in):
    """TTS 工作协程（终点，无输出队列）"""
    print("🔊 [TTS] Worker 启动")
    try:
        while True:
            # 获取 LLM 回复
            reply = await queue_in.get()
            
            # 检查结束信号
            if reply is None:
                break
            
            # 模拟 TTS 处理
            await asyncio.sleep(0.1)
            print(f"🔊 [TTS] 播放: {reply}")
    finally:
        print("🔊 [TTS] Worker 停止")


async def simple_pipeline():
    """简化版流水线示例"""
    print("\n" + "="*60)
    print("  简化版流水线示例")
    print("  Audio -> ASR -> LLM -> TTS")
    print("="*60 + "\n")
    
    # 创建三个队列连接四个阶段
    q1 = asyncio.Queue()  # Audio -> ASR
    q2 = asyncio.Queue()  # ASR -> LLM
    q3 = asyncio.Queue()  # LLM -> TTS
    
    # 并行运行所有阶段
    await asyncio.gather(
        audio_source(q1),
        asr_worker(q1, q2),
        llm_worker(q2, q3),
        tts_worker(q3)
    )
    
    print("\n✅ 流水线执行完毕！\n")


# ==================== 完整示例（带错误处理） ====================

async def robust_asr_worker(queue_in, queue_out, fail_at=None):
    """带错误处理的 ASR Worker"""
    print("🎤 [ASR] Worker 启动（健壮版）")
    try:
        count = 0
        while True:
            chunk = await queue_in.get()
            
            if chunk is None:
                await queue_out.put(None)
                break
            
            try:
                count += 1
                
                # 模拟偶尔的错误
                if fail_at and count == fail_at:
                    raise Exception("模拟 ASR 识别失败")
                
                await asyncio.sleep(0.2)
                text = f"识别文本({chunk})"
                print(f"🎤 [ASR] 识别: {text}")
                
                await queue_out.put(text)
                
            except Exception as e:
                print(f"❌ [ASR] 错误: {e}（继续处理下一个）")
                # 不中断流水线，继续处理下一个
                
    finally:
        print("🎤 [ASR] Worker 停止（健壮版）")


async def robust_pipeline():
    """带错误处理的健壮流水线"""
    print("\n" + "="*60)
    print("  健壮版流水线示例（带错误处理）")
    print("  第 2 个音频块会触发 ASR 错误")
    print("="*60 + "\n")
    
    q1 = asyncio.Queue()
    q2 = asyncio.Queue()
    q3 = asyncio.Queue()
    
    await asyncio.gather(
        audio_source(q1),
        robust_asr_worker(q1, q2, fail_at=2),  # 第 2 个会失败
        llm_worker(q2, q3),
        tts_worker(q3)
    )
    
    print("\n✅ 健壮流水线执行完毕！（即使有错误也能继续）\n")


# ==================== 多客户端示例 ====================

async def client_pipeline(client_id: str, num_chunks: int):
    """单个客户端的流水线"""
    print(f"\n[客户端 {client_id}] 流水线启动")
    
    async def audio_gen(q):
        for i in range(num_chunks):
            await asyncio.sleep(0.15)
            await q.put(f"[{client_id}]音频{i}")
        await q.put(None)
    
    async def asr(q_in, q_out):
        while True:
            data = await q_in.get()
            if data is None:
                await q_out.put(None)
                break
            await asyncio.sleep(0.1)
            result = f"识别({data})"
            print(f"  [{client_id}] ASR: {result}")
            await q_out.put(result)
    
    async def llm(q_in, q_out):
        while True:
            data = await q_in.get()
            if data is None:
                await q_out.put(None)
                break
            await asyncio.sleep(0.15)
            result = f"回复({data})"
            print(f"  [{client_id}] LLM: {result}")
            await q_out.put(result)
    
    async def tts(q_in):
        while True:
            data = await q_in.get()
            if data is None:
                break
            await asyncio.sleep(0.05)
            print(f"  [{client_id}] TTS: {data}")
    
    q1, q2, q3 = asyncio.Queue(), asyncio.Queue(), asyncio.Queue()
    
    await asyncio.gather(
        audio_gen(q1),
        asr(q1, q2),
        llm(q2, q3),
        tts(q3)
    )
    
    print(f"[客户端 {client_id}] 流水线结束")


async def multi_client_pipeline():
    """多客户端并发流水线示例"""
    print("\n" + "="*60)
    print("  多客户端并发流水线示例")
    print("  3 个客户端同时运行独立的流水线")
    print("="*60)
    
    # 三个客户端并发运行
    await asyncio.gather(
        client_pipeline("客户端A", 3),
        client_pipeline("客户端B", 4),
        client_pipeline("客户端C", 2),
    )
    
    print("\n✅ 多客户端流水线执行完毕！\n")


# ==================== 主函数 ====================

async def main():
    """运行所有示例"""
    print("\n" + "🚀"*30)
    print("  流水线模式示例")
    print("🚀"*30)
    
    # 1. 简化版示例
    await simple_pipeline()
    
    await asyncio.sleep(1)
    
    # 2. 健壮版示例
    await robust_pipeline()
    
    await asyncio.sleep(1)
    
    # 3. 多客户端示例
    await multi_client_pipeline()
    
    print("\n" + "🎉"*30)
    print("  所有示例运行完毕！")
    print("🎉"*30 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")

