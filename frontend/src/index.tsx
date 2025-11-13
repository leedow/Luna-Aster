import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { VideoCaptureProvider } from './contexts/VideoCaptureContext';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <WebSocketProvider>
      <VideoCaptureProvider>
        <App />
      </VideoCaptureProvider>
    </WebSocketProvider>
  </React.StrictMode>
);