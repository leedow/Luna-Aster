/**
 * AudioWorklet处理器
 * 用于实时音频录制和处理，支持持续监听模式
 */

class AudioRecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    
    // 音频配置
    this.sampleRate = 16000;
    this.channels = 1;
    this.bufferSize = 4096;
    this.chunkSize = 1024; // 实时传输的块大小
    
    // 音频缓冲区
    this.audioBuffer = [];
    this.isRecording = false;
    this.isListening = false; // 新增：持续监听状态
    
    // 重采样相关
    this.resampleRatio = sampleRate / this.sampleRate;
    this.resampleBuffer = [];
    
    // 实时传输相关
    this.realtimeBuffer = [];
    this.enableRealtimeTransmission = false;
    
    // 监听主线程消息
    this.port.onmessage = (event) => {
      const { command, data } = event.data;
      
      switch (command) {
        case 'start':
          this.startRecording(data);
          break;
        case 'stop':
          this.stopRecording();
          break;
        case 'startListening':
          this.startListening(data);
          break;
        case 'stopListening':
          this.stopListening();
          break;
        case 'configure':
          this.configure(data);
          break;
      }
    };
  }

  startRecording(config = {}) {
    this.isRecording = true;
    this.audioBuffer = [];
    
    // 更新配置
    if (config.sampleRate) this.sampleRate = config.sampleRate;
    if (config.channels) this.channels = config.channels;
    if (config.chunkSize) this.chunkSize = config.chunkSize;
    
    this.resampleRatio = sampleRate / this.sampleRate;
    
    this.port.postMessage({
      type: 'recording-started',
      config: {
        sampleRate: this.sampleRate,
        channels: this.channels
      }
    });
    
    console.log('🎤 AudioWorklet开始录音');
  }

  stopRecording() {
    this.isRecording = false;
    
    // 发送最终的音频数据
    if (this.audioBuffer.length > 0) {
      const audioData = this.convertToWAV(this.audioBuffer);
      this.port.postMessage({
        type: 'recording-stopped',
        audioData: audioData
      });
    }
    
    this.audioBuffer = [];
    console.log('🛑 AudioWorklet停止录音');
  }

  // 新增：开始持续监听
  startListening(config = {}) {
    this.isListening = true;
    this.enableRealtimeTransmission = true;
    this.realtimeBuffer = [];
    
    // 更新配置
    if (config.sampleRate) this.sampleRate = config.sampleRate;
    if (config.channels) this.channels = config.channels;
    if (config.chunkSize) this.chunkSize = config.chunkSize;
    
    this.resampleRatio = sampleRate / this.sampleRate;
    
    this.port.postMessage({
      type: 'listening-started',
      config: {
        sampleRate: this.sampleRate,
        channels: this.channels,
        chunkSize: this.chunkSize
      }
    });
    
    console.log('👂 AudioWorklet开始持续监听');
  }

  // 新增：停止持续监听
  stopListening() {
    this.isListening = false;
    this.enableRealtimeTransmission = false;
    this.realtimeBuffer = [];
    
    this.port.postMessage({
      type: 'listening-stopped'
    });
    
    console.log('🔇 AudioWorklet停止持续监听');
  }

  configure(config) {
    if (config.sampleRate) this.sampleRate = config.sampleRate;
    if (config.channels) this.channels = config.channels;
    if (config.bufferSize) this.bufferSize = config.bufferSize;
    if (config.chunkSize) this.chunkSize = config.chunkSize;
    
    this.resampleRatio = sampleRate / this.sampleRate;
  }
  
  process(inputs, outputs, parameters) {
    if ((!this.isRecording && !this.isListening) || inputs.length === 0) {
      return true;
    }
    
    const input = inputs[0];
    if (input.length === 0) {
      return true;
    }
    
    // 处理音频数据（假设单声道）
    const inputChannel = input[0];
    
    // 重采样到目标采样率
    const resampledData = this.resample(inputChannel);
    
    // 如果正在录音，添加到录音缓冲区
    if (this.isRecording) {
      this.audioBuffer.push(...resampledData);
      
      // 当缓冲区达到一定大小时，发送数据块
      if (this.audioBuffer.length >= this.bufferSize) {
        const chunk = this.audioBuffer.splice(0, this.bufferSize);
        const audioData = this.convertToWAV([chunk]);
        
        this.port.postMessage({
          type: 'audio-chunk',
          audioData: audioData,
          timestamp: currentTime
        });
      }
    }
    
    // 如果正在监听，进行实时传输
    if (this.isListening && this.enableRealtimeTransmission) {
      this.realtimeBuffer.push(...resampledData);
      
      // 当实时缓冲区达到块大小时，发送实时数据
      if (this.realtimeBuffer.length >= this.chunkSize) {
        const chunk = this.realtimeBuffer.splice(0, this.chunkSize);
        const audioData = this.convertToWAV([chunk]);
        
        this.port.postMessage({
          type: 'realtime-audio-chunk',
          audioData: audioData,
          timestamp: currentTime,
          chunkSize: this.chunkSize
        });
      }
    }
    
    return true;
  }

  // 重采样函数
  resample(inputData) {
    if (this.resampleRatio === 1) {
      return Array.from(inputData);
    }
    
    const outputLength = Math.floor(inputData.length / this.resampleRatio);
    const output = new Float32Array(outputLength);
    
    for (let i = 0; i < outputLength; i++) {
      const sourceIndex = i * this.resampleRatio;
      const index = Math.floor(sourceIndex);
      const fraction = sourceIndex - index;
      
      if (index + 1 < inputData.length) {
        output[i] = inputData[index] * (1 - fraction) + inputData[index + 1] * fraction;
      } else {
        output[i] = inputData[index];
      }
    }
    
    return Array.from(output);
  }

  // 转换为WAV格式
  convertToWAV(audioData) {
    const flatData = audioData.flat();
    const length = flatData.length;
    const buffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(buffer);
    
    // WAV文件头
    const writeString = (offset, string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, this.channels, true);
    view.setUint32(24, this.sampleRate, true);
    view.setUint32(28, this.sampleRate * this.channels * 2, true);
    view.setUint16(32, this.channels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * 2, true);
    
    // 音频数据
    let offset = 44;
    for (let i = 0; i < length; i++) {
      const sample = Math.max(-1, Math.min(1, flatData[i]));
      view.setInt16(offset, sample * 0x7FFF, true);
      offset += 2;
    }
    
    return buffer;
  }
}

registerProcessor('audio-recorder-processor', AudioRecorderProcessor);