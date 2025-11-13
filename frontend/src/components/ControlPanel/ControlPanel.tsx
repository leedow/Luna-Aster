import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { useWebSocket, useVoiceControl, useConnectionStatus } from '../../contexts/WebSocketContext';
import { AudioRecorder, audioUtils, AudioChunk } from '../../utils/audioUtils';
import { websocketUtils } from '../../utils/websocketUtils';
import VideoInputControl from './VideoInputControl';

const ControlContainer = styled.div`
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 10px;
  margin: 10px;
  height: calc(100vh - 120px);
  overflow-y: auto;
`;

const ControlSection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const SectionTitle = styled.h3`
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 8px;
`;

const ControlButton = styled.button<{ active?: boolean; variant?: 'primary' | 'secondary' | 'danger' }>`
  padding: 12px 20px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  
  background: ${props => {
    if (props.active) {
      return props.variant === 'danger' 
        ? 'linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%)'
        : 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)';
    }
    return 'rgba(255, 255, 255, 0.1)';
  }};
  
  color: white;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
    background: ${props => {
      if (props.active) {
        return props.variant === 'danger' 
          ? 'linear-gradient(135deg, #ff5252 0%, #d32f2f 100%)'
          : 'linear-gradient(135deg, #26a69a 0%, #00695c 100%)';
      }
      return 'rgba(255, 255, 255, 0.2)';
    }};
  }

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }
`;

const StatusIndicator = styled.div<{ status: string }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  background: rgba(255, 255, 255, 0.1);
  
  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: ${props => {
      switch (props.status) {
        case 'connected': return '#4CAF50';
        case 'connecting': return '#FF9800';
        case 'reconnecting': return '#FF9800';
        case 'disconnected': return '#f44336';
        case 'error': return '#f44336';
        default: return '#9E9E9E';
      }
    }};
    animation: ${props => (props.status === 'connecting' || props.status === 'reconnecting') ? 'pulse 1s infinite' : 'none'};
  }

  @keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
  }
`;

const StatsContainer = styled.div`
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  padding: 10px;
  font-size: 11px;
  line-height: 1.4;
  opacity: 0.8;
`;

const AudioVisualizer = styled.canvas`
  width: 100%;
  height: 60px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.1);
`;

const VoiceIndicator = styled.div<{ active: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  background: ${props => props.active ? 'rgba(76, 175, 80, 0.2)' : 'rgba(255, 255, 255, 0.1)'};
  border: 1px solid ${props => props.active ? 'rgba(76, 175, 80, 0.5)' : 'rgba(255, 255, 255, 0.2)'};
  
  &::before {
    content: '${props => props.active ? '🎤' : '🔇'}';
    font-size: 14px;
  }
`;

const ControlPanel: React.FC = () => {
  const [audioRecorder] = useState(() => new AudioRecorder());
  const [isMonitoring, setIsMonitoring] = useState(false); // 新增：声音监听状态
  const [audioSupport, setAudioSupport] = useState(audioUtils.checkAudioSupport());
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const { connect, disconnect, clearMessages } = useWebSocket();
  const { connectionState, isConnected, stats } = useConnectionStatus();
  const { isListening, isSpeaking, setListening, setSpeaking, sendRealtimeAudioChunk } = useVoiceControl();

  // 检查音频支持
  useEffect(() => {
    setAudioSupport(audioUtils.checkAudioSupport());
  }, []);

  // 设置音频录制器回调
  useEffect(() => {
    // 设置实时音频块回调
    audioRecorder.setRealtimeAudioChunkCallback((chunk: AudioChunk) => {
      if (isMonitoring && isConnected) {
        // 将ArrayBuffer转换为base64
        const base64Data = arrayBufferToBase64(chunk.audioData);
        // 发送实时音频数据到服务器（PCM格式，16-bit，16kHz，单声道）
        sendRealtimeAudioChunk(base64Data, 'pcm', 16000, 1);
      }
    });

    // 设置监听状态回调
    audioRecorder.setListeningCallbacks({
      onListeningStart: () => {
        console.log('🎤 开始声音监听');
        setIsMonitoring(true);
        setListening(true);
      },
      onListeningStop: () => {
        console.log('🔇 停止声音监听');
        setIsMonitoring(false);
        setListening(false);
      }
    });
  }, [audioRecorder, isMonitoring, isConnected, sendRealtimeAudioChunk, setListening]);

  // ArrayBuffer转base64的辅助函数
  const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  // 处理声音监听
  const handleStartMonitoring = async () => {
    if (!audioSupport.recording) {
      alert('您的浏览器不支持音频录制功能');
      return;
    }

    try {
      await audioRecorder.startListening();
      console.log('✅ 声音监听已启动');
    } catch (error) {
      console.error('启动声音监听失败:', error);
      alert('无法启动声音监听，请检查麦克风权限');
    }
  };

  const handleStopMonitoring = async () => {
    if (!isMonitoring) return;

    try {
      audioRecorder.stopListening();
      console.log('✅ 声音监听已停止');
    } catch (error) {
      console.error('停止声音监听失败:', error);
    }
  };

  const handleToggleMonitoring = () => {
    if (isMonitoring) {
      handleStopMonitoring();
    } else {
      handleStartMonitoring();
    }
  };

  const handleToggleSpeaking = () => {
    setSpeaking(!isSpeaking);
  };

  const handleConnect = () => {
    if (isConnected) {
      disconnect();
    } else {
      connect();
    }
  };

  const handleClearMessages = () => {
    if (window.confirm('确定要清空所有消息吗？')) {
      clearMessages();
    }
  };

  return (
    <ControlContainer>
      <ControlSection>
        <SectionTitle>🔗 连接状态</SectionTitle>
        <StatusIndicator status={connectionState}>
          {websocketUtils.getStateDescription(connectionState)}
        </StatusIndicator>
        <ControlButton 
          onClick={handleConnect}
          variant={isConnected ? 'danger' : 'primary'}
        >
          {isConnected ? '断开连接' : '连接服务器'}
        </ControlButton>
      </ControlSection>

      <ControlSection>
        <SectionTitle>🎤 语音控制</SectionTitle>
        
        <VoiceIndicator active={isListening}>
          {isListening ? '正在监听...' : '未在监听'}
        </VoiceIndicator>
        
        <VoiceIndicator active={isSpeaking}>
          {isSpeaking ? '正在说话...' : '未在说话'}
        </VoiceIndicator>

        <ControlButton 
          onClick={handleToggleMonitoring}
          active={isMonitoring}
          variant={isMonitoring ? 'danger' : 'primary'}
          disabled={!isConnected || !audioSupport.recording}
        >
          {isMonitoring ? '🛑 停止监听' : '🎤 开始监听'}
        </ControlButton>

        <ControlButton 
          onClick={handleToggleSpeaking}
          active={isSpeaking}
          variant="secondary"
          disabled={!isConnected}
        >
          {isSpeaking ? '🔇 停止说话' : '🔊 开始说话'}
        </ControlButton>

        {/* 音频可视化 */}
        {isListening && (
          <AudioVisualizer 
            ref={canvasRef}
            width={260}
            height={60}
          />
        )}
      </ControlSection>

      {/* 视频输入控制：放在语音控制下面 */}
      <VideoInputControl />

      <ControlSection>
        <SectionTitle>🪄 虚拟人物悬浮窗口</SectionTitle>
        <ControlButton 
          onClick={() => {
            if ((window as any).electronAPI?.openAvatarWindow) {
              (window as any).electronAPI.openAvatarWindow();
            } else {
              alert('请在 Electron 模式下使用该功能');
            }
          }}
          variant="primary"
        >
          打开悬浮窗口
        </ControlButton>
        <ControlButton 
          onClick={() => {
            if ((window as any).electronAPI?.closeAvatarWindow) {
              (window as any).electronAPI.closeAvatarWindow();
            }
          }}
          variant="secondary"
        >
          关闭悬浮窗口
        </ControlButton>
      </ControlSection>

      <ControlSection>
        <SectionTitle>📊 统计信息</SectionTitle>
        <StatsContainer>
          {websocketUtils.formatStats(stats)}
        </StatsContainer>
      </ControlSection>

      <ControlSection>
        <SectionTitle>🔧 音频支持</SectionTitle>
        <StatsContainer>
          录音支持: {audioSupport.recording ? '✅' : '❌'}<br/>
          播放支持: {audioSupport.playback ? '✅' : '❌'}<br/>
          支持格式: {audioSupport.formats.join(', ') || '无'}<br/>
          AudioWorkletRecorder 支持: {audioSupport.audioWorklet ? '✅' : '❌'}<br/>
          MediaRecorder 支持: {audioSupport.mediaRecorder ? '✅' : '❌'}
        </StatsContainer>
      </ControlSection>

      <ControlSection>
        <SectionTitle>⚙️ 操作</SectionTitle>
        <ControlButton onClick={handleClearMessages}>
          🗑️ 清空消息
        </ControlButton>
        <ControlButton 
          onClick={() => window.location.reload()}
          variant="secondary"
        >
          🔄 重新加载
        </ControlButton>
      </ControlSection>
    </ControlContainer>
  );
};

export default ControlPanel;