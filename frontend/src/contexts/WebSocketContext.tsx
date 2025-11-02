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
import { BaseMessage, MessageType } from '../types/message';

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
    }
  }, [maxMessages]);

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
    setSpeaking
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