import React, { useEffect, useState } from 'react';
import styled, { keyframes } from 'styled-components';

interface VirtualCharacterProps {
  isListening: boolean;
  isSpeaking: boolean;
}

const breathe = keyframes`
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
`;

const pulse = keyframes`
  0%, 100% { opacity: 0.8; }
  50% { opacity: 1; }
`;

const listening = keyframes`
  0%, 100% { transform: scale(1) rotate(0deg); }
  25% { transform: scale(1.05) rotate(1deg); }
  75% { transform: scale(1.05) rotate(-1deg); }
`;

const speaking = keyframes`
  0%, 100% { transform: scale(1); }
  25% { transform: scale(1.1); }
  50% { transform: scale(1.05); }
  75% { transform: scale(1.1); }
`;

const CharacterContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  position: relative;
`;

const CharacterAvatar = styled.div<{ isListening: boolean; isSpeaking: boolean }>`
  width: 200px;
  height: 200px;
  border-radius: 50%;
  background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
  background-size: 400% 400%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  animation: ${props => {
    if (props.isSpeaking) return speaking;
    if (props.isListening) return listening;
    return breathe;
  }} 2s ease-in-out infinite;
  
  &::before {
    content: '';
    position: absolute;
    top: -10px;
    left: -10px;
    right: -10px;
    bottom: -10px;
    border-radius: 50%;
    background: linear-gradient(45deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
    background-size: 400% 400%;
    opacity: ${props => props.isListening || props.isSpeaking ? 0.6 : 0.3};
    animation: ${pulse} 1.5s ease-in-out infinite;
    z-index: -1;
  }
`;

const CharacterFace = styled.div`
  font-size: 80px;
  color: white;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
`;

const CharacterName = styled.h2`
  margin-top: 20px;
  font-size: 24px;
  font-weight: 300;
  color: white;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
`;

const StatusIndicator = styled.div<{ isListening: boolean; isSpeaking: boolean }>`
  margin-top: 15px;
  padding: 8px 16px;
  border-radius: 20px;
  background: ${props => {
    if (props.isSpeaking) return 'rgba(255, 107, 107, 0.8)';
    if (props.isListening) return 'rgba(78, 205, 196, 0.8)';
    return 'rgba(255, 255, 255, 0.2)';
  }};
  color: white;
  font-size: 14px;
  font-weight: 500;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  transition: all 0.3s ease;
`;

const WaveContainer = styled.div<{ isActive: boolean }>`
  position: absolute;
  bottom: -50px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 3px;
  opacity: ${props => props.isActive ? 1 : 0};
  transition: opacity 0.3s ease;
`;

const WaveBar = styled.div<{ delay: number; isActive: boolean }>`
  width: 4px;
  height: 20px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 2px;
  animation: ${props => props.isActive ? `
    wave 1.5s ease-in-out infinite;
    animation-delay: ${props.delay}s;
  ` : 'none'};
  
  @keyframes wave {
    0%, 100% { height: 20px; }
    50% { height: 40px; }
  }
`;

const VirtualCharacter: React.FC<VirtualCharacterProps> = ({ isListening, isSpeaking }) => {
  const [currentEmotion, setCurrentEmotion] = useState('😊');
  
  const emotions = ['😊', '😄', '🤔', '😌', '😮', '🙂'];
  
  useEffect(() => {
    const interval = setInterval(() => {
      if (!isListening && !isSpeaking) {
        const randomEmotion = emotions[Math.floor(Math.random() * emotions.length)];
        setCurrentEmotion(randomEmotion);
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [isListening, isSpeaking]);
  
  useEffect(() => {
    if (isListening) {
      setCurrentEmotion('👂');
    } else if (isSpeaking) {
      setCurrentEmotion('🗣️');
    } else {
      setCurrentEmotion('😊');
    }
  }, [isListening, isSpeaking]);
  
  const getStatusText = () => {
    if (isSpeaking) return '正在说话...';
    if (isListening) return '正在聆听...';
    return '待机中';
  };
  
  return (
    <CharacterContainer>
      <CharacterAvatar isListening={isListening} isSpeaking={isSpeaking}>
        <CharacterFace>{currentEmotion}</CharacterFace>
      </CharacterAvatar>
      
      <CharacterName>Luna</CharacterName>
      
      <StatusIndicator isListening={isListening} isSpeaking={isSpeaking}>
        {getStatusText()}
      </StatusIndicator>
      
      <WaveContainer isActive={isListening || isSpeaking}>
        {[...Array(5)].map((_, index) => (
          <WaveBar 
            key={index} 
            delay={index * 0.1} 
            isActive={isListening || isSpeaking}
          />
        ))}
      </WaveContainer>
    </CharacterContainer>
  );
};

export default VirtualCharacter;