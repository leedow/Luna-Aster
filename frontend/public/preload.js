const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的 API 给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 应用信息
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  
  // 窗口控制
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  
  // 系统信息
  platform: process.platform,
  
  // 事件监听
  onWindowStateChange: (callback) => {
    ipcRenderer.on('window-state-changed', callback);
  },
  
  // 移除事件监听
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});

// 暴露 WebSocket 相关的 API
contextBridge.exposeInMainWorld('wsAPI', {
  // 这里可以添加一些 WebSocket 连接的辅助方法
  // 比如获取后端服务地址等
  getBackendUrl: () => {
    // 可以从环境变量或配置文件中读取
    return process.env.BACKEND_URL || 'ws://localhost:8765';
  }
});