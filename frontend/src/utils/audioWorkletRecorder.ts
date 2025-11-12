/**
 * AudioWorklet录音器
 * 支持高质量实时音频录制和持续监听模式
 * 本文件导出以下内容：
 * 1. AudioConfig 接口：基础音频配置（采样率、通道数、位深、格式）
 * 2. AudioWorkletConfig 接口：继承 AudioConfig，扩展 bufferSize、chunkSize、enableRealTimeProcessing、enableNoiseReduction、enableRealtimeTransmission 等 AudioWorklet 专用配置
 * 3. AudioChunk 接口：实时音频块结构（audioData、timestamp、chunkSize）
 * 4. DEFAULT_WORKLET_CONFIG 常量：默认 AudioWorklet 配置对象
 * 5. AudioWorkletRecorder 类：基于 AudioWorklet 的高性能录音器，支持：
 *    - 高质量实时录音与暂停/继续
 *    - 持续监听模式（低功耗实时音频流）
 *    - 噪声抑制、自动增益
 *    - 实时音频块回调与录音完成回调
 *    - 动态配置更新
 *    - 浏览器兼容性检测
 *    主要方法：startRecording、stopRecording、startListening、stopListening、updateConfig、setAudioChunkCallback、setRealtimeAudioChunkCallback、setListeningCallbacks、getStatus、getConfig、isSupported 等
 */

export interface AudioConfig {
  sampleRate: number;
  channels: number;
  bitDepth: number;
  format: string;
}

export interface AudioWorkletConfig extends AudioConfig {
  bufferSize?: number;
  chunkSize?: number;
  enableRealTimeProcessing?: boolean;
  enableNoiseReduction?: boolean;
  enableRealtimeTransmission?: boolean;
}

export interface AudioChunk {
  audioData: ArrayBuffer;
  timestamp: number;
  chunkSize?: number;
}

export const DEFAULT_WORKLET_CONFIG: AudioWorkletConfig = {
  sampleRate: 44100,
  channels: 1,
  bitDepth: 16,
  format: 'wav',
  bufferSize: 4096,
  chunkSize: 512,
  enableRealTimeProcessing: true,
  enableNoiseReduction: true,
  enableRealtimeTransmission: true
};

export class AudioWorkletRecorder {
  private audioContext: AudioContext | null = null;
  private audioWorkletNode: AudioWorkletNode | null = null;
  private mediaStream: MediaStream | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private isRecording = false;
  private isListening = false; // 新增：持续监听状态
  private audioChunks: ArrayBuffer[] = [];
  private onAudioChunk?: (chunk: ArrayBuffer) => void;
  private onRealtimeAudioChunk?: (chunk: AudioChunk) => void; // 新增：实时音频块回调
  private onRecordingComplete?: (audioData: ArrayBuffer) => void;
  private onListeningStart?: () => void; // 新增：监听开始回调
  private onListeningStop?: () => void; // 新增：监听停止回调

  constructor(private config: AudioWorkletConfig = DEFAULT_WORKLET_CONFIG) {}

  /**
   * 初始化AudioWorklet
   */
  private async initializeAudioWorklet(): Promise<void> {
    try {
      // 创建AudioContext
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.config.sampleRate
      });

      // 加载AudioWorklet模块
      await this.audioContext.audioWorklet.addModule('/audio-worklet-processor.js');

      // 创建AudioWorkletNode
      this.audioWorkletNode = new AudioWorkletNode(
        this.audioContext,
        'audio-recorder-processor',
        {
          numberOfInputs: 1,
          numberOfOutputs: 0,
          channelCount: this.config.channels,
          channelCountMode: 'explicit',
          channelInterpretation: 'speakers'
        }
      );

      // 监听来自AudioWorklet的消息
      this.audioWorkletNode.port.onmessage = (event) => {
        this.handleWorkletMessage(event.data);
      };

      console.log('✅ AudioWorklet初始化成功');
    } catch (error) {
      console.error('❌ AudioWorklet初始化失败:', error);
      throw new Error('AudioWorklet初始化失败，请检查浏览器支持');
    }
  }

  /**
   * 处理来自AudioWorklet的消息
   */
  private handleWorkletMessage(data: any): void {
    switch (data.type) {
      case 'recording-started':
        console.log('🎤 AudioWorklet录音已开始');
        break;

      case 'listening-started':
        console.log('👂 AudioWorklet持续监听已开始');
        if (this.onListeningStart) {
          this.onListeningStart();
        }
        break;

      case 'listening-stopped':
        console.log('🔇 AudioWorklet持续监听已停止');
        if (this.onListeningStop) {
          this.onListeningStop();
        }
        break;

      case 'audio-chunk':
        // 实时音频数据块
        this.audioChunks.push(data.audioData);
        if (this.onAudioChunk) {
          this.onAudioChunk(data.audioData);
        }
        break;

      case 'realtime-audio-chunk':
        // 持续监听模式下的实时音频块
        if (this.onRealtimeAudioChunk) {
          this.onRealtimeAudioChunk({
            audioData: data.audioData,
            timestamp: data.timestamp,
            chunkSize: data.chunkSize
          });
        }
        break;

      case 'recording-stopped':
        // 录音完成
        if (data.audioData) {
          this.audioChunks.push(data.audioData);
        }
        if (this.onRecordingComplete) {
          const completeAudio = this.combineAudioChunks();
          this.onRecordingComplete(completeAudio);
        }
        console.log('🛑 AudioWorklet录音已停止');
        break;

      default:
        console.warn('未知的AudioWorklet消息类型:', data.type);
    }
  }

  /**
   * 合并音频数据块
   */
  private combineAudioChunks(): ArrayBuffer {
    if (this.audioChunks.length === 0) {
      return new ArrayBuffer(0);
    }

    if (this.audioChunks.length === 1) {
      return this.audioChunks[0];
    }

    // 计算总长度
    const totalLength = this.audioChunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
    
    // 合并所有数据块
    const combined = new Uint8Array(totalLength);
    let offset = 0;
    
    for (const chunk of this.audioChunks) {
      combined.set(new Uint8Array(chunk), offset);
      offset += chunk.byteLength;
    }

    return combined.buffer;
  }

  /**
   * 开始录音
   */
  async startRecording(): Promise<void> {
    try {
      // 获取麦克风权限
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: this.config.sampleRate,
          channelCount: this.config.channels,
          echoCancellation: this.config.enableNoiseReduction,
          noiseSuppression: this.config.enableNoiseReduction,
          autoGainControl: true
        }
      });

      // 初始化AudioWorklet
      await this.initializeAudioWorklet();

      if (!this.audioContext || !this.audioWorkletNode) {
        throw new Error('AudioWorklet未正确初始化');
      }

      // 创建音频源节点
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      // 连接音频节点
      this.sourceNode.connect(this.audioWorkletNode);

      // 清空之前的音频数据
      this.audioChunks = [];

      // 发送开始录音命令到AudioWorklet
      this.audioWorkletNode.port.postMessage({
        command: 'start',
        data: {
          sampleRate: this.config.sampleRate,
          channels: this.config.channels,
          bufferSize: this.config.bufferSize
        }
      });

      this.isRecording = true;
      console.log('🎤 AudioWorklet录音开始');

    } catch (error) {
      console.error('❌ 启动AudioWorklet录音失败:', error);
      this.cleanup();
      throw new Error('无法启动录音，请检查麦克风权限和浏览器支持');
    }
  }

  /**
   * 停止录音
   */
  async stopRecording(): Promise<ArrayBuffer> {
    return new Promise((resolve, reject) => {
      if (!this.isRecording || !this.audioWorkletNode) {
        reject(new Error('录音未开始'));
        return;
      }

      // 设置录音完成回调
      this.onRecordingComplete = (audioData: ArrayBuffer) => {
        this.cleanup();
        resolve(audioData);
      };

      // 发送停止录音命令到AudioWorklet
      this.audioWorkletNode.port.postMessage({
        command: 'stop'
      });

      this.isRecording = false;
      console.log('🛑 AudioWorklet录音停止');
    });
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

      // 如果还未初始化，先初始化AudioWorklet
      if (!this.audioWorkletNode) {
        await this.initializeAudioWorklet();
      }

      if (!this.audioContext || !this.audioWorkletNode) {
        throw new Error('AudioWorklet未正确初始化');
      }

      // 获取麦克风权限（如果还没有）
      if (!this.mediaStream) {
        this.mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            sampleRate: this.config.sampleRate,
            channelCount: this.config.channels,
            echoCancellation: this.config.enableNoiseReduction,
            noiseSuppression: this.config.enableNoiseReduction,
            autoGainControl: true
          }
        });

        // 创建音频源节点
        this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
        // 连接音频节点
        this.sourceNode.connect(this.audioWorkletNode);
      }

      // 发送开始监听命令到AudioWorklet
      this.audioWorkletNode.port.postMessage({
        command: 'startListening',
        data: {
          sampleRate: this.config.sampleRate,
          channels: this.config.channels,
          chunkSize: this.config.chunkSize,
          enableRealtimeTransmission: this.config.enableRealtimeTransmission
        }
      });

      this.isListening = true;
      console.log('👂 AudioWorklet持续监听开始');

    } catch (error) {
      console.error('❌ 启动AudioWorklet持续监听失败:', error);
      throw new Error('无法启动持续监听，请检查麦克风权限和浏览器支持');
    }
  }

  /**
   * 停止持续监听
   */
  stopListening(): void {
    if (!this.isListening || !this.audioWorkletNode) {
      return;
    }

    // 发送停止监听命令到AudioWorklet
    this.audioWorkletNode.port.postMessage({
      command: 'stopListening'
    });

    this.isListening = false;
    console.log('🔇 AudioWorklet持续监听停止');
  }

  /**
   * 获取录音状态
   */
  getRecordingState(): boolean {
    return this.isRecording;
  }

  /**
   * 获取监听状态
   */
  getListeningState(): boolean {
    return this.isListening;
  }

  /**
   * 设置实时音频数据回调
   */
  setAudioChunkCallback(callback: (chunk: ArrayBuffer) => void): void {
    this.onAudioChunk = callback;
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
   * 清理资源
   */
  private cleanup(): void {
    // 停止监听
    this.stopListening();

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.audioWorkletNode) {
      this.audioWorkletNode.disconnect();
      this.audioWorkletNode = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }

    this.audioChunks = [];
    this.isListening = false;
    this.onAudioChunk = undefined;
    this.onRealtimeAudioChunk = undefined;
    this.onRecordingComplete = undefined;
    this.onListeningStart = undefined;
    this.onListeningStop = undefined;
  }

  /**
   * 检查AudioWorklet支持
   */
  static isSupported(): boolean {
    try {
      if (typeof window === 'undefined') return false;

      const AC: any = (window as any).AudioContext || (window as any).webkitAudioContext;
      if (!AC) return false;

      // 避免直接访问 getter 导致 Illegal invocation
      const hasAudioWorkletProp = 'audioWorklet' in (AC.prototype || {});
      const hasAudioWorkletNode = typeof (window as any).AudioWorkletNode !== 'undefined';

      return !!(hasAudioWorkletProp && hasAudioWorkletNode);
    } catch (error) {
      console.warn('AudioWorklet support check failed:', error);
      return false;
    }
  }

  /**
   * 获取当前状态
   */
  getStatus() {
    return {
      isRecording: this.isRecording,
      isListening: this.isListening,
      isInitialized: !!this.audioWorkletNode,
      config: this.config
    };
  }

  /**
   * 获取音频配置信息
   */
  getConfig(): AudioWorkletConfig {
    return { ...this.config };
  }

  /**
   * 更新配置
   */
  updateConfig(newConfig: Partial<AudioWorkletConfig>): void {
    this.config = { ...this.config, ...newConfig };
    
    // 如果正在录音或监听，发送配置更新到AudioWorklet
    if ((this.isRecording || this.isListening) && this.audioWorkletNode) {
      this.audioWorkletNode.port.postMessage({
        command: 'configure',
        data: newConfig
      });
    }
  }
}