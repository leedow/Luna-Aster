import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { useMessaging, useConnectionStatus } from '../../contexts/WebSocketContext';
import { MessageType } from '../../types/message';
import { useVideoCapture } from '../../contexts/VideoCaptureContext';

interface DisplayMessage {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'error';
  content: string;
  timestamp: Date;
}

interface DisplayItem {
  id: string;
  kind: 'text' | 'image';
  type: 'user' | 'assistant' | 'system' | 'error';
  content?: string;
  imageUrl?: string;
  timestamp: Date;
}

const ChatContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100%;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  margin: 10px;
  overflow: hidden;
`;

const ChatHeader = styled.div`
  padding: 15px 20px;
  background: rgba(255, 255, 255, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  font-weight: 600;
  font-size: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const ConnectionIndicator = styled.div<{ connected: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  opacity: 0.8;

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${props => props.connected ? '#4CAF50' : '#f44336'};
    animation: ${props => props.connected ? 'pulse 2s infinite' : 'none'};
  }

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const MessagesContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 3px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.3);
    border-radius: 3px;
  }
`;

const MessageBubble = styled.div<{ messageType: string }>`
  max-width: 80%;
  padding: 12px 16px;
  border-radius: 18px;
  background: ${props => {
    switch (props.messageType) {
      case 'user':
        return 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
      case 'assistant':
        return 'rgba(255, 255, 255, 0.15)';
      case 'system':
        return 'rgba(255, 193, 7, 0.2)';
      case 'error':
        return 'rgba(244, 67, 54, 0.2)';
      default:
        return 'rgba(255, 255, 255, 0.1)';
    }
  }};
  align-self: ${props => props.messageType === 'user' ? 'flex-end' : 'flex-start'};
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  word-wrap: break-word;
`;

const MessageContent = styled.div`
  margin-bottom: 5px;
  line-height: 1.4;
`;

const ScreenshotImage = styled.img`
  max-width: 100%;
  border-radius: 8px;
  display: block;
`;

const MessageTime = styled.div`
  font-size: 11px;
  opacity: 0.7;
  text-align: right;
`;

const InputContainer = styled.div`
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
`;

const InputWrapper = styled.div`
  display: flex;
  gap: 10px;
  align-items: flex-end;
`;

const MessageInput = styled.textarea`
  flex: 1;
  padding: 12px 16px;
  border: none;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.1);
  color: white;
  font-size: 14px;
  resize: none;
  min-height: 20px;
  max-height: 100px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);

  &::placeholder {
    color: rgba(255, 255, 255, 0.6);
  }

  &:focus {
    outline: none;
    border-color: rgba(255, 255, 255, 0.4);
    background: rgba(255, 255, 255, 0.15);
  }
`;

const SendButton = styled.button`
  padding: 12px 20px;
  border: none;
  border-radius: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }
`;

const EmptyState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  opacity: 0.6;
  text-align: center;
  gap: 10px;

  .icon {
    font-size: 48px;
  }

  .text {
    font-size: 16px;
  }

  .subtext {
    font-size: 12px;
    opacity: 0.7;
  }
`;

const ChatInterface: React.FC = () => {
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const { messages, sendChatMessage } = useMessaging();
  const { isConnected } = useConnectionStatus();
  const { capturedImages } = useVideoCapture();

  // 转换消息格式用于显示
  const displayMessages: DisplayMessage[] = messages.map(msg => ({
    id: msg.timestamp + msg.type,
    type: msg.type === MessageType.CHAT ? 'user' : 
          msg.type === MessageType.LLM_RESPONSE ? 'assistant' :
          msg.type === MessageType.SYSTEM ? 'system' :
          msg.type === MessageType.ERROR ? 'error' : 'system',
    content: msg.content || '',
    timestamp: new Date(msg.timestamp)
  }));

  const imageItems: DisplayItem[] = capturedImages.map(img => ({
    id: `img-${img.id}`,
    kind: 'image',
    type: 'system',
    imageUrl: img.dataUrl,
    timestamp: new Date(img.capturedAt)
  }));

  const textItems: DisplayItem[] = displayMessages.map(m => ({
    id: m.id,
    kind: 'text',
    type: m.type,
    content: m.content,
    timestamp: m.timestamp
  }));

  const combinedItems: DisplayItem[] = [...textItems, ...imageItems]
    .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [combinedItems]);

  const handleSendMessage = () => {
    if (inputValue.trim() && isConnected) {
      sendChatMessage(inputValue.trim());
      setInputValue('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <ChatContainer>
      <ChatHeader>
        <span>💬 对话界面</span>
        <ConnectionIndicator connected={isConnected}>
          {isConnected ? '已连接' : '未连接'}
        </ConnectionIndicator>
      </ChatHeader>
      
      <MessagesContainer>
        {combinedItems.length === 0 ? (
          <EmptyState>
            <div className="icon">🌙</div>
            <div className="text">欢迎使用 Luna-Aster</div>
            <div className="subtext">
              {isConnected ? '开始对话吧！' : '等待连接到服务器...'}
            </div>
          </EmptyState>
        ) : (
          combinedItems.map((item) => (
            <MessageBubble key={item.id} messageType={item.type}>
              {item.kind === 'image' ? (
                <>
                  <ScreenshotImage src={item.imageUrl} alt="自动截图" />
                  <MessageTime>
                    {item.timestamp.toLocaleTimeString()}
                  </MessageTime>
                </>
              ) : (
                <>
                  <MessageContent>{item.content}</MessageContent>
                  <MessageTime>
                    {item.timestamp.toLocaleTimeString()}
                  </MessageTime>
                </>
              )}
            </MessageBubble>
          ))
        )}
        <div ref={messagesEndRef} />
      </MessagesContainer>

      <InputContainer>
        <InputWrapper>
          <MessageInput
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={isConnected ? "输入消息..." : "等待连接..."}
            rows={1}
            disabled={!isConnected}
          />
          <SendButton 
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || !isConnected}
          >
            发送
          </SendButton>
        </InputWrapper>
      </InputContainer>
    </ChatContainer>
  );
};

export default ChatInterface;