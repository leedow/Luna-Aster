import React from 'react';
import styled from 'styled-components';
import { WebSocketProvider } from './contexts/WebSocketContext';
import ChatInterface from './components/ChatInterface/ChatInterface';
import ControlPanel from './components/ControlPanel/ControlPanel';
import StatusBar from './components/StatusBar/StatusBar';

const AppContainer = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  overflow: hidden;
`;

const MainContent = styled.div`
  display: flex;
  flex: 1;
  overflow: hidden;
`;

const LeftPanel = styled.div`
  width: 300px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
`;

const ChatArea = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0; /* 防止flex子元素溢出 */
`;

const AppContent: React.FC = () => {
  return (
    <AppContainer>
      <StatusBar />
      <MainContent>
        <LeftPanel>
          <ControlPanel />
        </LeftPanel>
        <ChatArea>
          <ChatInterface />
        </ChatArea>
      </MainContent>
    </AppContainer>
  );
};

function App() {
  return (
    <WebSocketProvider autoConnect={true} maxMessages={500}>
      <AppContent />
    </WebSocketProvider>
  );
}

export default App;