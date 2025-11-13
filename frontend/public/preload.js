const { contextBridge, ipcRenderer, desktopCapturer } = require('electron');

// 暴露安全的 API 给渲染进程（统一一次性暴露）

// 暴露 WebSocket 相关的 API
contextBridge.exposeInMainWorld('wsAPI', {
  // 这里可以添加一些 WebSocket 连接的辅助方法
  // 比如获取后端服务地址等
  getBackendUrl: () => {
    // 可以从环境变量或配置文件中读取
    return process.env.BACKEND_URL || 'ws://localhost:8765';
  }
});

// 悬浮头像窗口控制 API
contextBridge.exposeInMainWorld('electronAPI', {
  // 保留已有方法
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  minimizeWindow: () => ipcRenderer.invoke('minimize-window'),
  maximizeWindow: () => ipcRenderer.invoke('maximize-window'),
  closeWindow: () => ipcRenderer.invoke('close-window'),
  platform: process.platform,
  onWindowStateChange: (callback) => ipcRenderer.on('window-state-changed', callback),
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
  captureScreen: async (options = {}) => {
    const {
      sourceId = null,
      types = ['screen'],
      width = 640,
      height = 360,
      quality = 0.8
    } = options;

    const thumbnailSize = {
      width: Math.max(1, Math.floor(width)),
      height: Math.max(1, Math.floor(height))
    };

    const sources = await desktopCapturer.getSources({
      types,
      thumbnailSize,
      fetchWindowIcons: false
    });

    const targetSource = sourceId
      ? sources.find(source => source.id === sourceId)
      : sources[0];

    if (!targetSource) {
      throw new Error('未找到可用的屏幕源');
    }

    if (targetSource.thumbnail.isEmpty()) {
      throw new Error('无法捕获屏幕图像，请检查系统截屏权限');
    }

    let image = targetSource.thumbnail;

    // 再次调整尺寸，确保符合设定
    image = image.resize(thumbnailSize);

    const jpegBuffer = image.toJPEG(Math.round(quality * 100));
    const dataUrl = `data:image/jpeg;base64,${jpegBuffer.toString('base64')}`;

    return {
      dataUrl,
      sourceId: targetSource.id,
      sourceName: targetSource.name,
      capturedAt: Date.now(),
      width: thumbnailSize.width,
      height: thumbnailSize.height
    };
  },
  // Avatar 悬浮窗口
  openAvatarWindow: () => ipcRenderer.invoke('open-avatar-window'),
  closeAvatarWindow: () => ipcRenderer.invoke('close-avatar-window'),
  toggleAvatarWindow: () => ipcRenderer.invoke('toggle-avatar-window'),
  resizeAvatarWindow: (size) => ipcRenderer.invoke('avatar-resize', size),
  moveAvatarWindow: (pos) => ipcRenderer.invoke('avatar-move', pos),
  setAvatarAlwaysOnTop: (on) => ipcRenderer.invoke('avatar-always-on-top', on)
});