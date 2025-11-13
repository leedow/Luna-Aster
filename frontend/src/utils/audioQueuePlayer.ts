/**
 * 音频队列播放器
 * 管理音频播放队列，支持自动顺序播放
 */

import { AudioPlayer } from './audioUtils';

export interface AudioQueueItem {
  id: string;
  audioData: string; // base64 encoded
  format: string;
  text?: string;
  voice?: string;
  addedAt: Date;
}

export enum PlayerState {
  IDLE = 'idle',
  PLAYING = 'playing',
  PAUSED = 'paused',
  STOPPED = 'stopped'
}

export class AudioQueuePlayer {
  private queue: AudioQueueItem[] = [];
  private audioPlayer: AudioPlayer;
  private currentItem: AudioQueueItem | null = null;
  private state: PlayerState = PlayerState.IDLE;
  private isProcessing = false;

  // 回调函数
  private onPlayStart?: (item: AudioQueueItem) => void;
  private onPlayEnd?: (item: AudioQueueItem) => void;
  private onQueueUpdate?: (queueLength: number) => void;
  private onError?: (error: Error, item: AudioQueueItem) => void;

  constructor() {
    this.audioPlayer = new AudioPlayer();
  }

  /**
   * 添加音频到队列
   */
  async enqueue(item: Omit<AudioQueueItem, 'id' | 'addedAt'>): Promise<void> {
    const queueItem: AudioQueueItem = {
      ...item,
      id: `audio-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      addedAt: new Date()
    };

    this.queue.push(queueItem);
    console.log(`🎵 音频已加入队列 [${this.queue.length}]: ${queueItem.text?.substring(0, 30) || queueItem.id}...`);
    
    this.onQueueUpdate?.(this.queue.length);

    // 如果当前没有播放，开始播放
    if (!this.isProcessing && this.state === PlayerState.IDLE) {
      await this.processQueue();
    }
  }

  /**
   * 处理队列（按顺序播放）
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessing) {
      return;
    }

    this.isProcessing = true;

    while (this.queue.length > 0) {
      const item = this.queue.shift();
      if (!item) break;

      this.currentItem = item;
      this.state = PlayerState.PLAYING;

      try {
        console.log(`🔊 开始播放音频 [${this.queue.length + 1}]: ${item.text?.substring(0, 50) || item.id}...`);
        this.onPlayStart?.(item);

        // 播放音频
        await this.audioPlayer.playAudioFromBase64(item.audioData, item.format);

        console.log(`✅ 音频播放完成: ${item.text?.substring(0, 30) || item.id}...`);
        this.onPlayEnd?.(item);

      } catch (error) {
        console.error(`❌ 音频播放失败:`, error);
        this.onError?.(error as Error, item);
      }

      this.currentItem = null;
      this.onQueueUpdate?.(this.queue.length);
    }

    this.state = PlayerState.IDLE;
    this.isProcessing = false;
    console.log(`🎵 音频队列播放完成`);
  }

  /**
   * 停止播放并清空队列
   */
  stop(): void {
    console.log('⏹️ 停止音频播放并清空队列');
    this.audioPlayer.stopCurrentAudio();
    this.queue = [];
    this.currentItem = null;
    this.state = PlayerState.STOPPED;
    this.isProcessing = false;
    this.onQueueUpdate?.(0);
  }

  /**
   * 跳过当前音频
   */
  skip(): void {
    if (this.currentItem) {
      console.log('⏭️ 跳过当前音频');
      this.audioPlayer.stopCurrentAudio();
    }
  }

  /**
   * 清空队列（但不停止当前播放）
   */
  clearQueue(): void {
    console.log('🗑️ 清空播放队列');
    this.queue = [];
    this.onQueueUpdate?.(0);
  }

  /**
   * 获取队列状态
   */
  getStatus() {
    return {
      state: this.state,
      queueLength: this.queue.length,
      currentItem: this.currentItem,
      isPlaying: this.audioPlayer.isPlaying()
    };
  }

  /**
   * 获取队列
   */
  getQueue(): AudioQueueItem[] {
    return [...this.queue];
  }

  /**
   * 设置回调函数
   */
  setCallbacks(callbacks: {
    onPlayStart?: (item: AudioQueueItem) => void;
    onPlayEnd?: (item: AudioQueueItem) => void;
    onQueueUpdate?: (queueLength: number) => void;
    onError?: (error: Error, item: AudioQueueItem) => void;
  }): void {
    this.onPlayStart = callbacks.onPlayStart;
    this.onPlayEnd = callbacks.onPlayEnd;
    this.onQueueUpdate = callbacks.onQueueUpdate;
    this.onError = callbacks.onError;
  }
}

// 全局单例
export const audioQueuePlayer = new AudioQueuePlayer();
