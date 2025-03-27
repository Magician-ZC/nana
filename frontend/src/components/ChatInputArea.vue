<template>
  <div class="chat-input-area">
    <div :class="['input-container', { recording: isRecording }]">
      <template v-if="isRecording">
        <!-- 录音波形动画 -->
        <div class="voice-wave">
          <div class="wave"></div>
          <div class="wave"></div>
          <div class="wave"></div>
          <div class="wave"></div>
          <div class="wave"></div>
        </div>
      </template>
      <template v-else>
        <!-- 文本输入框 -->
        <textarea 
          v-model="text" 
          @keydown="handleKeyDown" 
          placeholder="输入消息或按住语音按钮说话..." 
          rows="1"
        ></textarea>
        
        <!-- 发送按钮 -->
        <button 
          class="send-button" 
          @click="handleSendText" 
          :disabled="!text.trim() || chatStore.loading"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
        </button>
      </template>
    </div>
    
    <!-- 语音按钮 -->
    <button 
      class="voice-button" 
      @mousedown="handleVoiceButtonDown" 
      @mouseup="handleVoiceButtonUp" 
      @mouseleave="handleVoiceButtonUp"
      @touchstart.prevent="handleVoiceButtonDown" 
      @touchend.prevent="handleVoiceButtonUp"
      @touchcancel.prevent="handleVoiceButtonUp"
      :class="{ 
        pressed: voiceButtonPressed, 
        'not-supported': !microphoneSupported 
      }"
      :title="microphoneSupported ? '按住说话' : '此设备不支持语音输入'"
      :disabled="chatStore.loading || !microphoneSupported"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
        <line x1="12" y1="19" x2="12" y2="23"></line>
        <line x1="8" y1="23" x2="16" y2="23"></line>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useChatStore } from '../stores/chat'

const props = defineProps({
  isMobile: {
    type: Boolean,
    default: false
  }
})

const chatStore = useChatStore()

// 检测设备类型
const isIOS = ref(/iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream)
const isAndroid = ref(/Android/.test(navigator.userAgent))
const isSecureContext = ref(window.isSecureContext)

// 文本输入状态
const text = ref('')
// 录音状态
const isRecording = ref(false)
// 录音提示文本
const recordingText = ref('')
// 媒体录制器
let mediaRecorder = null
// 语音按钮按压状态
const voiceButtonPressed = ref(false)

// 检测麦克风支持状态
const microphoneSupported = ref(true)

// 添加formatTime函数
function formatTime() {
  const now = new Date()
  return {
    time: now,
    hours: now.getHours().toString().padStart(2, '0'),
    minutes: now.getMinutes().toString().padStart(2, '0')
  }
}

// 处理键盘事件
function handleKeyDown(e) {
  // 按下Enter键发送消息，除非同时按下Shift键
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendText()
  }
}

// 处理发送文本消息
function handleSendText() {
  const trimmedText = text.value.trim()
  if (!trimmedText || chatStore.loading) return
  
  // 发送消息到store
  chatStore.sendMessage(trimmedText)
  
  // 清空输入框
  text.value = ''
  
  // 通知父组件消息发送完成，用于滚动到底部
  nextTick(() => {
    document.dispatchEvent(new CustomEvent('message-sent'))
  })
}

// 语音按钮按下事件
function handleVoiceButtonDown() {
  if (chatStore.loading || !microphoneSupported.value) return
  
  voiceButtonPressed.value = true
  startRecording().catch(error => {
    // 额外的错误处理，以防startRecording的catch块没有捕获所有错误
    console.error('录音启动异常:', error)
    voiceButtonPressed.value = false
  })
}

// 语音按钮释放事件
function handleVoiceButtonUp() {
  if (!voiceButtonPressed.value) return
  
  voiceButtonPressed.value = false
  stopRecording()
}

// 开始录音
async function startRecording() {
  try {
    // 改进检查浏览器媒体设备API支持的方式
    if (!navigator.mediaDevices && !navigator.getUserMedia && !navigator.webkitGetUserMedia && 
        !navigator.mozGetUserMedia && !navigator.msGetUserMedia) {
      throw new Error('您的浏览器不支持媒体设备API');
    }

    // 使用兼容多浏览器的方式获取媒体流
    let stream;
    
    // 优先使用现代API
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } 
    // 回退到旧版API
    else {
      // 创建兼容不同浏览器的getUserMedia函数
      const getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia ||
                         navigator.mozGetUserMedia || navigator.msGetUserMedia;
      
      if (!getUserMedia) {
        throw new Error('您的浏览器不支持媒体录制');
      }
      
      // 使用Promise包装旧版API
      stream = await new Promise((resolve, reject) => {
        getUserMedia.call(navigator, { audio: true }, resolve, reject);
      });
    }
    
    // 创建媒体录制器
    // 检查是否支持MediaRecorder
    if (typeof MediaRecorder === 'undefined') {
      throw new Error('您的浏览器不支持MediaRecorder');
    }
    
    mediaRecorder = new MediaRecorder(stream)
    const audioChunks = []
    
    // 收集录音数据
    mediaRecorder.addEventListener('dataavailable', event => {
      audioChunks.push(event.data)
    })
    
    // 录音结束后处理
    mediaRecorder.addEventListener('stop', async () => {
      // 关闭所有音轨
      stream.getTracks().forEach(track => track.stop())
      
      // 如果没有录音数据或录音太短，忽略
      if (audioChunks.length === 0 || recordingText.value.trim() === '') {
        isRecording.value = false
        recordingText.value = ''
        return
      }
      
      // 发送语音消息到store
      const message = recordingText.value.trim()
      chatStore.sendMessage(message)
      
      // 重置录音状态
      isRecording.value = false
      recordingText.value = ''
      
      // 通知消息发送完成
      nextTick(() => {
        document.dispatchEvent(new CustomEvent('message-sent'))
      })
    })
    
    // 开始录音
    mediaRecorder.start()
    isRecording.value = true
    
    // 开始语音识别
    startSpeechRecognition()
  } catch (error) {
    console.error('录音失败:', error)
    // 重置按钮状态
    voiceButtonPressed.value = false
    isRecording.value = false
    
    // 提供更友好的错误信息
    let errorMessage = '无法访问麦克风，请检查浏览器权限设置。';
    
    // 针对iOS设备的特殊处理
    if (isIOS.value) {
      errorMessage = '您使用的是iOS设备，请确保在Safari浏览器中访问并已授予麦克风权限。';
    }
    
    // 针对Android设备的特殊处理
    if (isAndroid.value) {
      errorMessage = '您使用的是Android设备，请确保授予麦克风权限并使用Chrome或Firefox浏览器。';
    }
    
    // 检查是否为安全上下文
    if (!isSecureContext.value && window.location.hostname !== 'localhost') {
      errorMessage = '麦克风访问需要安全连接(HTTPS)，请使用HTTPS访问本站。';
    }
    
    alert(errorMessage + '\n\n技术详情: ' + error.message);
  }
}

// 停止录音
function stopRecording() {
  try {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
  } catch (error) {
    console.error('停止录音失败:', error)
  } finally {
    // 无论如何都停止语音识别
    stopSpeechRecognition()
    // 确保状态被重置
    setTimeout(() => {
      // 使用setTimeout确保状态重置在UI更新循环中
      isRecording.value = false
      voiceButtonPressed.value = false
    }, 0)
  }
}

// 语音识别实例
let recognition = null

// 开始语音识别
function startSpeechRecognition() {
  // 检查浏览器是否支持语音识别
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition || 
                          window.mozSpeechRecognition || window.msSpeechRecognition;
  
  if (!SpeechRecognition) {
    console.warn('浏览器不支持语音识别，将仅进行录音');
    // 在移动设备上设置一个默认的提示文本
    if (props.isMobile) {
      recordingText.value = '正在录音... (语音识别不可用)';
    }
    // 继续录音过程，但不启动识别
    return;
  }
  
  try {
    // 创建识别实例
    recognition = new SpeechRecognition();
    
    // 设置识别参数
    recognition.lang = 'zh-CN';
    recognition.continuous = true;
    recognition.interimResults = true;
    
    // 设置超时
    let recognitionTimeout;
    
    // 处理识别结果
    recognition.onresult = (event) => {
      // 清除之前的超时
      if (recognitionTimeout) {
        clearTimeout(recognitionTimeout);
      }
      
      let interimTranscript = '';
      let finalTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }
      
      // 更新显示文本
      recordingText.value = finalTranscript || interimTranscript;
      
      // 设置新的超时来处理可能的识别停止问题
      recognitionTimeout = setTimeout(() => {
        try {
          // 如果识别似乎停止了，尝试重新启动
          if (recognition && isRecording.value) {
            recognition.stop();
            setTimeout(() => {
              if (isRecording.value) {
                recognition.start();
              }
            }, 100);
          }
        } catch (error) {
          console.warn('重新启动语音识别失败:', error);
        }
      }, 5000); // 5秒无结果就重试
    };
    
    // 处理错误
    recognition.onerror = (event) => {
      console.warn('语音识别错误:', event.error);
      
      // 检查错误类型
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        // 权限错误时提供反馈
        recordingText.value = '无法访问麦克风，请检查权限';
      } else if (event.error === 'network') {
        // 网络错误
        recordingText.value = '网络错误，语音识别不可用';
      } else if (props.isMobile) {
        // 移动设备上的其他错误，提供默认文本
        recordingText.value = '正在录音... (语音识别受限)';
      }
      
      // 继续录音过程，识别错误不影响录音本身
    };
    
    // 当识别停止时尝试重新启动(如果仍在录音)
    recognition.onend = () => {
      if (isRecording.value) {
        try {
          recognition.start();
        } catch (error) {
          console.warn('重新启动语音识别失败:', error);
        }
      }
    };
    
    // 开始识别
    recognition.start();
  } catch (error) {
    console.warn('启动语音识别失败:', error);
    
    // 在移动设备上设置一个默认的提示文本
    if (props.isMobile) {
      recordingText.value = '正在录音... (语音识别不可用)';
    }
    
    // 继续录音过程，识别失败不影响录音本身
  }
}

// 停止语音识别
function stopSpeechRecognition() {
  try {
    if (recognition) {
      recognition.stop()
      recognition = null
    }
  } catch (error) {
    console.error('停止语音识别失败:', error)
    recognition = null
  }
}

// 导出录音状态和文本，以便父组件可以访问
defineExpose({
  isRecording,
  recordingText,
  formatTime
})

// 组件挂载时检测麦克风支持
async function checkMicrophoneSupport() {
  try {
    // 检查是否支持mediaDevices API
    if (!navigator.mediaDevices && !navigator.getUserMedia && !navigator.webkitGetUserMedia && 
        !navigator.mozGetUserMedia && !navigator.msGetUserMedia) {
      microphoneSupported.value = false;
      return;
    }
    
    // 检查MediaRecorder是否可用
    if (typeof MediaRecorder === 'undefined') {
      microphoneSupported.value = false;
      return;
    }
    
    // 在iOS上检查AudioContext支持
    if (isIOS.value && typeof (window.AudioContext || window.webkitAudioContext) === 'undefined') {
      microphoneSupported.value = false;
      return;
    }
    
    // 如果不是安全上下文且不是localhost，麦克风将不可用
    if (!isSecureContext.value && window.location.hostname !== 'localhost') {
      microphoneSupported.value = false;
      return;
    }
    
    // 一切正常
    microphoneSupported.value = true;
  } catch (error) {
    console.warn('检测麦克风支持失败:', error);
    microphoneSupported.value = false;
  }
}

onMounted(() => {
  // 检测麦克风支持
  checkMicrophoneSupport();
  
  // 监听消息发送事件，以便重置状态
  document.addEventListener('message-sent', handleMessageSent);
})

function handleMessageSent() {
  // 消息发送后的回调，可以在这里添加额外逻辑
}

onUnmounted(() => {
  // 确保在组件卸载时停止录音
  if (isRecording.value) {
    stopRecording();
  }
  
  // 移除事件监听器
  document.removeEventListener('message-sent', handleMessageSent);
})
</script>

<style scoped>
.chat-input-area {
  padding: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
  z-index: 15;
  border-radius: 0;
  pointer-events: auto; /* 输入区域可以捕获事件 */
}

@media (max-width: 768px) {
  .chat-input-area {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 10px 15px;
    background-color: rgba(30, 30, 30, 0.7);
    backdrop-filter: blur(10px);
    z-index: 999;
  }
}

.input-container {
  flex: 1;
  position: relative;
  border-radius: 24px;
  -webkit-border-radius: 24px;
  -moz-border-radius: 24px;
  background-color: rgba(60, 60, 60, 0.7);
  display: flex;
  align-items: center;
  overflow: hidden;
  -webkit-mask-image: -webkit-radial-gradient(white, black);
  z-index: 15;
  pointer-events: auto; /* 确保可交互 */
}

.input-container::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 24px;
  pointer-events: none; /* 确保不阻止交互 */
}

.input-container.recording {
  background-color: rgba(80, 40, 40, 0.7);
  padding: 12px 15px;
  justify-content: center;
}

textarea {
  width: 100%;
  height: auto;
  border: none;
  background-color: transparent;
  padding: 12px 50px 12px 15px;
  color: white;
  resize: none;
  border-radius: 0; /* 移除textarea的圆角，让容器控制圆角 */
  outline: none;
  max-height: 120px;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.4;
}

.send-button {
  position: absolute;
  right: 8px; /* 稍微调整位置，避免太靠近边缘 */
  width: 36px; /* 略微减小尺寸 */
  height: 36px;
  border-radius: 50%;
  border: none;
  background-color: #2c7c7e;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.3s;
  z-index: 20; /* 确保在最上层且可交互 */
}

.send-button:hover {
  background-color: #3a9a9c;
}

.send-button:disabled {
  background-color: #444;
  cursor: not-allowed;
}

.voice-button {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: none;
  background-color: #4a6fa5;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  z-index: 20; /* 确保可交互 */
  touch-action: none; /* 防止移动设备上的默认行为 */
  user-select: none; /* 防止文本选择 */
  -webkit-user-select: none;
  -webkit-tap-highlight-color: transparent; /* 移除iOS上的点击高亮 */
}

@media (max-width: 768px) {
  .voice-button {
    width: 52px; /* 在移动设备上略微增大按钮 */
    height: 52px;
  }
}

.voice-button:hover {
  background-color: #5788cc;
}

.voice-button.pressed {
  background-color: #953e3e;
  transform: scale(1.1);
}

.voice-button:disabled {
  background-color: #444;
  cursor: not-allowed;
}

.voice-button.not-supported {
  background-color: #888;
  opacity: 0.7;
  cursor: not-allowed;
}

.voice-button.not-supported:hover {
  background-color: #888;
  transform: none;
}

.typing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 16px;
}

.typing-indicator span {
  display: block;
  width: 6px;
  height: 6px;
  background-color: rgba(255, 255, 255, 0.6);
  border-radius: 50%;
  animation: typing 1.5s infinite ease;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-6px);
  }
}

.voice-wave {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  height: 16px;
}

.voice-wave .wave {
  display: block;
  width: 2px;
  height: 16px;
  background-color: rgba(255, 255, 255, 0.6);
  animation: wave 1s infinite ease-in-out;
  border-radius: 2px;
}

.voice-wave .wave:nth-child(2) {
  animation-delay: 0.2s;
}

.voice-wave .wave:nth-child(3) {
  animation-delay: 0.4s;
}

.voice-wave .wave:nth-child(4) {
  animation-delay: 0.6s;
}

.voice-wave .wave:nth-child(5) {
  animation-delay: 0.8s;
}

@keyframes wave {
  0%, 100% {
    height: 5px;
  }
  50% {
    height: 20px;
  }
}

/* 确保按钮可交互 */
.send-button, .voice-button, textarea {
  pointer-events: auto;
}
</style> 