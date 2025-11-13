export {}; // ensure this file is treated as a module

declare global {
  interface Window {
    electronAPI?: {
      // 主窗口控制
      getAppVersion: () => Promise<string>;
      minimizeWindow: () => Promise<void>;
      maximizeWindow: () => Promise<void>;
      closeWindow: () => Promise<void>;
      platform: string;
      onWindowStateChange: (callback: (...args: any[]) => void) => void;
      removeAllListeners: (channel: string) => void;

      // 屏幕捕获
      captureScreen: (options?: {
        sourceId?: string | null;
        types?: string[];
        width?: number;
        height?: number;
        quality?: number;
      }) => Promise<{
        dataUrl: string;
        sourceId: string;
        sourceName: string;
        capturedAt: number;
        width: number;
        height: number;
      }>;

      // 悬浮头像窗口控制
      openAvatarWindow: () => Promise<void>;
      closeAvatarWindow: () => Promise<void>;
      toggleAvatarWindow: () => Promise<void>;
      resizeAvatarWindow: (size: { width: number; height: number }) => Promise<void>;
      moveAvatarWindow: (pos: { x: number; y: number }) => Promise<void>;
      setAvatarAlwaysOnTop: (on: boolean) => Promise<void>;
    };
  }
}