/**
 * 前端 WebSocket 连接管理工具
 * 提供连接管理、消息发送、重连机制等功能
 */

import { BaseMessage, MessageType, createMessage, validateMessage } from '../types/message';

export interface WebSocketConfig {
  url: string;
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  connectionTimeout: number;
}

export const DEFAULT_WEBSOCKET_CONFIG: WebSocketConfig = {
  url: 'ws://localhost:8000/ws',
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
  heartbeatInterval: 30000,
  connectionTimeout: 10000
};

export enum ConnectionState {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error'
}

export interface ConnectionStats {
  connectedAt?: Date;
  lastMessageAt?: Date;
  messagesSent: number;
  messagesReceived: number;
  reconnectAttempts: number;
  totalReconnects: number;
}

export type MessageHandler = (message: BaseMessage) => void;
export type ConnectionStateHandler = (state: ConnectionState, error?: Error) => void;

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private state: ConnectionState = ConnectionState.DISCONNECTED;
  private clientId: string | null = null;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private connectionTimer: NodeJS.Timeout | null = null;
  private stats: ConnectionStats = {
    messagesSent: 0,
    messagesReceived: 0,
    reconnectAttempts: 0,
    totalReconnects: 0
  };

  private messageHandlers: Set<MessageHandler> = new Set();
  private stateHandlers: Set<ConnectionStateHandler> = new Set();

  constructor(config: Partial<WebSocketConfig> = {}) {
    this.config = { ...DEFAULT_WEBSOCKET_CONFIG, ...config };
  }

  // 连接管理
  async connect(): Promise<void> {
    if (this.state === ConnectionState.CONNECTING || this.state === ConnectionState.CONNECTED) {
      console.warn('⚠️ WebSocket 已连接或正在连接中');
      return;
    }

    this.setState(ConnectionState.CONNECTING);
    console.log('🔌 正在连接 WebSocket...', this.config.url);

    try {
      this.ws = new WebSocket(this.config.url);
      this.setupEventListeners();
      
      // 设置连接超时
      this.connectionTimer = setTimeout(() => {
        if (this.state === ConnectionState.CONNECTING) {
          this.handleConnectionError(new Error('连接超时'));
        }
      }, this.config.connectionTimeout);

    } catch (error) {
      this.handleConnectionError(error as Error);
    }
  }

  disconnect(): void {
    console.log('🔌 断开 WebSocket 连接');
    this.cleanup();
    this.setState(ConnectionState.DISCONNECTED);
  }

  // 消息发送
  sendMessage(message: BaseMessage): boolean {
    if (this.state !== ConnectionState.CONNECTED || !this.ws) {
      console.warn('⚠️ WebSocket 未连接，无法发送消息');
      return false;
    }

    try {
      // 验证消息格式
      if (!validateMessage(message)) {
        console.error('❌ 消息格式验证失败:', message);
        return false;
      }

      // 添加客户端ID
      const messageWithClientId = {
        ...message,
        client_id: this.clientId,
        timestamp: new Date().toISOString()
      };

      const messageStr = JSON.stringify(messageWithClientId);
      this.ws.send(messageStr);
      
      this.stats.messagesSent++;
      console.log('📤 发送消息:', message.type, messageWithClientId);
      
      return true;
    } catch (error) {
      console.error('❌ 发送消息失败:', error);
      return false;
    }
  }

  // 便捷方法
  sendChatMessage(content: string): boolean {
    return this.sendMessage(createMessage.chat(content, this.clientId || ''));
  }

  sendAudioData(audioData: string, format: string = 'webm', sampleRate: number = 44100, channels: number = 1): boolean {
    return this.sendMessage(createMessage.audioData(audioData, format, sampleRate, channels, this.clientId || ''));
  }

  sendControlMessage(type: MessageType, data?: any): boolean {
    const message: BaseMessage = {
      type,
      content: '',
      timestamp: new Date().toISOString(),
      client_id: this.clientId || '',
      data
    };
    return this.sendMessage(message);
  }

  // 事件监听器管理
  addMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.add(handler);
  }

  removeMessageHandler(handler: MessageHandler): void {
    this.messageHandlers.delete(handler);
  }

  addStateHandler(handler: ConnectionStateHandler): void {
    this.stateHandlers.add(handler);
  }

  removeStateHandler(handler: ConnectionStateHandler): void {
    this.stateHandlers.delete(handler);
  }

  // 状态获取
  getState(): ConnectionState {
    return this.state;
  }

  getClientId(): string | null {
    return this.clientId;
  }

  getStats(): ConnectionStats {
    return { ...this.stats };
  }

  isConnected(): boolean {
    return this.state === ConnectionState.CONNECTED;
  }

  // 私有方法
  private setupEventListeners(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('✅ WebSocket 连接成功');
      this.clearConnectionTimer();
      this.setState(ConnectionState.CONNECTED);
      this.stats.connectedAt = new Date();
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: BaseMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('❌ 解析消息失败:', error, event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log('🔌 WebSocket 连接关闭:', event.code, event.reason);
      this.cleanup();
      
      if (event.code !== 1000 && this.state !== ConnectionState.DISCONNECTED) {
        // 非正常关闭，尝试重连
        this.handleConnectionError(new Error(`连接关闭: ${event.reason || '未知原因'}`));
      } else {
        this.setState(ConnectionState.DISCONNECTED);
      }
    };

    this.ws.onerror = (error) => {
      console.error('❌ WebSocket 错误:', error);
      this.handleConnectionError(new Error('WebSocket 连接错误'));
    };
  }

  private handleMessage(message: BaseMessage): void {
    this.stats.messagesReceived++;
    this.stats.lastMessageAt = new Date();

    // 处理特殊消息类型
    if (message.type === MessageType.CONNECTION_ESTABLISHED) {
      this.clientId = message.data?.client_id || null;
      console.log('🆔 获得客户端ID:', this.clientId);
    }

    // 通知所有消息处理器
    this.messageHandlers.forEach(handler => {
      try {
        handler(message);
      } catch (error) {
        console.error('❌ 消息处理器错误:', error);
      }
    });

    console.log('📥 收到消息:', message.type, message);
  }

  private handleConnectionError(error: Error): void {
    console.error('❌ 连接错误:', error.message);
    this.cleanup();
    
    if (this.reconnectAttempts < this.config.maxReconnectAttempts) {
      this.setState(ConnectionState.RECONNECTING);
      this.scheduleReconnect();
    } else {
      console.error('❌ 重连次数已达上限，停止重连');
      this.setState(ConnectionState.ERROR, error);
    }
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    this.stats.reconnectAttempts++;
    
    const delay = this.config.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
    console.log(`🔄 ${delay}ms 后尝试第 ${this.reconnectAttempts} 次重连...`);
    
    this.reconnectTimer = setTimeout(() => {
      this.stats.totalReconnects++;
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(() => {
      if (this.state === ConnectionState.CONNECTED) {
        this.sendControlMessage(MessageType.HEARTBEAT);
      }
    }, this.config.heartbeatInterval);
  }

  private setState(newState: ConnectionState, error?: Error): void {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;
      console.log(`🔄 连接状态变更: ${oldState} -> ${newState}`);
      
      // 通知状态变更处理器
      this.stateHandlers.forEach(handler => {
        try {
          handler(newState, error);
        } catch (err) {
          console.error('❌ 状态处理器错误:', err);
        }
      });
    }
  }

  private cleanup(): void {
    this.clearConnectionTimer();
    this.clearReconnectTimer();
    this.clearHeartbeatTimer();
    
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.close(1000, '正常关闭');
      }
      this.ws = null;
    }
  }

  private clearConnectionTimer(): void {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearHeartbeatTimer(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
}

// 单例 WebSocket 管理器
export const websocketManager = new WebSocketManager();

// 工具函数
export const websocketUtils = {
  // 检查 WebSocket 支持
  checkWebSocketSupport(): boolean {
    return 'WebSocket' in window;
  },

  // 获取连接状态描述
  getStateDescription(state: ConnectionState): string {
    const descriptions = {
      [ConnectionState.DISCONNECTED]: '未连接',
      [ConnectionState.CONNECTING]: '连接中',
      [ConnectionState.CONNECTED]: '已连接',
      [ConnectionState.RECONNECTING]: '重连中',
      [ConnectionState.ERROR]: '连接错误'
    };
    return descriptions[state];
  },

  // 格式化连接统计信息
  formatStats(stats: ConnectionStats): string {
    const lines = [
      `连接时间: ${stats.connectedAt?.toLocaleString() || '未连接'}`,
      `最后消息: ${stats.lastMessageAt?.toLocaleString() || '无'}`,
      `发送消息: ${stats.messagesSent}`,
      `接收消息: ${stats.messagesReceived}`,
      `重连次数: ${stats.totalReconnects}`
    ];
    return lines.join('\n');
  }
};