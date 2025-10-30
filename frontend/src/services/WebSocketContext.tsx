import React, { createContext, useContext, useEffect, useState, useCallback, ReactNode } from 'react';

export interface WebSocketMessage {
  type: string;
  content?: string;
  data?: any;
  timestamp: number;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WebSocketContextType {
  connectionStatus: ConnectionStatus;
  sendMessage: (message: WebSocketMessage) => void;
  lastMessage: WebSocketMessage | null;
  connect: () => void;
  disconnect: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
}

export const WebSocketProvider: React.FC<WebSocketProviderProps> = ({ children }) => {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  const maxReconnectAttempts = 5;
  const reconnectInterval = 3000;

  const getWebSocketUrl = useCallback(() => {
    // 尝试从 Electron API 获取后端地址
    if (window.wsAPI?.getBackendUrl) {
      return window.wsAPI.getBackendUrl();
    }
    // 默认地址
    return 'ws://localhost:8765';
  }, []);

  const connect = useCallback(() => {
    if (ws?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionStatus('connecting');
    
    try {
      const websocket = new WebSocket(getWebSocketUrl());
      
      websocket.onopen = () => {
        console.log('WebSocket 连接已建立');
        setConnectionStatus('connected');
        setReconnectAttempts(0);
        setWs(websocket);
        
        // 发送连接确认消息
        websocket.send(JSON.stringify({
          type: 'connection_established',
          timestamp: Date.now()
        }));
      };

      websocket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setLastMessage(message);
          console.log('收到消息:', message);
        } catch (error) {
          console.error('解析消息失败:', error);
        }
      };

      websocket.onclose = (event) => {
        console.log('WebSocket 连接已关闭:', event.code, event.reason);
        setConnectionStatus('disconnected');
        setWs(null);
        
        // 自动重连
        if (reconnectAttempts < maxReconnectAttempts) {
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, reconnectInterval);
        }
      };

      websocket.onerror = (error) => {
        console.error('WebSocket 错误:', error);
        setConnectionStatus('error');
      };

    } catch (error) {
      console.error('创建 WebSocket 连接失败:', error);
      setConnectionStatus('error');
    }
  }, [ws, getWebSocketUrl, reconnectAttempts]);

  const disconnect = useCallback(() => {
    if (ws) {
      ws.close();
      setWs(null);
      setConnectionStatus('disconnected');
    }
  }, [ws]);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (ws?.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(message));
        console.log('发送消息:', message);
      } catch (error) {
        console.error('发送消息失败:', error);
      }
    } else {
      console.warn('WebSocket 未连接，无法发送消息');
    }
  }, [ws]);

  useEffect(() => {
    // 组件挂载时自动连接
    connect();
    
    // 组件卸载时断开连接
    return () => {
      disconnect();
    };
  }, []);

  // 监听网络状态变化
  useEffect(() => {
    const handleOnline = () => {
      if (connectionStatus === 'disconnected') {
        connect();
      }
    };

    const handleOffline = () => {
      setConnectionStatus('disconnected');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [connectionStatus, connect]);

  const value: WebSocketContextType = {
    connectionStatus,
    sendMessage,
    lastMessage,
    connect,
    disconnect
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = (): WebSocketContextType => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};

// 扩展 Window 接口以支持 Electron API
declare global {
  interface Window {
    electronAPI?: {
      getAppVersion: () => Promise<string>;
      minimizeWindow: () => Promise<void>;
      maximizeWindow: () => Promise<void>;
      closeWindow: () => Promise<void>;
      platform: string;
    };
    wsAPI?: {
      getBackendUrl: () => string;
    };
  }
}