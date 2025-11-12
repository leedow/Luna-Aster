"""
消息处理服务
负责处理不同类型的消息并调用相应的服务

采用流水线模式（Pipeline Pattern）实现并行处理：
    Audio Queue -> VAD Worker -> ASR Worker -> Text Queue -> LLM Worker -> Reply Queue -> TTS Worker
    
流水线特点：
1. 使用 asyncio.Queue 连接各个处理阶段
2. 每个 Worker 独立运行，并行处理数据
3. 使用 None 作为结束信号优雅终止流水线
4. 通过 asyncio.gather 并发运行所有 Worker
5. VAD Worker 负责检测语音片段，只将有效的语音片段传递给 ASR
"""

import asyncio
from typing import Optional, Dict
from datetime import datetime
from loguru import logger

from models.message import (
    Message, MessageType,
    create_llm_response_message,
    create_system_message,
    create_error_message,
    create_status_update_message,
    SpeechRecognitionMessage,
)
from core.llm.llm_service import LLMService
from core.asr.asr_service import ASRService
from core.tts.tts_service import TTSService
from core.vad.vad_service import VADService

class MessageHandler:
    """消息处理器 - 流水线模式"""
    
    def __init__(self, llm_service: LLMService, asr_service: ASRService, tts_service: TTSService, vad_service: VADService):
        self.llm_service = llm_service
        self.asr_service = asr_service
        self.tts_service = tts_service
        self.vad_service = vad_service
        self.total_messages = 0
        
        # 用户会话状态
        self.user_sessions = {}
        
        # 流水线队列：为每个客户端维护独立的流水线
        # client_id -> {"audio_queue": Queue, "vad_queue": Queue, "asr_queue": Queue, "llm_queue": Queue, 
        #              "pipeline_task": gather_coro, "tasks": [Task, Task, Task, Task]}
        self.pipelines: Dict[str, dict] = {}
        
        # WebSocket连接引用（用于发送流式消息）
        self.websocket_manager = None
    
    def set_websocket_manager(self, websocket_manager):
        """设置WebSocket管理器（用于发送流式消息）"""
        self.websocket_manager = websocket_manager
    
    async def _create_pipeline(self, client_id: str):
        """为客户端创建处理流水线：Audio -> VAD -> ASR -> LLM -> TTS"""
        if client_id in self.pipelines:
            logger.warning(f"⚠️ 客户端 {client_id} 的流水线已存在，先销毁旧的")
            await self._destroy_pipeline(client_id)
        
        # 创建四个队列连接五个阶段（参考流水线模式）
        q1 = asyncio.Queue()  # Audio -> VAD
        q2 = asyncio.Queue()  # VAD -> ASR
        q3 = asyncio.Queue()  # ASR -> LLM
        q4 = asyncio.Queue()  # LLM -> TTS
        
        # 为每个 worker 创建 task，然后使用 gather 收集
        vad_task = asyncio.create_task(self._vad_worker(client_id, q1, q2))
        asr_task = asyncio.create_task(self._asr_worker(client_id, q2, q3))
        llm_task = asyncio.create_task(self._llm_worker(client_id, q3, q4))
        tts_task = asyncio.create_task(self._tts_worker(client_id, q4))
        
        # 使用 gather 收集所有 task（用于统一等待和错误处理）
        pipeline_task = asyncio.gather(
            vad_task,
            asr_task,
            llm_task,
            tts_task,
            return_exceptions=True
        )
        
        self.pipelines[client_id] = {
            "audio_queue": q1,
            "vad_queue": q2,
            "asr_queue": q3,
            "llm_queue": q4,
            "pipeline_task": pipeline_task,
            "tasks": [vad_task, asr_task, llm_task, tts_task],  # 保存 task 引用以便取消
        }
        
        logger.info(f"🚀 已为客户端 {client_id} 创建处理流水线 [Audio -> VAD -> ASR -> LLM -> TTS]")
    
    async def _destroy_pipeline(self, client_id: str):
        """销毁客户端的处理流水线"""
        if client_id not in self.pipelines:
            return
        
        pipeline = self.pipelines[client_id]
        
        # 发送结束信号 None 到队列头（参考示例代码）
        try:
            await pipeline["audio_queue"].put(None)
        except Exception as e:
            logger.debug(f"发送结束信号失败: {e}")
        
        # 等待流水线任务完成（设置超时）
        try:
            await asyncio.wait_for(
                pipeline["pipeline_task"],
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ 客户端 {client_id} 的流水线任务超时，强制取消")
            # 取消所有 task
            for task in pipeline.get("tasks", []):
                task.cancel()
            # 等待 gather 完成
            try:
                await pipeline["pipeline_task"]
            except asyncio.CancelledError:
                pass
        except Exception as e:
            logger.error(f"❌ 销毁流水线时出错: {e}")
        
        del self.pipelines[client_id]
        logger.info(f"🛑 已销毁客户端 {client_id} 的处理流水线")
    
    async def _vad_worker(self, client_id: str, queue_in: asyncio.Queue, queue_out: asyncio.Queue):
        """VAD工作协程：处理音频数据 -> 检测语音片段 -> 传递给ASR"""
        logger.info(f"🎤 [VAD Worker] 已启动 - 客户端: {client_id}")
        
        try:
            while True:
                # 从输入队列获取音频数据
                audio_item = await queue_in.get()
                
                # None 表示结束信号
                if audio_item is None:
                    await queue_out.put(None)
                    break
                
                try:
                    # 提取音频数据和参数
                    audio_data = audio_item["audio_data"]
                    language = audio_item.get("language")
                    is_final = audio_item.get("is_final", False)
                    audio_format = audio_item.get("audio_format", "pcm")
                    sample_rate = audio_item.get("sample_rate", 16000)
                    channels = audio_item.get("channels", 1)

                    
                    
                    # 调用VAD服务进行语音活动检测
                    result = await self.vad_service.detect_speech(
                        audio_data,
                        client_id=client_id,
                        audio_format=audio_format,
                        sample_rate=sample_rate,
                        channels=channels,
                        is_final=is_final,
                    )
                    
                    # 如果VAD检测到有效的语音片段，传递给ASR队列
                    if result and result.get("vad_detected") and result.get("speech_segment"):
                        speech_segment = result["speech_segment"]
                        logger.info(f"🎤 [VAD] 检测到语音片段: {len(speech_segment)}B")
                        
                        # 将检测到的语音片段传递给ASR队列
                        await queue_out.put({
                            "audio_data": speech_segment,
                            "language": language,
                            "is_final": True,  # VAD检测到的片段是完整的
                            "audio_format": audio_format,
                            "sample_rate": sample_rate,
                            "channels": channels,
                            "vad_metadata": result.get("vad_metadata", {}),
                        })
                    elif result and result.get("speech_active"):
                        # 语音进行中，但还未结束，不传递给ASR
                        logger.debug(f"🔄 [VAD] 语音进行中，等待结束...")
                    # 如果没有检测到语音，静默丢弃（不传递给ASR）
                
                except Exception as e:
                    logger.error(f"❌ [VAD Worker] 处理失败: {str(e)}")
                    # VAD失败不影响整体流程，继续处理下一个音频块
        
        finally:
            logger.info(f"🛑 [VAD Worker] 已停止 - 客户端: {client_id}")
    
    async def _asr_worker(self, client_id: str, queue_in: asyncio.Queue, queue_out: asyncio.Queue):
        """ASR工作协程：处理已通过VAD检测的语音片段 -> 识别文本"""
        logger.info(f"🎤 [ASR Worker] 已启动 - 客户端: {client_id}")
        
        try:
            while True:
                # 从输入队列获取音频数据
                audio_item = await queue_in.get()
                
                # None 表示结束信号（参考示例代码）
                if audio_item is None:
                    await queue_out.put(None)
                    break
                
                try:
                    # 提取音频数据和参数
                    audio_data = audio_item["audio_data"]
                    language = audio_item.get("language")
                    is_final = audio_item.get("is_final", False)
                    audio_format = audio_item.get("audio_format", "pcm")
                    sample_rate = audio_item.get("sample_rate", 16000)
                    channels = audio_item.get("channels", 1)
                    
                    # 调用ASR服务识别
                    # 注意：音频已经通过VAD检测，直接进行ASR识别，跳过VAD检测
                    result = await self.asr_service.transcribe_audio(
                        audio_data,
                        client_id=client_id,
                        language=language,
                        is_final=is_final,
                        audio_format=audio_format,
                        sample_rate=sample_rate,
                        channels=channels,
                        skip_vad=True,  # 跳过VAD检测，因为已经在VAD worker中完成
                    )
                    
                    # 如果识别出文本，发送给前端并传递给下一阶段
                    if result and result.get("text"):
                        text = result["text"].strip()
                        if text:
                            logger.info(f"🎤 [ASR] 识别: {text[:50]}...")
                            
                            # 发送ASR识别结果给前端
                            await self._send_asr_result(client_id, text, result)
                            
                            #传递给LLM队列
                            await queue_out.put({
                                "text": text,
                                "metadata": result
                            })
                    
                except Exception as e:
                    logger.error(f"❌ [ASR Worker] 处理失败: {str(e)}")
                    await self._send_error(client_id, f"语音识别失败: {str(e)}", "ASR_ERROR")
        
        finally:
            logger.info(f"🛑 [ASR Worker] 已停止 - 客户端: {client_id}")
    
    async def _llm_worker(self, client_id: str, queue_in: asyncio.Queue, queue_out: asyncio.Queue):
        """LLM工作协程：处理识别文本 -> 生成回复"""
        logger.info(f"🤖 [LLM Worker] 已启动 - 客户端: {client_id}")
        
        try:
            while True:
                # 从输入队列获取识别文本
                asr_item = await queue_in.get()
                
                # None 表示结束信号（参考示例代码）
                if asr_item is None:
                    await queue_out.put(None)
                    break
                
                try:
                    text = asr_item["text"]
                    
                    # 调用LLM生成回复
                    start_time = datetime.now()
                    response = await self.llm_service.generate_response(
                        text,
                        client_id=client_id
                    )
                    processing_time = (datetime.now() - start_time).total_seconds()
                    
                    reply_text = response.get("content", "").strip()
                    if reply_text:
                        logger.info(f"🤖 [LLM] 回复: {reply_text[:50]}... (耗时: {processing_time:.2f}s)")
                        
                        # 发送LLM回复给前端
                        await self._send_llm_result(client_id, reply_text, response, processing_time)
                        
                        # 传递给TTS队列
                        await queue_out.put({
                            "text": reply_text,
                            "metadata": response
                        })
                
                except Exception as e:
                    logger.error(f"❌ [LLM Worker] 处理失败: {str(e)}")
                    await self._send_error(client_id, f"生成回复失败: {str(e)}", "LLM_ERROR")
        
        finally:
            logger.info(f"🛑 [LLM Worker] 已停止 - 客户端: {client_id}")
    
    async def _tts_worker(self, client_id: str, queue_in: asyncio.Queue):
        """TTS工作协程：处理回复文本 -> 合成语音"""
        logger.info(f"🔊 [TTS Worker] 已启动 - 客户端: {client_id}")
        
        try:
            while True:
                # 从输入队列获取LLM回复
                llm_item = await queue_in.get()
                
                # None 表示结束信号（参考示例代码）
                if llm_item is None:
                    break
                
                try:
                    text = llm_item["text"]
                    
                    # 调用TTS合成语音
                    result = await self.tts_service.synthesize_speech(
                        text,
                        client_id=client_id
                    )
                    
                    # 发送音频数据给前端
                    if result and result.get("audio_data"):
                        logger.info(f"🔊 [TTS] 已合成语音: {text[:30]}...")
                        await self._send_tts_result(client_id, text, result)
                
                except Exception as e:
                    logger.error(f"❌ [TTS Worker] 处理失败: {str(e)}")
                    await self._send_error(client_id, f"语音合成失败: {str(e)}", "TTS_ERROR")
        
        finally:
            logger.info(f"🛑 [TTS Worker] 已停止 - 客户端: {client_id}")
    
    # ==================== 辅助方法：消息发送 ====================
    
    async def _send_asr_result(self, client_id: str, text: str, result: dict):
        """发送ASR识别结果给前端"""
        if not self.websocket_manager:
            logger.warning(f"⚠️ WebSocket管理器未设置，无法发送ASR结果给客户端 {client_id}")
            return

        try:
            asr_message = SpeechRecognitionMessage(
                content=text,
                confidence=result.get("confidence"),
                language=result.get("language"),
                client_id=client_id,
                data={
                    "provider": result.get("provider"),
                    "model": result.get("model"),
                    "processing_time": result.get("processing_time"),
                    "is_sentence_end": result.get("is_sentence_end", False),
                    "vad_enabled": result.get("vad_enabled", False),
                }
            )

            if hasattr(asr_message, "model_dump"):
                payload = asr_message.model_dump(exclude_none=True)
            else:
                payload = asr_message.dict(exclude_none=True)

            await self.websocket_manager.send_message_to_client(client_id, payload)
            logger.info(f"✅ ASR识别结果已发送给客户端 {client_id}: {text[:30]}...")
            logger.debug(f"📤 ASR消息详情: type={payload.get('type')}, content={text[:50]}, timestamp={payload.get('timestamp')}")
        except Exception as e:
            logger.error(f"❌ 发送ASR结果失败: {str(e)}")
            logger.exception(f"❌ 发送ASR结果异常详情:")
    
    async def _send_llm_result(self, client_id: str, text: str, response: dict, processing_time: float):
        """发送LLM回复给前端"""
        if not self.websocket_manager:
            logger.warning(f"⚠️ WebSocket管理器未设置，无法发送LLM回复给客户端 {client_id}")
            return

        try:
            llm_message = create_llm_response_message(
                content=text,
                model=response.get("model"),
                tokens_used=response.get("tokens_used"),
                processing_time=processing_time,
                client_id=client_id
            )

            if hasattr(llm_message, "model_dump"):
                payload = llm_message.model_dump(exclude_none=True)
            else:
                payload = llm_message.dict(exclude_none=True)

            await self.websocket_manager.send_message_to_client(client_id, payload)
            logger.debug(f"✅ LLM回复已发送给客户端 {client_id}: {text[:30]}...")
        except Exception as e:
            logger.error(f"❌ 发送LLM回复失败: {str(e)}")
    
    async def _send_tts_result(self, client_id: str, text: str, result: dict):
        """发送TTS音频数据给前端"""
        if not self.websocket_manager:
            logger.warning(f"⚠️ WebSocket管理器未设置，无法发送TTS结果给客户端 {client_id}")
            return

        try:
            import base64

            audio_b64 = base64.b64encode(result["audio_data"]).decode("utf-8")
            tts_message = Message(
                type=MessageType.AUDIO_GENERATED,
                content="audio_generated",
                data={
                    "audio_data": audio_b64,
                    "format": result.get("format", "wav"),
                    "text": text,
                    "voice": result.get("voice"),
                    "duration": result.get("duration"),
                    "provider": result.get("provider"),
                },
                client_id=client_id
            )

            if hasattr(tts_message, "model_dump"):
                payload = tts_message.model_dump(exclude_none=True)
            else:
                payload = tts_message.dict(exclude_none=True)

            await self.websocket_manager.send_message_to_client(client_id, payload)
            logger.debug(f"✅ TTS音频已发送给客户端 {client_id}: {text[:30]}...")
        except Exception as e:
            logger.error(f"❌ 发送TTS结果失败: {str(e)}")
    
    async def _send_error(self, client_id: str, message: str, error_code: str):
        """发送错误消息给前端"""
        if not self.websocket_manager:
            logger.warning(f"⚠️ WebSocket管理器未设置，无法发送错误消息给客户端 {client_id}")
            return

        try:
            error_msg = create_error_message(
                message,
                error_code=error_code,
                client_id=client_id
            )

            if hasattr(error_msg, "model_dump"):
                payload = error_msg.model_dump(exclude_none=True)
            else:
                payload = error_msg.dict(exclude_none=True)

            await self.websocket_manager.send_message_to_client(client_id, payload)
            logger.debug(f"✅ 错误消息已发送给客户端 {client_id}: {message[:50]}...")
        except Exception as e:
            logger.error(f"❌ 发送错误消息失败: {str(e)}")
    
    # ==================== 消息处理主入口 ====================
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """处理消息的主入口"""
        self.total_messages += 1
        
        try:
            # 根据消息类型分发处理
            handler_map = {
                MessageType.CHAT: self._handle_chat_message,
                MessageType.CONNECTION_ESTABLISHED: self._handle_connection_established,
                MessageType.START_LISTENING: self._handle_start_listening,
                MessageType.STOP_LISTENING: self._handle_stop_listening,
                MessageType.AUDIO_DATA: self._handle_audio_data,
                MessageType.START_SPEAKING: self._handle_start_speaking,
                MessageType.STOP_SPEAKING: self._handle_stop_speaking,
                MessageType.HEARTBEAT: self._handle_heartbeat,
            }
            
            handler = handler_map.get(message.type)
            if handler:
                return await handler(message)
            else:
                logger.warning(f"⚠️ 未知的消息类型: {message.type}")
                return create_error_message(
                    f"未知的消息类型: {message.type}",
                    error_code="UNKNOWN_MESSAGE_TYPE",
                    client_id=message.client_id
                )
                
        except Exception as e:
            logger.error(f"❌ 处理消息时发生错误: {str(e)}")
            return create_error_message(
                f"处理消息时发生错误: {str(e)}",
                error_code="MESSAGE_PROCESSING_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_chat_message(self, message: Message) -> Optional[Message]:
        """处理聊天消息"""
        if not message.content:
            return create_error_message(
                "聊天消息内容不能为空",
                error_code="EMPTY_CHAT_MESSAGE",
                client_id=message.client_id
            )
        
        logger.info(f"💬 处理聊天消息: {message.content[:50]}...")
        
        try:
            # 调用LLM服务生成回复
            start_time = datetime.now()
            response = await self.llm_service.generate_response(
                message.content, 
                client_id=message.client_id
            )
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 创建LLM响应消息
            llm_response = create_llm_response_message(
                content=response.get("content", "抱歉，我无法生成回复。"),
                model=response.get("model"),
                tokens_used=response.get("tokens_used"),
                processing_time=processing_time,
                client_id=message.client_id
            )
            
            logger.info(f"🤖 LLM回复生成完成，耗时: {processing_time:.2f}秒")
            return llm_response
            
        except Exception as e:
            logger.error(f"❌ LLM处理失败: {str(e)}")
            return create_error_message(
                f"生成回复时发生错误: {str(e)}",
                error_code="LLM_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_connection_established(self, message: Message) -> Optional[Message]:
        """处理连接建立消息"""
        logger.info(f"🤝 客户端 {message.client_id} 连接已确认")
        
        # 初始化用户会话
        if message.client_id:
            self.user_sessions[message.client_id] = {
                "connected_at": datetime.now(),
                "is_listening": False,
                "is_speaking": False,
                "conversation_history": []
            }
        
        return create_system_message(
            "连接已建立，Luna 已准备就绪！",
            level="info",
            client_id=message.client_id
        )
    
    async def _handle_start_listening(self, message: Message) -> Optional[Message]:
        """处理开始语音识别消息 - 启动流水线"""
        logger.info(f"🎤 客户端 {message.client_id} 开始语音识别")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_listening"] = True
        
        # 创建处理流水线（ASR -> LLM -> TTS）
        try:
            await self._create_pipeline(message.client_id)
            
            # 启动ASR服务
            await self.asr_service.start_listening(message.client_id)
            
            return create_status_update_message(
                service="asr",
                status="listening",
                details={"message": "语音识别流水线已启动"},
                client_id=message.client_id
            )
        except Exception as e:
            logger.error(f"❌ 启动语音识别流水线失败: {str(e)}")
            return create_error_message(
                f"启动语音识别失败: {str(e)}",
                error_code="ASR_START_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_stop_listening(self, message: Message) -> Optional[Message]:
        """处理停止语音识别消息 - 停止流水线"""
        logger.info(f"🛑 客户端 {message.client_id} 停止语音识别")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_listening"] = False
        
        # 停止ASR服务和流水线
        try:
            await self.asr_service.stop_listening(message.client_id)
            
            # 销毁处理流水线
            await self._destroy_pipeline(message.client_id)
            
            return create_status_update_message(
                service="asr",
                status="stopped",
                details={"message": "语音识别流水线已停止"},
                client_id=message.client_id
            )
        except Exception as e:
            logger.error(f"❌ 停止语音识别流水线失败: {str(e)}")
            return create_error_message(
                f"停止语音识别失败: {str(e)}",
                error_code="ASR_STOP_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_audio_data(self, message: Message) -> Optional[Message]:
        """处理音频数据消息 - 放入流水线队列"""
        logger.debug(f"🎵 收到客户端 {message.client_id} 的音频数据")

        try:
            # 检查流水线是否已创建，如果不存在则自动创建
            if message.client_id not in self.pipelines:
                logger.info(f"⚙️ 客户端 {message.client_id} 的流水线不存在，自动创建...")
                try:
                    await self._create_pipeline(message.client_id)
                    await self.asr_service.start_listening(message.client_id)
                    logger.info(f"✅ 已自动为客户端 {message.client_id} 创建流水线")
                except Exception as e:
                    logger.error(f"❌ 自动创建流水线失败: {str(e)}")
                    return create_error_message(
                        f"自动创建流水线失败，请先发送 START_LISTENING 消息: {str(e)}",
                        error_code="PIPELINE_CREATE_ERROR",
                        client_id=message.client_id,
                    )
            
            if message.data and "audio_data" in message.data:
                import base64
                audio_data = base64.b64decode(message.data["audio_data"])
                
                # 将音频数据放入流水线队列
                # 前端发送的字段名是 "format"，后端使用 "audio_format"
                audio_format = message.data.get("audio_format") or message.data.get("format", "pcm")
                audio_item = {
                    "audio_data": audio_data,
                    "language": message.data.get("language"),
                    "is_final": message.data.get("is_final", False),
                    "audio_format": audio_format,  # 支持 "format" 和 "audio_format" 两种字段名
                    "sample_rate": message.data.get("sample_rate", 16000),
                    "channels": message.data.get("channels", 1),
                }
                
                pipeline = self.pipelines[message.client_id]
                await pipeline["audio_queue"].put(audio_item)
                
                logger.debug(f"✅ 音频数据已放入流水线队列")
            
            # 不返回消息，由worker异步处理并发送结果
            return None

        except Exception as e:
            logger.error(f"❌ 处理音频数据失败: {str(e)}")
            return create_error_message(
                f"处理音频数据失败: {str(e)}",
                error_code="AUDIO_PROCESSING_ERROR",
                client_id=message.client_id,
            )
    
    async def _handle_start_speaking(self, message: Message) -> Optional[Message]:
        """处理开始语音合成消息"""
        logger.info(f"🔊 客户端 {message.client_id} 开始语音合成")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_speaking"] = True
        
        # 校验文本
        if not message.content or not message.content.strip():
            return create_error_message(
                "语音合成文本为空",
                error_code="TTS_EMPTY_TEXT",
                client_id=message.client_id
            )
        
        try:
            # 调用 TTS 合成
            result = await self.tts_service.synthesize_speech(message.content, client_id=message.client_id)
            
            # 将二进制音频编码为 base64
            import base64
            audio_b64 = base64.b64encode(result.get("audio_data", b""))
            audio_b64_str = audio_b64.decode("utf-8") if audio_b64 else ""
            if not audio_b64_str:
                raise Exception("生成的音频数据为空")
            
            # 返回前端期望的 audio_generated 消息
            return Message(
                type=MessageType.AUDIO_GENERATED,
                content="audio_generated",
                data={
                    "audio_data": audio_b64_str,
                    "format": result.get("format", "wav"),
                    "text": message.content,
                    "voice": result.get("voice"),
                    "duration": result.get("duration"),
                    "provider": result.get("provider"),
                },
                client_id=message.client_id
            )
        
        except Exception as e:
            logger.error(f"❌ 语音合成失败: {str(e)}")
            return create_error_message(
                f"语音合成失败: {str(e)}",
                error_code="TTS_ERROR",
                client_id=message.client_id
            )
    
    async def _handle_stop_speaking(self, message: Message) -> Optional[Message]:
        """处理停止语音合成消息"""
        logger.info(f"🔇 客户端 {message.client_id} 停止语音合成")
        
        # 更新会话状态
        if message.client_id in self.user_sessions:
            self.user_sessions[message.client_id]["is_speaking"] = False
        
        return create_status_update_message(
            service="tts",
            status="stopped",
            details={"message": "语音合成已停止"},
            client_id=message.client_id
        )
    
    async def _handle_heartbeat(self, message: Message) -> Optional[Message]:
        """处理心跳消息"""
        logger.debug(f"💓 收到客户端 {message.client_id} 的心跳")
        
        # 返回心跳响应
        return Message(
            type=MessageType.HEARTBEAT,
            content="pong",
            timestamp=datetime.now(),
            client_id=message.client_id
        )
    
    def get_user_session(self, client_id: str) -> Optional[dict]:
        """获取用户会话信息"""
        return self.user_sessions.get(client_id)
    
    async def cleanup_user_session(self, client_id: str):
        """清理用户会话和流水线"""
        # 销毁流水线
        await self._destroy_pipeline(client_id)
        
        # 清理会话数据
        if client_id in self.user_sessions:
            del self.user_sessions[client_id]
            logger.info(f"🧹 已清理客户端 {client_id} 的会话数据")