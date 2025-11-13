import React, { useEffect, useMemo, useRef } from 'react';
import styled from 'styled-components';
import { useVideoCapture } from '../../contexts/VideoCaptureContext';

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

const Row = styled.div`
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
`;

const Label = styled.label`
  font-size: 13px;
  opacity: 0.9;
`;

const NumberInput = styled.input`
  width: 100px;
  padding: 8px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.08);
  color: white;
`;

const ControlButton = styled.button<{ active?: boolean; variant?: 'primary' | 'secondary' | 'danger' }>`
  padding: 10px 16px;
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
  opacity: ${props => (props.disabled ? 0.5 : 1)};
`;

const Hint = styled.div`
  font-size: 12px;
  opacity: 0.8;
`;

// electronAPI 类型声明已在 global d.ts 中提供

const VideoInputControl: React.FC = () => {
  const { settings, updateSettings, isEnabled, setEnabled, addCapturedImage } = useVideoCapture();
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const electronAvailable = useMemo(() => {
    return typeof window !== 'undefined' && !!window.electronAPI && typeof window.electronAPI.captureScreen === 'function';
  }, []);

  useEffect(() => {
    const stopTimer = () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };

    const startTimer = () => {
      stopTimer();
      if (!electronAvailable) return;
      const intervalMs = Math.max(1, settings.intervalSec) * 1000;
      timerRef.current = setInterval(async () => {
        try {
          const result = await window.electronAPI!.captureScreen({
            width: settings.width,
            height: settings.height,
            quality: 0.8,
          });
          addCapturedImage({
            id: `${result.capturedAt}-${result.sourceId}`,
            dataUrl: result.dataUrl,
            capturedAt: result.capturedAt,
            sourceId: result.sourceId,
            sourceName: result.sourceName,
            width: result.width,
            height: result.height,
          });
        } catch (err) {
          console.error('captureScreen error:', err);
        }
      }, intervalMs);
    };

    if (isEnabled) {
      startTimer();
    } else {
      stopTimer();
    }

    return () => stopTimer();
  }, [isEnabled, settings.width, settings.height, settings.intervalSec, electronAvailable, addCapturedImage]);

  const toggleEnabled = () => {
    if (!electronAvailable) return;
    setEnabled(!isEnabled);
  };

  return (
    <ControlSection>
      <SectionTitle>🎥 视频输入控制</SectionTitle>

      {!electronAvailable && (
        <Hint>此功能仅在 Electron 桌面应用中可用。</Hint>
      )}

      <Row>
        <ControlButton
          onClick={toggleEnabled}
          active={isEnabled}
          variant={isEnabled ? 'danger' : 'primary'}
          disabled={!electronAvailable}
        >
          {isEnabled ? '🛑 关闭截图' : '📸 开启截图'}
        </ControlButton>
      </Row>

      <Row>
        <Label>间隔(秒)</Label>
        <NumberInput
          type="number"
          min={1}
          step={1}
          value={settings.intervalSec}
          onChange={(e) => updateSettings({ intervalSec: Math.max(1, Number(e.target.value) || 1) })}
        />
        <Label>分辨率</Label>
        <NumberInput
          type="number"
          min={16}
          step={16}
          value={settings.width}
          onChange={(e) => updateSettings({ width: Math.max(16, Number(e.target.value) || 16) })}
        />
        <span>x</span>
        <NumberInput
          type="number"
          min={16}
          step={16}
          value={settings.height}
          onChange={(e) => updateSettings({ height: Math.max(16, Number(e.target.value) || 16) })}
        />
      </Row>

      <Row>
        <ControlButton
          onClick={async () => {
            if (!electronAvailable) return;
            try {
              const result = await window.electronAPI!.captureScreen({
                width: settings.width,
                height: settings.height,
                quality: 0.8,
              });
              addCapturedImage({
                id: `${result.capturedAt}-${result.sourceId}`,
                dataUrl: result.dataUrl,
                capturedAt: result.capturedAt,
                sourceId: result.sourceId,
                sourceName: result.sourceName,
                width: result.width,
                height: result.height,
              });
            } catch (err) {
              console.error('captureScreen error:', err);
            }
          }}
          variant="secondary"
          disabled={!electronAvailable}
        >
          立即截图
        </ControlButton>
      </Row>
    </ControlSection>
  );
};

export default VideoInputControl;