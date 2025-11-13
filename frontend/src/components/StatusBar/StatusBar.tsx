import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import { useConnectionStatus, useVoiceControl, useWebSocket } from '../../contexts/WebSocketContext';
import { websocketUtils } from '../../utils/websocketUtils';
import { PlayerState } from '../../utils/audioQueuePlayer';

const StatusContainer = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 12px;
  height: 32px;
  user-select: none;
`;

const LeftSection = styled.div`
  display: flex;
  align-items: center;
  gap: 16px;
`;

const RightSection = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
`;

const StatusItem = styled.div<{ status?: 'active' | 'inactive' | 'connected' | 'disconnected' | 'connecting' | 'error' }>`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.1);
  transition: all 0.3s ease;
  
  &::before {
    content: '';
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: ${props => {
      switch (props.status) {
        case 'active':
        case 'connected':
          return '#4CAF50';
        case 'connecting':
          return '#FF9800';
        case 'inactive':
        case 'disconnected':
          return '#f44336';
        case 'error':
          return '#f44336';
        default:
          return '#9E9E9E';
      }
    }};
    animation: ${props => props.status === 'connecting' ? 'pulse 1s infinite' : 'none'};
  }

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const TimeDisplay = styled.div`
  font-family: 'Courier New', monospace;
  font-weight: 600;
  min-width: 80px;
  text-align: center;
`;

const WindowControls = styled.div`
  display: flex;
  gap: 8px;
`;

const AppInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  opacity: 0.8;
`;

const StatsInfo = styled.div`
  font-size: 10px;
  opacity: 0.7;
  cursor: help;
  
  &:hover {
    opacity: 1;
  }
`;

const WindowButton = styled.button<{ variant: 'minimize' | 'maximize' | 'close' }>`
  width: 12px;
  height: 12px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s ease;
  
  background: ${props => {
    switch (props.variant) {
      case 'minimize': return '#FFBD2E';
      case 'maximize': return '#28CA42';
      case 'close': return '#FF5F56';
      default: return '#9E9E9E';
    }
  }};

  &:hover {
    opacity: 0.8;
    transform: scale(1.1);
  }

  &:active {
    transform: scale(0.9);
  }
`;

const StatusBar: React.FC = () => {
  const [currentTime, setCurrentTime] = useState(new Date());
  const { connectionState, isConnected, stats } = useConnectionStatus();
  const { isListening, isSpeaking } = useVoiceControl();
  const { audioQueueLength, audioPlayerState, currentAudioItem } = useWebSocket();

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const handleMinimize = () => {
    if (window.electronAPI) {
      window.electronAPI.minimizeWindow();
    }
  };

  const handleMaximize = () => {
    if (window.electronAPI) {
      window.electronAPI.maximizeWindow();
    }
  };

  const handleClose = () => {
    if (window.electronAPI) {
      window.electronAPI.closeWindow();
    }
  };

  const getConnectionStatusForDisplay = () => {
    switch (connectionState) {
      case 'connected': return 'connected';
      case 'connecting': return 'connecting';
      case 'reconnecting': return 'connecting';
      case 'disconnected': return 'disconnected';
      case 'error': return 'error';
      default: return 'inactive';
    }
  };

  return (
    <StatusContainer>
      <LeftSection>
        <AppInfo>
          🌙 Luna-Aster
        </AppInfo>
        
        <StatusItem status={getConnectionStatusForDisplay()}>
          {websocketUtils.getStateDescription(connectionState)}
        </StatusItem>
        
        <StatusItem status={isListening ? 'active' : 'inactive'}>
          ASR {isListening ? '🎤' : '🔇'}
        </StatusItem>
        
        <StatusItem status={isSpeaking ? 'active' : 'inactive'}>
          TTS {isSpeaking ? '🔊' : '🔇'}
        </StatusItem>
        
        <StatusItem status={audioQueueLength > 0 ? 'active' : 'inactive'}>
          队列 {audioQueueLength > 0 ? `${audioQueueLength}` : '0'}
        </StatusItem>

        {isConnected && (
          <StatsInfo title={websocketUtils.formatStats(stats)}>
            📊 发送:{stats.messagesSent} 接收:{stats.messagesReceived}
          </StatsInfo>
        )}
        
        {currentAudioItem && (
          <StatsInfo title={currentAudioItem.text}>
            🎵 {currentAudioItem.text?.substring(0, 20) || '播放中'}...
          </StatsInfo>
        )}
      </LeftSection>

      <RightSection>
        <TimeDisplay>
          {currentTime.toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })}
        </TimeDisplay>
        
        <WindowControls>
          <WindowButton 
            variant="minimize" 
            onClick={handleMinimize}
            title="最小化"
          />
          <WindowButton 
            variant="maximize" 
            onClick={handleMaximize}
            title="最大化"
          />
          <WindowButton 
            variant="close" 
            onClick={handleClose}
            title="关闭"
          />
        </WindowControls>
      </RightSection>
    </StatusContainer>
  );
};

export default StatusBar;