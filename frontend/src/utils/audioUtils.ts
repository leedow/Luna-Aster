/**
 * 前端音频处理工具
 * 提供音频录制、播放、格式转换等功能，支持持续监听模式
 */

import { AudioWorkletRecorder, AudioWorkletConfig, DEFAULT_WORKLET_CONFIG, AudioConfig } from './audioWorkletRecorder';

export const DEFAULT_AUDIO_CONFIG: AudioConfig = {
  sampleRate: 16000,
  channels: 1,
  bitDepth: 16,
  format: 'wav'
};

export enum RecorderType {
  AUDIO_WORKLET = 'audioworklet',
  MEDIA_RECORDER = 'mediarecorder'
}

export interface AudioRecorderConfig extends AudioConfig {
  preferredRecorder?: RecorderType;
  enableRealTimeProcessing?: boolean;
  bufferSize?: number;
  chunkSize?: number;
  enableRealtimeTransmission?: boolean;
}

export interface AudioChunk {
  audioData: ArrayBuffer;
  timestamp: number;
  chunkSize?: number;
}

export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioWorkletRecorder: AudioWorkletRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private isRecording = false;
  private isListening = false; // 新增：持续监听状态
  private currentRecorderType: RecorderType;

  // 回调函数
  private onRealtimeAudioChunk?: (chunk: AudioChunk) => void;
  private onListeningStart?: () => void;
  private onListeningStop?: () => void;

  constructor(private config: AudioRecorderConfig = DEFAULT_AUDIO_CONFIG) {
    // 自动选择最佳的录制器类型
    this.currentRecorderType = this.selectBestRecorderType();
  }

  /**
   * 选择最佳的录制器类型
   */
  private selectBestRecorderType(): RecorderType {
    // 如果用户指定了偏好，优先使用
    if (this.config.preferredRecorder) {
      if (this.config.preferredRecorder === RecorderType.AUDIO_WORKLET && AudioWorkletRecorder.isSupported()) {
        return RecorderType.AUDIO_WORKLET;
      }
      if (this.config.preferredRecorder === RecorderType.MEDIA_RECORDER && this.isMediaRecorderSupported()) {
        return RecorderType.MEDIA_RECORDER;
      }
    }

    // 自动选择：优先使用AudioWorklet（更低延迟）
    if (AudioWorkletRecorder.isSupported()) {
      return RecorderType.AUDIO_WORKLET;
    }

    // 回退到MediaRecorder
    if (this.isMediaRecorderSupported()) {
      return RecorderType.MEDIA_RECORDER;
    }

    // 默认使用MediaRecorder
    return RecorderType.MEDIA_RECORDER;
  }

  /**
   * 检查MediaRecorder支持
   */
  private isMediaRecorderSupported(): boolean {
    return typeof MediaRecorder !== 'undefined';
  }

  async startRecording(): Promise<void> {
    try {
      this.isRecording = true;

      if (this.currentRecorderType === RecorderType.AUDIO_WORKLET) {
        await this.startAudioWorkletRecording();
      } else {
        await this.startMediaRecorderRecording();
      }

      console.log(`🎤 开始录音 (${this.currentRecorderType})`);
    } catch (error) {
      console.error('❌ 启动录音失败:', error);
      this.isRecording = false;
      throw new Error('无法访问麦克风，请检查权限设置');
    }
  }

  /**
   * 开始持续监听
   */
  async startListening(): Promise<void> {
    try {
      if (this.isListening) {
        console.warn('⚠️ 持续监听已在进行中');
        return;
      }

      this.isListening = true;

      // 只支持AudioWorklet进行持续监听
      if (this.currentRecorderType === RecorderType.AUDIO_WORKLET) {
        await this.startAudioWorkletListening();
      } else {
        // 如果当前不是AudioWorklet，切换到AudioWorklet
        this.currentRecorderType = RecorderType.AUDIO_WORKLET;
        await this.startAudioWorkletListening();
      }

      console.log(`👂 开始持续监听 (${this.currentRecorderType})`);
    } catch (error) {
      console.error('❌ 启动持续监听失败:', error);
      this.isListening = false;
      throw new Error('无法启动持续监听，请检查麦克风权限');
    }
  }

  /**
   * 停止持续监听
   */
  stopListening(): void {
    if (!this.isListening) {
      return;
    }

    this.isListening = false;

    if (this.audioWorkletRecorder) {
      this.audioWorkletRecorder.stopListening();
    }

    console.log('🔇 停止持续监听');
  }

  /**
   * 使用AudioWorklet开始录音
   */
  private async startAudioWorkletRecording(): Promise<void> {
    const workletConfig: AudioWorkletConfig = {
      sampleRate: this.config.sampleRate,
      channels: this.config.channels,
      bitDepth: this.config.bitDepth,
      format: this.config.format || 'wav',
      bufferSize: this.config.bufferSize || 4096,
      chunkSize: this.config.chunkSize || 1024,
      enableRealTimeProcessing: this.config.enableRealTimeProcessing ?? true,
      enableNoiseReduction: true,
      enableRealtimeTransmission: this.config.enableRealtimeTransmission ?? true
    };

    if (!this.audioWorkletRecorder) {
      this.audioWorkletRecorder = new AudioWorkletRecorder(workletConfig);
      this.setupAudioWorkletCallbacks();
    }
    
    await this.audioWorkletRecorder.startRecording();
  }

  /**
   * 使用AudioWorklet开始持续监听
   */
  private async startAudioWorkletListening(): Promise<void> {
    const workletConfig: AudioWorkletConfig = {
      sampleRate: this.config.sampleRate,
      channels: this.config.channels,
      bitDepth: this.config.bitDepth,
      format: this.config.format || 'wav',
      bufferSize: this.config.bufferSize || 4096,
      chunkSize: this.config.chunkSize || 1024,
      enableRealTimeProcessing: this.config.enableRealTimeProcessing ?? true,
      enableNoiseReduction: true,
      enableRealtimeTransmission: this.config.enableRealtimeTransmission ?? true
    };

    if (!this.audioWorkletRecorder) {
      this.audioWorkletRecorder = new AudioWorkletRecorder(workletConfig);
      this.setupAudioWorkletCallbacks();
    }
    
    await this.audioWorkletRecorder.startListening();
  }

  /**
   * 设置AudioWorklet回调函数
   */
  private setupAudioWorkletCallbacks(): void {
    if (!this.audioWorkletRecorder) return;

    // 设置实时音频块回调
    this.audioWorkletRecorder.setRealtimeAudioChunkCallback((chunk: AudioChunk) => {
      this.onRealtimeAudioChunk?.(chunk);
    });

    // 设置监听状态回调
    this.audioWorkletRecorder.setListeningCallbacks({
      onListeningStart: () => {
        this.onListeningStart?.();
      },
      onListeningStop: () => {
        this.onListeningStop?.();
      }
    });
  }

  /**
   * 使用MediaRecorder开始录音
   */
  private async startMediaRecorderRecording(): Promise<void> {
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
  }

  async stopRecording(): Promise<Blob> {
    return new Promise(async (resolve, reject) => {
      if (!this.isRecording) {
        reject(new Error('录音未开始'));
        return;
      }

      try {
        this.isRecording = false;

        if (this.currentRecorderType === RecorderType.AUDIO_WORKLET) {
          const audioData = await this.stopAudioWorkletRecording();
          const audioBlob = new Blob([audioData], { type: 'audio/wav' });
          resolve(audioBlob);
        } else {
          await this.stopMediaRecorderRecording(resolve);
        }

        console.log(`🛑 停止录音 (${this.currentRecorderType})`);
      } catch (error) {
        console.error('❌ 停止录音失败:', error);
        reject(error);
      }
    });
  }

  /**
   * 停止AudioWorklet录音
   */
  private async stopAudioWorkletRecording(): Promise<ArrayBuffer> {
    if (!this.audioWorkletRecorder) {
      throw new Error('AudioWorklet录制器未初始化');
    }

    const audioData = await this.audioWorkletRecorder.stopRecording();
    this.audioWorkletRecorder = null;
    return audioData;
  }

  /**
   * 停止MediaRecorder录音
   */
  private async stopMediaRecorderRecording(resolve: (value: Blob) => void): Promise<void> {
    if (!this.mediaRecorder) {
      throw new Error('MediaRecorder未初始化');
    }

    this.mediaRecorder.onstop = () => {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
      this.cleanupMediaRecorder();
      resolve(audioBlob);
    };

    this.mediaRecorder.stop();
  }

  getRecordingState(): boolean {
    return this.isRecording;
  }

  /**
   * 获取持续监听状态
   */
  getListeningState(): boolean {
    return this.isListening;
  }

  /**
   * 获取当前状态
   */
  getStatus() {
    return {
      isRecording: this.isRecording,
      isListening: this.isListening,
      currentRecorderType: this.currentRecorderType,
      isInitialized: !!this.audioWorkletRecorder
    };
  }

  /**
   * 设置实时音频块回调（持续监听模式）
   */
  setRealtimeAudioChunkCallback(callback: (chunk: AudioChunk) => void): void {
    this.onRealtimeAudioChunk = callback;
  }

  /**
   * 设置监听状态回调
   */
  setListeningCallbacks(callbacks: {
    onListeningStart?: () => void;
    onListeningStop?: () => void;
  }): void {
    this.onListeningStart = callbacks.onListeningStart;
    this.onListeningStop = callbacks.onListeningStop;
  }

  /**
   * 获取当前使用的录制器类型
   */
  getCurrentRecorderType(): RecorderType {
    return this.currentRecorderType;
  }

  /**
   * 强制切换录制器类型
   */
  switchRecorderType(type: RecorderType): void {
    if (this.isRecording) {
      throw new Error('无法在录音过程中切换录制器类型');
    }

    if (type === RecorderType.AUDIO_WORKLET && !AudioWorkletRecorder.isSupported()) {
      throw new Error('当前浏览器不支持AudioWorklet');
    }

    if (type === RecorderType.MEDIA_RECORDER && !this.isMediaRecorderSupported()) {
      throw new Error('当前浏览器不支持MediaRecorder');
    }

    this.currentRecorderType = type;
    console.log(`🔄 切换到录制器类型: ${type}`);
  }

  /**
   * 设置实时音频数据回调（仅AudioWorklet支持）
   */
  setAudioChunkCallback(callback: (chunk: ArrayBuffer) => void): void {
    if (this.currentRecorderType === RecorderType.AUDIO_WORKLET && this.audioWorkletRecorder) {
      this.audioWorkletRecorder.setAudioChunkCallback(callback);
    } else {
      console.warn('实时音频数据回调仅在AudioWorklet模式下支持');
    }
  }

  /**
   * 清理MediaRecorder资源
   */
  private cleanupMediaRecorder(): void {
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.mediaRecorder = null;
    this.audioChunks = [];
  }

  /**
   * 清理所有资源
   */
  private cleanup(): void {
    this.cleanupMediaRecorder();
    
    if (this.audioWorkletRecorder) {
      // AudioWorkletRecorder有自己的cleanup方法
      this.audioWorkletRecorder = null;
    }
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
    audioWorklet: boolean;
    mediaRecorder: boolean;
    recommendedRecorder: RecorderType;
  } {
    const recording = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    const playback = !!(window.AudioContext || (window as any).webkitAudioContext);
    const audioWorklet = AudioWorkletRecorder.isSupported();
    const mediaRecorder = typeof MediaRecorder !== 'undefined';
    
    const audio = document.createElement('audio');
    const formats: string[] = [];
    
    if (audio.canPlayType('audio/mp3')) formats.push('mp3');
    if (audio.canPlayType('audio/wav')) formats.push('wav');
    if (audio.canPlayType('audio/ogg')) formats.push('ogg');
    if (audio.canPlayType('audio/webm')) formats.push('webm');

    // 推荐的录制器类型
    const recommendedRecorder = audioWorklet ? RecorderType.AUDIO_WORKLET : RecorderType.MEDIA_RECORDER;

    return { 
      recording, 
      playback, 
      formats, 
      audioWorklet, 
      mediaRecorder, 
      recommendedRecorder 
    };
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