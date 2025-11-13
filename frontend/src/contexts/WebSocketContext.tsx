/**
 * WebSocket 上下文
 * 提供全局 WebSocket 连接状态和消息管理
 */

import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';
import { 
  WebSocketManager, 
  ConnectionState, 
  ConnectionStats,
  websocketManager 
} from '../utils/websocketUtils';
import { BaseMessage, MessageType, AudioGeneratedMessage } from '../types/message';
import { audioQueuePlayer, AudioQueueItem, PlayerState } from '../utils/audioQueuePlayer';

interface WebSocketContextType {
  // 连接状态
  connectionState: ConnectionState;
  clientId: string | null;
  stats: ConnectionStats;
  isConnected: boolean;
  
  // 消息管理
  messages: BaseMessage[];
  lastMessage: BaseMessage | null;
  
  // 连接控制
  connect: () => Promise<void>;
  disconnect: () => void;
  
  // 消息发送
  sendMessage: (message: BaseMessage) => boolean;
  sendChatMessage: (content: string) => boolean;
  sendAudioData: (audioData: string, format?: string) => boolean;
  sendRealtimeAudioChunk: (audioData: string, format?: string, sampleRate?: number, channels?: number) => boolean;
  sendControlMessage: (type: MessageType, data?: any) => boolean;
  
  // 消息管理
  clearMessages: () => void;
  getMessagesByType: (type: MessageType) => BaseMessage[];
  
  // 语音控制状态
  isListening: boolean;
  isSpeaking: boolean;
  setListening: (listening: boolean) => void;
  setSpeaking: (speaking: boolean) => void;
  
  // 音频播放队列
  audioQueueLength: number;
  currentAudioItem: AudioQueueItem | null;
  audioPlayerState: PlayerState;
  stopAudioPlayback: () => void;
  skipCurrentAudio: () => void;
  clearAudioQueue: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
  autoConnect?: boolean;
  maxMessages?: number;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ 
  children, 
  autoConnect = true,
  maxMessages = 1000 
}) => {
  // 连接状态
  const [connectionState, setConnectionState] = useState<ConnectionState>(ConnectionState.DISCONNECTED);
  const [clientId, setClientId] = useState<string | null>(null);
  const [stats, setStats] = useState<ConnectionStats>({
    messagesSent: 0,
    messagesReceived: 0,
    reconnectAttempts: 0,
    totalReconnects: 0
  });

  // 消息状态
  const [messages, setMessages] = useState<BaseMessage[]>([]);
  const [lastMessage, setLastMessage] = useState<BaseMessage | null>(null);

  // 语音控制状态
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  // 音频播放队列状态
  const [audioQueueLength, setAudioQueueLength] = useState(0);
  const [currentAudioItem, setCurrentAudioItem] = useState<AudioQueueItem | null>(null);
  const [audioPlayerState, setAudioPlayerState] = useState<PlayerState>(PlayerState.IDLE);

  // 消息处理器
  const handleMessage = useCallback((message: BaseMessage) => {
    setLastMessage(message);
    
    // 更新消息列表
    setMessages(prev => {
      const newMessages = [...prev, message];
      // 限制消息数量
      if (newMessages.length > maxMessages) {
        return newMessages.slice(-maxMessages);
      }
      return newMessages;
    });

    // 处理特殊消息类型
    switch (message.type) {
      case MessageType.CONNECTION_ESTABLISHED:
        setClientId(message.data?.client_id || null);
        break;
        
      case MessageType.START_LISTENING:
        setIsListening(true);
        break;
        
      case MessageType.STOP_LISTENING:
        setIsListening(false);
        break;
        
      case MessageType.START_SPEAKING:
        setIsSpeaking(true);
        break;
        
      case MessageType.STOP_SPEAKING:
        setIsSpeaking(false);
        break;
        
      case MessageType.STATUS_UPDATE:
        if (message.data?.asr_active !== undefined) {
          setIsListening(message.data.asr_active);
        }
        if (message.data?.tts_active !== undefined) {
          setIsSpeaking(message.data.tts_active);
        }
        break;
      
      case MessageType.AUDIO_GENERATED:
        // 处理音频生成消息，加入播放队列
        handleAudioGenerated(message as AudioGeneratedMessage);
        break;
    }
  }, [maxMessages]);

  // 处理音频生成消息
  const handleAudioGenerated = useCallback(async (message: AudioGeneratedMessage) => {
    try {
      const audioData = message.data?.audio_data;
      const format = message.data?.format || 'mp3';
      const text = message.data?.text || '';
      const voice = message.data?.voice;

      if (!audioData) {
        console.warn('⚠️ 收到的音频数据为空');
        return;
      }

      console.log(`📥 收到音频数据: ${text.substring(0, 50)}... (格式: ${format})`);

      // 将音频加入播放队列
      await audioQueuePlayer.enqueue({
        audioData,
        format,
        text,
        voice
      });
    } catch (error) {
      console.error('❌ 处理音频生成消息失败:', error);
    }
  }, []);

  // 连接状态处理器
  const handleStateChange = useCallback((state: ConnectionState, error?: Error) => {
    setConnectionState(state);
    
    if (error) {
      console.error('WebSocket 连接错误:', error);
      // 可以在这里添加错误通知
    }
    
    // 更新统计信息
    setStats(websocketManager.getStats());
  }, []);

  // 初始化音频队列播放器
  useEffect(() => {
    audioQueuePlayer.setCallbacks({
      onPlayStart: (item) => {
        setCurrentAudioItem(item);
        setAudioPlayerState(PlayerState.PLAYING);
        setIsSpeaking(true);
        console.log('🔊 开始播放:', item.text?.substring(0, 50) || item.id);
      },
      onPlayEnd: (item) => {
        setCurrentAudioItem(null);
        console.log('✅ 播放完成:', item.text?.substring(0, 50) || item.id);
        // 检查队列是否为空
        const status = audioQueuePlayer.getStatus();
        if (status.queueLength === 0) {
          setAudioPlayerState(PlayerState.IDLE);
          setIsSpeaking(false);
        }
      },
      onQueueUpdate: (length) => {
        setAudioQueueLength(length);
      },
      onError: (error, item) => {
        console.error('❌ 音频播放错误:', error, item);
        setCurrentAudioItem(null);
      }
    });
  }, []);

  // 初始化 WebSocket 管理器
  useEffect(() => {
    websocketManager.addMessageHandler(handleMessage);
    websocketManager.addStateHandler(handleStateChange);

    // 自动连接
    if (autoConnect) {
      websocketManager.connect();
    }

    return () => {
      websocketManager.removeMessageHandler(handleMessage);
      websocketManager.removeStateHandler(handleStateChange);
    };
  }, [handleMessage, handleStateChange, autoConnect]);

  // 定期更新统计信息
  useEffect(() => {
    const interval = setInterval(() => {
      setStats(websocketManager.getStats());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // 连接控制方法
  const connect = useCallback(async () => {
    await websocketManager.connect();
  }, []);

  const disconnect = useCallback(() => {
    websocketManager.disconnect();
    setIsListening(false);
    setIsSpeaking(false);
    // 停止音频播放
    audioQueuePlayer.stop();
  }, []);

  // 消息发送方法
  const sendMessage = useCallback((message: BaseMessage) => {
    return websocketManager.sendMessage(message);
  }, []);

  const sendChatMessage = useCallback((content: string) => {
    return websocketManager.sendChatMessage(content);
  }, []);

  const sendAudioData = useCallback((audioData: string, format: string = 'webm') => {
    return websocketManager.sendAudioData(audioData, format);
  }, []);

  // 发送实时音频块
  const sendRealtimeAudioChunk = useCallback((audioData: string, format: string = 'wav', sampleRate: number = 16000, channels: number = 1) => {
    return websocketManager.sendAudioData(audioData, format, sampleRate, channels);
  }, []);

  const sendControlMessage = useCallback((type: MessageType, data?: any) => {
    return websocketManager.sendControlMessage(type, data);
  }, []);

  // 消息管理方法
  const clearMessages = useCallback(() => {
    setMessages([]);
    setLastMessage(null);
  }, []);

  const getMessagesByType = useCallback((type: MessageType) => {
    return messages.filter(msg => msg.type === type);
  }, [messages]);

  // 语音控制方法
  const setListening = useCallback((listening: boolean) => {
    if (listening !== isListening) {
      const messageType = listening ? MessageType.START_LISTENING : MessageType.STOP_LISTENING;
      sendControlMessage(messageType);
    }
  }, [isListening, sendControlMessage]);

  const setSpeaking = useCallback((speaking: boolean) => {
    if (speaking !== isSpeaking) {
      const messageType = speaking ? MessageType.START_SPEAKING : MessageType.STOP_SPEAKING;
      sendControlMessage(messageType);
    }
  }, [isSpeaking, sendControlMessage]);

  // 音频播放控制方法
  const stopAudioPlayback = useCallback(() => {
    audioQueuePlayer.stop();
    setAudioPlayerState(PlayerState.STOPPED);
    setIsSpeaking(false);
  }, []);

  const skipCurrentAudio = useCallback(() => {
    audioQueuePlayer.skip();
  }, []);

  const clearAudioQueue = useCallback(() => {
    audioQueuePlayer.clearQueue();
  }, []);

  const contextValue: WebSocketContextType = {
    // 连接状态
    connectionState,
    clientId,
    stats,
    isConnected: connectionState === ConnectionState.CONNECTED,
    
    // 消息管理
    messages,
    lastMessage,
    
    // 连接控制
    connect,
    disconnect,
    
    // 消息发送
    sendMessage,
    sendChatMessage,
    sendAudioData,
    sendRealtimeAudioChunk,
    sendControlMessage,
    
    // 消息管理
    clearMessages,
    getMessagesByType,
    
    // 语音控制状态
    isListening,
    isSpeaking,
    setListening,
    setSpeaking,
    
    // 音频播放队列
    audioQueueLength,
    currentAudioItem,
    audioPlayerState,
    stopAudioPlayback,
    skipCurrentAudio,
    clearAudioQueue
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
};

// Hook for using WebSocket context
export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// Hook for connection status
export const useConnectionStatus = () => {
  const { connectionState, isConnected, stats } = useWebSocket();
  return { connectionState, isConnected, stats };
};

// Hook for messaging
export const useMessaging = () => {
  const { 
    messages, 
    lastMessage, 
    sendMessage, 
    sendChatMessage, 
    clearMessages, 
    getMessagesByType 
  } = useWebSocket();
  
  return {
    messages,
    lastMessage,
    sendMessage,
    sendChatMessage,
    clearMessages,
    getMessagesByType
  };
};

// Hook for voice control
export const useVoiceControl = () => {
  const { 
    isListening, 
    isSpeaking, 
    setListening, 
    setSpeaking, 
    sendAudioData,
    sendRealtimeAudioChunk
  } = useWebSocket();
  
  return {
    isListening,
    isSpeaking,
    setListening,
    setSpeaking,
    sendAudioData,
    sendRealtimeAudioChunk
  };
};