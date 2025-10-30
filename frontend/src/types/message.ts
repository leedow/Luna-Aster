/**
 * 前端消息类型定义
 * 与后端 Python 消息模型保持一致
 */

export enum MessageType {
  // 连接管理
  CONNECTION_ESTABLISHED = 'CONNECTION_ESTABLISHED',
  HEARTBEAT = 'HEARTBEAT',
  
  // 聊天消息
  CHAT = 'CHAT',
  LLM_RESPONSE = 'LLM_RESPONSE',
  
  // 语音识别
  START_LISTENING = 'START_LISTENING',
  STOP_LISTENING = 'STOP_LISTENING',
  AUDIO_DATA = 'AUDIO_DATA',
  SPEECH_RECOGNITION = 'SPEECH_RECOGNITION',
  
  // 语音合成
  START_SPEAKING = 'START_SPEAKING',
  STOP_SPEAKING = 'STOP_SPEAKING',
  AUDIO_GENERATED = 'AUDIO_GENERATED',
  
  // 状态更新
  STATUS_UPDATE = 'STATUS_UPDATE',
  
  // 系统消息
  SYSTEM = 'SYSTEM',
  ERROR = 'ERROR'
}

export interface BaseMessage {
  type: MessageType;
  content?: string;
  timestamp: string;
  client_id: string;
  data?: Record<string, any>;
}

export interface ChatMessage extends BaseMessage {
  type: MessageType.CHAT;
  content: string;
}

export interface LLMResponseMessage extends BaseMessage {
  type: MessageType.LLM_RESPONSE;
  content: string;
  data: {
    model?: string;
    tokens_used?: number;
    processing_time?: number;
    provider?: string;
  };
}

export interface AudioDataMessage extends BaseMessage {
  type: MessageType.AUDIO_DATA;
  data: {
    audio_data: string; // base64 encoded
    format: string;
    sample_rate: number;
    channels: number;
  };
}

export interface SpeechRecognitionMessage extends BaseMessage {
  type: MessageType.SPEECH_RECOGNITION;
  content: string;
  data: {
    confidence?: number;
    language?: string;
    provider?: string;
  };
}

export interface AudioGeneratedMessage extends BaseMessage {
  type: MessageType.AUDIO_GENERATED;
  data: {
    audio_data: string; // base64 encoded
    format: string;
    voice?: string;
    text: string;
    duration?: number;
    provider?: string;
  };
}

export interface StatusUpdateMessage extends BaseMessage {
  type: MessageType.STATUS_UPDATE;
  data: {
    service: 'asr' | 'tts' | 'llm';
    status: 'listening' | 'speaking' | 'processing' | 'idle' | 'stopped';
    details?: Record<string, any>;
  };
}

export interface SystemMessage extends BaseMessage {
  type: MessageType.SYSTEM;
  content: string;
  data?: {
    level: 'info' | 'warning' | 'error';
    code?: string;
  };
}

export interface ErrorMessage extends BaseMessage {
  type: MessageType.ERROR;
  content: string;
  data: {
    error_code: string;
    details?: Record<string, any>;
  };
}

export type Message = 
  | BaseMessage
  | ChatMessage
  | LLMResponseMessage
  | AudioDataMessage
  | SpeechRecognitionMessage
  | AudioGeneratedMessage
  | StatusUpdateMessage
  | SystemMessage
  | ErrorMessage;

// 消息创建工厂函数
export const createMessage = {
  chat: (content: string, clientId: string): ChatMessage => ({
    type: MessageType.CHAT,
    content,
    timestamp: new Date().toISOString(),
    client_id: clientId
  }),

  startListening: (clientId: string): BaseMessage => ({
    type: MessageType.START_LISTENING,
    timestamp: new Date().toISOString(),
    client_id: clientId
  }),

  stopListening: (clientId: string): BaseMessage => ({
    type: MessageType.STOP_LISTENING,
    timestamp: new Date().toISOString(),
    client_id: clientId
  }),

  audioData: (audioData: string, format: string, sampleRate: number, channels: number, clientId: string): AudioDataMessage => ({
    type: MessageType.AUDIO_DATA,
    timestamp: new Date().toISOString(),
    client_id: clientId,
    data: {
      audio_data: audioData,
      format,
      sample_rate: sampleRate,
      channels
    }
  }),

  startSpeaking: (text: string, clientId: string): BaseMessage => ({
    type: MessageType.START_SPEAKING,
    content: text,
    timestamp: new Date().toISOString(),
    client_id: clientId
  }),

  stopSpeaking: (clientId: string): BaseMessage => ({
    type: MessageType.STOP_SPEAKING,
    timestamp: new Date().toISOString(),
    client_id: clientId
  }),

  heartbeat: (clientId: string): BaseMessage => ({
    type: MessageType.HEARTBEAT,
    content: 'ping',
    timestamp: new Date().toISOString(),
    client_id: clientId
  })
};

// 消息验证函数
export const validateMessage = (message: any): message is Message => {
  return (
    message &&
    typeof message === 'object' &&
    typeof message.type === 'string' &&
    Object.values(MessageType).includes(message.type) &&
    typeof message.timestamp === 'string' &&
    typeof message.client_id === 'string'
  );
};

// 错误代码枚举
export enum ErrorCode {
  INVALID_MESSAGE_FORMAT = 'INVALID_MESSAGE_FORMAT',
  MISSING_CLIENT_ID = 'MISSING_CLIENT_ID',
  RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED',
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE',
  AUDIO_PROCESSING_ERROR = 'AUDIO_PROCESSING_ERROR',
  LLM_ERROR = 'LLM_ERROR',
  ASR_ERROR = 'ASR_ERROR',
  TTS_ERROR = 'TTS_ERROR',
  CONNECTION_ERROR = 'CONNECTION_ERROR',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}