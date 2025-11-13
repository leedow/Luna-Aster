import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  ReactNode,
} from 'react';

export interface CapturedImage {
  id: string;
  dataUrl: string;
  capturedAt: number;
  sourceId: string;
  sourceName: string;
  width: number;
  height: number;
}

export interface VideoCaptureSettings {
  intervalSec: number;
  width: number;
  height: number;
  quality: number;
}

interface VideoCaptureContextValue {
  capturedImages: CapturedImage[];
  addCapturedImage: (image: CapturedImage) => void;
  clearCapturedImages: () => void;
  settings: VideoCaptureSettings;
  updateSettings: (partial: Partial<VideoCaptureSettings>) => void;
  isEnabled: boolean;
  setEnabled: (enabled: boolean) => void;
}

const DEFAULT_SETTINGS: VideoCaptureSettings = {
  intervalSec: 5,
  width: 640,
  height: 360,
  quality: 0.8,
};

const VideoCaptureContext = createContext<VideoCaptureContextValue | null>(null);

export const VideoCaptureProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [capturedImages, setCapturedImages] = useState<CapturedImage[]>([]);
  const [settings, setSettings] = useState<VideoCaptureSettings>(DEFAULT_SETTINGS);
  const [isEnabled, setIsEnabled] = useState<boolean>(false);

  const addCapturedImage = useCallback((image: CapturedImage) => {
    setCapturedImages(prev => {
      const next = [...prev, image];
      // 限制缓存数量，避免无限增长
      if (next.length > 100) {
        return next.slice(next.length - 100);
      }
      return next;
    });
  }, []);

  const clearCapturedImages = useCallback(() => {
    setCapturedImages([]);
  }, []);

  const updateSettings = useCallback((partial: Partial<VideoCaptureSettings>) => {
    setSettings(prev => ({
      ...prev,
      ...partial,
    }));
  }, []);

  const value = useMemo<VideoCaptureContextValue>(() => ({
    capturedImages,
    addCapturedImage,
    clearCapturedImages,
    settings,
    updateSettings,
    isEnabled,
    setEnabled: setIsEnabled,
  }), [capturedImages, addCapturedImage, clearCapturedImages, settings, updateSettings, isEnabled]);

  return (
    <VideoCaptureContext.Provider value={value}>
      {children}
    </VideoCaptureContext.Provider>
  );
};

export const useVideoCapture = (): VideoCaptureContextValue => {
  const context = useContext(VideoCaptureContext);
  if (!context) {
    throw new Error('useVideoCapture must be used within a VideoCaptureProvider');
  }
  return context;
};

