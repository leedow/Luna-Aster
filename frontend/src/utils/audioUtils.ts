/**
 * 前端音频处理工具
 * 提供音频录制、播放、格式转换等功能
 */

export interface AudioConfig {
  sampleRate: number;
  channels: number;
  bitsPerSample: number;
}

export const DEFAULT_AUDIO_CONFIG: AudioConfig = {
  sampleRate: 16000,
  channels: 1,
  bitsPerSample: 16
};

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private isRecording = false;

  constructor(private config: AudioConfig = DEFAULT_AUDIO_CONFIG) {}

  async startRecording(): Promise<void> {
    try {
      // 获取麦克风权限
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });

      // 创建 MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      this.audioChunks = [];

      // 设置事件监听器
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      // 开始录制
      this.mediaRecorder.start(100); // 每100ms收集一次数据
      this.isRecording = true;

      console.log('🎤 开始录音');
    } catch (error) {
      console.error('❌ 启动录音失败:', error);
      throw new Error('无法访问麦克风，请检查权限设置');
    }
  }

  async stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder || !this.isRecording) {
        reject(new Error('录音未开始'));
        return;
      }

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        this.cleanup();
        resolve(audioBlob);
      };

      this.mediaRecorder.stop();
      this.isRecording = false;
      console.log('🛑 停止录音');
    });
  }

  getRecordingState(): boolean {
    return this.isRecording;
  }

  private cleanup(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.audioChunks = [];
  }
}

export class AudioPlayer {
  private audioContext: AudioContext | null = null;
  private currentSource: AudioBufferSourceNode | null = null;

  constructor() {
    this.initAudioContext();
  }

  private initAudioContext(): void {
    try {
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    } catch (error) {
      console.error('❌ 音频上下文初始化失败:', error);
    }
  }

  async playAudioFromBase64(base64Data: string, format: string = 'mp3'): Promise<void> {
    if (!this.audioContext) {
      throw new Error('音频上下文未初始化');
    }

    try {
      // 解码 base64 数据
      const binaryString = atob(base64Data);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // 解码音频数据
      const audioBuffer = await this.audioContext.decodeAudioData(bytes.buffer);

      // 停止当前播放
      this.stopCurrentAudio();

      // 创建音频源
      this.currentSource = this.audioContext.createBufferSource();
      this.currentSource.buffer = audioBuffer;
      this.currentSource.connect(this.audioContext.destination);

      // 播放音频
      this.currentSource.start();
      console.log('🔊 开始播放音频');

      // 播放结束后清理
      this.currentSource.onended = () => {
        this.currentSource = null;
        console.log('🔇 音频播放结束');
      };

    } catch (error) {
      console.error('❌ 音频播放失败:', error);
      throw new Error('音频播放失败');
    }
  }

  stopCurrentAudio(): void {
    if (this.currentSource) {
      this.currentSource.stop();
      this.currentSource = null;
      console.log('⏹️ 停止音频播放');
    }
  }

  isPlaying(): boolean {
    return this.currentSource !== null;
  }
}

// 音频格式转换工具
export const audioUtils = {
  // 将 Blob 转换为 base64
  async blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        // 移除 data:audio/webm;base64, 前缀
        const base64 = result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  },

  // 将 base64 转换为 Blob
  base64ToBlob(base64: string, mimeType: string = 'audio/webm'): Blob {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return new Blob([bytes], { type: mimeType });
  },

  // 检查浏览器音频支持
  checkAudioSupport(): {
    recording: boolean;
    playback: boolean;
    formats: string[];
  } {
    const recording = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    const playback = !!(window.AudioContext || (window as any).webkitAudioContext);
    
    const audio = document.createElement('audio');
    const formats: string[] = [];
    
    if (audio.canPlayType('audio/mp3')) formats.push('mp3');
    if (audio.canPlayType('audio/wav')) formats.push('wav');
    if (audio.canPlayType('audio/ogg')) formats.push('ogg');
    if (audio.canPlayType('audio/webm')) formats.push('webm');

    return { recording, playback, formats };
  },

  // 获取音频时长（估算）
  estimateAudioDuration(base64Data: string, sampleRate: number = 16000): number {
    try {
      const binaryString = atob(base64Data);
      const bytes = binaryString.length;
      // 简单估算：假设16位单声道音频
      return bytes / (sampleRate * 2);
    } catch (error) {
      console.error('❌ 估算音频时长失败:', error);
      return 0;
    }
  },

  // 验证音频数据
  validateAudioData(base64Data: string, maxSizeKB: number = 1024): boolean {
    try {
      if (!base64Data || typeof base64Data !== 'string') {
        return false;
      }

      // 检查 base64 格式
      const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/;
      if (!base64Regex.test(base64Data)) {
        return false;
      }

      // 检查大小
      const sizeKB = (base64Data.length * 3) / 4 / 1024;
      if (sizeKB > maxSizeKB) {
        console.warn(`⚠️ 音频数据过大: ${sizeKB.toFixed(2)}KB > ${maxSizeKB}KB`);
        return false;
      }

      return true;
    } catch (error) {
      console.error('❌ 音频数据验证失败:', error);
      return false;
    }
  }
};

// 音频可视化工具
export class AudioVisualizer {
  private analyser: AnalyserNode | null = null;
  private dataArray: Uint8Array | null = null;
  private animationId: number | null = null;

  constructor(private audioContext: AudioContext, private canvas: HTMLCanvasElement) {}

  connectSource(source: MediaStreamAudioSourceNode): void {
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 256;
    
    const bufferLength = this.analyser.frequencyBinCount;
    this.dataArray = new Uint8Array(bufferLength);
    
    source.connect(this.analyser);
  }

  startVisualization(): void {
    if (!this.analyser || !this.dataArray) return;

    const canvas = this.canvas;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      if (!this.analyser || !this.dataArray) return;

      this.animationId = requestAnimationFrame(draw);

      this.analyser.getByteFrequencyData(this.dataArray);

      ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / this.dataArray.length) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < this.dataArray.length; i++) {
        barHeight = (this.dataArray[i] / 255) * canvas.height;

        ctx.fillStyle = `rgb(${barHeight + 100}, 50, 50)`;
        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);

        x += barWidth + 1;
      }
    };

    draw();
  }

  stopVisualization(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }
}