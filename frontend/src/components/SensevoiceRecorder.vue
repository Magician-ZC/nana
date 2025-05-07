<script setup>
import { ref, onMounted, onBeforeUnmount, watch, defineEmits } from 'vue';

const props = defineProps({
  // Enable/disable voice input mode
  voiceInputMode: {
    type: Boolean,
    default: true
  },
  // Auto-send message after silence (in seconds)
  voiceTimeout: {
    type: Number,
    default: 5
  },
  // Whether we're currently waiting for AI response
  isLoading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['transcript-result', 'recording-state-change', 'send-transcript']);

// State variables
const isRecording = ref(false);
const recordingError = ref(false);
const recordingText = ref('');
const voiceButtonPressed = ref(false);
const transcriptionList = ref([]);
const isConnecting = ref(false);

// WebSocket connection
let ws = null;
let silenceTimer = null;
let activityTimeoutId = null;

// Audio recording variables
let audioContext = null;
let mediaStream = null;
let mediaRecorder = null;
let audioProcessor = null;
let audioChunks = [];
let recorder = null; // Recorder.js instance

// Add reconnection capabilities
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 3;
let reconnectTimer = null;

// User inactivity detection
const INACTIVITY_TIMEOUT = 15000; // 15 seconds without speech detection
let lastActivityTime = 0;

// Clean up resources
onBeforeUnmount(() => {
  stopRecording();
  cleanupTimers();
  cleanupAudioResources();
});

// Clean up timers
function cleanupTimers() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  
  if (silenceTimer) {
    clearTimeout(silenceTimer);
    silenceTimer = null;
  }
  
  if (activityTimeoutId) {
    clearTimeout(activityTimeoutId);
    activityTimeoutId = null;
  }
}

// Clean up audio resources
function cleanupAudioResources() {
  if (recorder) {
    try {
      recorder.close();
    } catch (e) {
      console.error('关闭Recorder实例时出错:', e);
    }
    recorder = null;
  }
  
  if (mediaStream) {
    try {
      mediaStream.getTracks().forEach(track => track.stop());
    } catch (e) {
      console.error('停止媒体流时出错:', e);
    }
    mediaStream = null;
  }
}

// 重置环境，每次开始录音时必须先调用此方法，清理环境
function resetRecorderEnvironment() {
  if (window.RealTimeSendReset) {
    window.RealTimeSendReset();
  } else {
    // 如果全局函数不存在，创建一个本地实现
    window.send_frameBuffer = new Uint8Array(0);
    window.send_logNumber = 0;
  }
}

// 处理录音状态变更（内部使用）
function updateRecordingState(state) {
  console.log(`[SensevoiceRecorder] 内部更新录音状态: ${state}`);
  isRecording.value = state;
  emit('recording-state-change', state);
}

// Watch loading state changes
watch(() => props.isLoading, (newValue) => {
  if (newValue === true && isRecording.value) {
    // Stop recording when AI starts responding
    stopRecording();
  } else if (newValue === false && props.voiceInputMode && !isRecording.value) {
    // Resume recording after AI response if in voice mode
    // 确保重新开始录音时，先清空上一次的文本
    recordingText.value = '';
    emit('transcript-result', '');
    startRecording();
  }
});

// Watch voice input mode changes
watch(() => props.voiceInputMode, (newMode, oldMode) => {
  console.log(`[SensevoiceRecorder] 模式更改: ${oldMode ? '语音模式' : '文字模式'} -> ${newMode ? '语音模式' : '文字模式'}`);
  
  if (newMode) {
    // 切换到语音模式，自动开始录音（但不处于长按状态）
    if (!isRecording.value && !props.isLoading && !isConnecting.value) {
      console.log('[SensevoiceRecorder] 切换到语音模式，自动开始录音');
      startRecording();
    }
  } else {
    // 切换到文字模式，停止任何正在进行的录音
    if (isRecording.value) {
      console.log('[SensevoiceRecorder] 切换到文字模式，停止录音');
      stopRecording(false); // 停止录音但不发送当前内容
    }
  }
}, { immediate: true }); // 组件加载时立即执行

// Functions for recording
// Reset the environment before recording
function resetRecordingEnvironment() {
  transcriptionList.value = [];
  recordingText.value = '';
  lastActivityTime = Date.now();
}

// Start recording
function startRecording() {
  console.log('开始录音处理，当前状态:', 
              '录音中=', isRecording.value, 
              '加载中=', props.isLoading, 
              '连接中=', isConnecting.value);
              
  if (isRecording.value) {
    console.log('已经在录音中，忽略开始请求');
    return;
  }
  
  if (props.isLoading) {
    console.log('AI正在响应，忽略录音请求');
    return;
  }
  
  if (isConnecting.value) {
    console.log('正在连接中，忽略录音请求');
    return;
  }

  console.log('开始语音录音...');
  resetRecordingEnvironment();
  reconnectAttempts = 0;
  isConnecting.value = true;
  
  // 确保清空之前的录音文本，并通知父组件
  recordingText.value = '';
  emit('transcript-result', '');

  // 只使用WSS连接
  const wsUrl = 'wss://192.168.3.60:8000/api/realtime/ws';
  
  // 连接到WebSocket
  connectToWebSocket(wsUrl);
}

// 尝试连接到WebSocket服务器
function connectToWebSocket(url) {
  console.log(`尝试连接到WebSocket: ${url}`);
  
  // 首先使用fetch尝试连接以接受证书
  const serverUrl = url.replace('wss://', 'https://').split('/api/')[0];
  console.log(`尝试先访问服务器接受证书: ${serverUrl}`);
  
  fetch(serverUrl, { 
    method: 'GET',
    mode: 'no-cors' // 使用no-cors模式
  })
  .then(() => {
    console.log('已预先访问服务器，现在尝试WebSocket连接');
    createWebSocketConnection(url);
  })
  .catch(error => {
    console.warn('预先访问服务器失败，尝试直接连接WebSocket:', error);
    createWebSocketConnection(url);
  });
}

// 创建WebSocket连接
function createWebSocketConnection(url) {
  // 设置连接超时检测
  const connectionTimeout = setTimeout(() => {
    console.error(`WebSocket连接超时: ${url}`);
    isConnecting.value = false;
    recordingError.value = true;
  }, 5000);
  
  try {
    ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    
    // 注意：connectionTimeout已在上面定义
    
    ws.onopen = function(event) {
      console.log(`WebSocket连接成功: ${url}`);
      clearTimeout(connectionTimeout);
      startRecordingAudio();
      isConnecting.value = false;
      recordingError.value = false;
    };
    
    ws.onerror = function(error) {
      console.error(`WebSocket错误: ${url}`, error);
      clearTimeout(connectionTimeout);
      recordingError.value = true;
      updateRecordingState(false);
      isConnecting.value = false;
    };
    
    ws.onclose = function(event) {
      console.log(`WebSocket连接关闭: ${url}`, event.code);
      clearTimeout(connectionTimeout);
      stopRecordingAudio();
      updateRecordingState(false);
      isConnecting.value = false;
      
      // 意外关闭时尝试重连
      if (event.code !== 1000 && event.code !== 1001 && isRecording.value) {
        console.log('意外断开，尝试重新连接...');
        reconnectTimer = setTimeout(() => attemptReconnect(), 1000);
      }
    };
    
    ws.onmessage = handleWebSocketMessage;
    
  } catch (e) {
    console.error(`创建WebSocket连接失败: ${url}`, e);
    recordingError.value = true;
    updateRecordingState(false);
    isConnecting.value = false;
  }
}

// Setup inactivity detection
function setupActivityDetection() {
  if (activityTimeoutId) {
    clearTimeout(activityTimeoutId);
  }
  
  activityTimeoutId = setTimeout(() => {
    const timeSinceLastActivity = Date.now() - lastActivityTime;
    if (timeSinceLastActivity > INACTIVITY_TIMEOUT && isRecording.value) {
      console.log(`No speech activity detected for ${INACTIVITY_TIMEOUT/1000} seconds, sending current transcript`);
      if (recordingText.value && recordingText.value.trim() && props.voiceInputMode) {
        // 只在语音模式下自动发送
        sendCurrentTranscript(true);
      } else {
        console.log('No transcript to send or not in voice mode, continuing recording');
        // Reset the timer to check again
        setupActivityDetection();
      }
    } else {
      // Reset the timer to check again
      setupActivityDetection();
    }
  }, 5000); // Check every 5 seconds
}

// 处理WebSocket消息
function handleWebSocketMessage(evt) {
  try {
    const resJson = JSON.parse(evt.data);
    
    switch (resJson["type"]) {
      case "TranscriptionResponse":
        // Update inactivity timer on any transcription
        lastActivityTime = Date.now();
        
        // Update transcription list
        if (transcriptionList.value.length <= resJson["id"]) {
          transcriptionList.value.push(resJson);
        } else {
          transcriptionList.value[resJson["id"]] = resJson;
        }
        
        // Update the current recording text
        if (resJson["data"] && resJson["data"]["raw_text"]) {
          recordingText.value = resJson["data"]["raw_text"];
          
          // Emit the transcript result - 但不发送，只通知父组件更新显示
          emit('transcript-result', recordingText.value);
          
          // Handle auto-send after silence - 但只在语音模式下启用
          if (silenceTimer) {
            clearTimeout(silenceTimer);
            silenceTimer = null;
          }
          
          // 只在语音模式下设置自动发送定时器，文字模式下禁用自动发送
          if (props.voiceInputMode && recordingText.value.trim()) {
            console.log(`设置语音自动发送定时器: ${props.voiceTimeout}秒`);
            
            // 只设置一个定时器，避免重复
            silenceTimer = setTimeout(() => {
              if (recordingText.value && recordingText.value.trim() && isRecording.value && props.voiceInputMode) {
                console.log(`检测到 ${props.voiceTimeout}秒 停顿，发送消息: "${recordingText.value}"`);
                sendCurrentTranscript(true); // true表示发送给父组件
              }
            }, props.voiceTimeout * 1000);
          }
          
          // 当检测到最终结果时，且在语音模式下，立即设置较短的定时器发送
          if (resJson["is_final"] && recordingText.value.trim() && props.voiceInputMode) {
            // 清除之前的定时器
            if (silenceTimer) {
              clearTimeout(silenceTimer);
              silenceTimer = null;
            }
            
            console.log(`收到最终结果，设置短延迟发送: "${recordingText.value}"`);
            silenceTimer = setTimeout(() => {
              if (recordingText.value && recordingText.value.trim() && isRecording.value && props.voiceInputMode) {
                console.log(`发送最终语音识别结果: "${recordingText.value}"`);
                sendCurrentTranscript(true); // true表示发送给父组件
              }
            }, 1000); // 最终结果1秒后发送
          }
        }
        break;
        
      case "VADEvent":
        // Visual feedback for voice activity detection
        console.log(`语音活动: ${resJson["is_active"]}`);
        if (resJson["is_active"]) {
          // Update activity timestamp on voice detection
          lastActivityTime = Date.now();
        }
        break;
        
      case "error":
        console.error('语音识别服务错误:', resJson["message"]);
        recordingError.value = true;
        break;
    }
  } catch (e) {
    console.error('解析WebSocket消息失败:', e);
  }
}

// Start audio recording with Recorder.js
function startRecordingAudio() {
  console.log('使用Recorder.js开始音频录制');
  
  // Clean up any existing audio resources
  cleanupAudioResources();
  
  // 重置Recorder环境
  resetRecorderEnvironment();
  
  // 实时发送音频数据处理函数
  window.RealTimeSendTry = function(chunkBytes, isClose) {
    if (chunkBytes.length > 0 && ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(chunkBytes.buffer);
      } catch (e) {
        console.error('发送音频数据时出错:', e);
      }
    }
  };
  
  // 创建录音实例
  try {
    recorder = Recorder({
      type: 'mp3',
      sampleRate: 16000,
      bitRate: 128,
      onProcess: function(buffers, powerLevel, bufferDuration, bufferSampleRate, newBufferIdx, asyncEnd) {
        // 音量大小值：0-100，实时反馈录音音量大小
        console.log('录音音量:', powerLevel);
        
        // 更新最后活动时间
        lastActivityTime = Date.now();
      },
      takeoffEncodeChunk: function(chunkBytes) {
        // 接管实时转码，推入实时处理
        window.RealTimeSendTry(chunkBytes, false);
      }
    });
    
    // 打开麦克风
    recorder.open(function() {
      // 开始录音
      recorder.start();
      console.log('Recorder.js录音已启动');
      
      // 成功启动录音，更新状态
      updateRecordingState(true);
      
      // 启动无活动检测
      setupActivityDetection();
    }, function(msg, isUserNotAllow) {
      console.error((isUserNotAllow ? '用户拒绝麦克风权限:' : '录音失败:') + msg);
      recordingError.value = true;
      updateRecordingState(false);
      isConnecting.value = false;
    });
  } catch (e) {
    console.error('创建Recorder实例失败:', e);
    recordingError.value = true;
    updateRecordingState(false);
    isConnecting.value = false;
  }
}

// Stop recording audio
function stopRecordingAudio() {
  console.log('停止音频录制');
  
  if (recorder) {
    try {
      recorder.stop(function() {
        console.log('Recorder.js录音已停止');
        // 最后一次发送
        if (window.RealTimeSendTry) {
          window.RealTimeSendTry(new Uint8Array(0), true);
        }
      }, function(msg) {
        console.error('录音停止失败:', msg);
      });
    } catch (e) {
      console.error('停止录音时出错:', e);
    }
  }
  
  cleanupAudioResources();
}

// Stop recording
function stopRecording(sendTranscript = true) {
  console.log('停止录音处理，当前状态:', 
              '录音中=', isRecording.value, 
              '连接中=', isConnecting.value,
              '发送文本=', sendTranscript);
              
  if (!isRecording.value && !isConnecting.value) {
    console.log('没有录音进行中，忽略停止请求');
    return;
  }
  
  console.log('停止录音...');
  
  // Clear timers
  cleanupTimers();
  
  // Close WebSocket
  if (ws) {
    try {
      ws.close();
      console.log('WebSocket连接已关闭');
    } catch (e) {
      console.error('关闭WebSocket时出错:', e);
    }
    ws = null;
  }
  
  // Stop recorder
  stopRecordingAudio();
  
  // 更新状态
  updateRecordingState(false);
  isConnecting.value = false;
  
  // 根据当前模式决定是否发送文本
  // 在文字模式下，只有明确要求发送时才发送
  // 在语音模式下，默认自动发送，除非明确要求不发送
  const shouldSend = props.voiceInputMode ? sendTranscript !== false : sendTranscript === true;
  
  // Send the current transcript if available and requested
  if (shouldSend && recordingText.value && recordingText.value.trim()) {
    console.log(`停止录音：将发送文本 (voiceMode=${props.voiceInputMode}, sendRequest=${sendTranscript})`);
    sendCurrentTranscript(true);
  } else {
    // 如果不需要发送，清空录音内容
    console.log(`停止录音：不发送文本 (voiceMode=${props.voiceInputMode}, sendRequest=${sendTranscript})`);
    recordingText.value = '';
    transcriptionList.value = [];
    emit('transcript-result', '');
  }
}

// Send the current transcript
function sendCurrentTranscript(sendToParent = false) {
  if (recordingText.value && recordingText.value.trim()) {
    const textToSend = recordingText.value.trim();
    console.log('准备发送文本:', textToSend, '发送到父组件:', sendToParent);
    
    // 取消任何待发送的定时器
    if (silenceTimer) {
      clearTimeout(silenceTimer);
      silenceTimer = null;
    }
    
    if (sendToParent) {
      // 触发特殊的"send-transcript"事件，表示需要发送到聊天
      emit('send-transcript', textToSend);
    } else {
      // 只更新显示但不发送到聊天
      emit('transcript-result', textToSend);
    }
    
    // Clear the text
    recordingText.value = '';
    
    // Reset transcription list
    transcriptionList.value = [];
  }
}

// Toggle recording state
function toggleRecording() {
  if (isRecording.value || isConnecting.value) {
    stopRecording();
  } else {
    startRecording();
  }
}

// Function to attempt reconnection
function attemptReconnect() {
  if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    console.error('达到最大重连次数，放弃连接');
    recordingError.value = true;
    isRecording.value = false;
    isConnecting.value = false;
    emit('recording-state-change', false);
    return;
  }
  
  reconnectAttempts++;
  console.log(`尝试重新连接 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
  
  // 只使用WSS连接
  const wsUrl = 'wss://192.168.3.60:8000/api/realtime/ws';
  connectToWebSocket(wsUrl);
}

// Expose methods to parent components
defineExpose({
  startRecording,
  stopRecording,
  toggleRecording,
  isRecording
});

// 完全重置组件状态和资源
function resetComponent() {
  console.log('重置SensevoiceRecorder组件');
  
  // 停止任何录音活动
  stopRecordingAudio();
  
  // 清理WebSocket连接
  if (ws) {
    try {
      ws.close();
    } catch (e) {
      console.error('重置组件时关闭WebSocket错误:', e);
    }
    ws = null;
  }
  
  // 清理所有计时器
  cleanupTimers();
  
  // 重置所有状态
  isRecording.value = false;
  recordingError.value = false;
  isConnecting.value = false;
  recordingText.value = '';
  transcriptionList.value = [];
  reconnectAttempts = 0;
  
  // 通知父组件
  emit('recording-state-change', false);
  emit('transcript-result', '');
}

// Lifecycle hooks
onMounted(() => {
  console.log('SensevoiceRecorder组件已挂载');
  
  // 重置组件状态
  resetComponent();
  
  // 延迟一段时间后，如果处于语音模式，自动开始录音
  setTimeout(() => {
    if (props.voiceInputMode && !isRecording.value && !props.isLoading) {
      console.log('语音模式自动开始录音');
      startRecording();
    }
  }, 500);
});
</script>

<template>
  <div class="sensevoice-recorder">
    <!-- 录音状态指示器（只对内部组件可见，不可交互） -->
    <div v-if="isRecording || isConnecting" class="recording-indicator" :class="{ 'connecting': isConnecting }">
      <div class="pulse-ring"></div>
      <div class="mic-status">
        {{ isConnecting ? '正在连接语音服务...' : '正在录音...' }}
      </div>
    </div>
    
    <!-- 当前识别文本预览 -->
    <div v-if="recordingText" class="transcript-preview" :class="{ 'connecting': isConnecting }">
      {{ recordingText }}
    </div>
  </div>
</template>

<style scoped>
.sensevoice-recorder {
  position: fixed;
  bottom: 100px;
  right: 20px;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  pointer-events: none; /* 避免干扰用户交互 */
  z-index: 50;
}

.recording-indicator {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  margin-bottom: 10px;
  background-color: rgba(255, 77, 79, 0.1);
  padding: 8px 12px;
  border-radius: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  animation: fadeIn 0.3s;
}

.recording-indicator.connecting {
  background-color: rgba(24, 144, 255, 0.1);
}

.mic-status {
  font-size: 14px;
  color: rgba(0, 0, 0, 0.6);
  margin-left: 10px;
}

.pulse-ring {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #ff4d4f;
  position: relative;
  display: inline-block;
  animation: pulse-ring 1.5s ease-out infinite;
}

.connecting .pulse-ring {
  background-color: #1890ff;
  animation: pulse-blue 1.5s ease-out infinite;
}

.transcript-preview {
  max-width: 300px;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.5;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.1);
  margin-top: 10px;
  word-break: break-word;
  animation: slideIn 0.3s;
  border-left: 3px solid #ff4d4f;
}

.transcript-preview.connecting {
  border-left: 3px solid #1890ff;
}

@keyframes pulse-ring {
  0% {
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.5);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(255, 77, 79, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0);
  }
}

@keyframes pulse-blue {
  0% {
    box-shadow: 0 0 0 0 rgba(24, 144, 255, 0.5);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(24, 144, 255, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(24, 144, 255, 0);
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateY(10px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}
</style>