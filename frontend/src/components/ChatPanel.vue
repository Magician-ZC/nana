<template>
  <div class="chat-panel" ref="chatPanelRef">
    <!-- 消息列表区域 -->
    <div class="chat-messages">
      <template v-if="chatStore.messages.length === 0">
        <!-- 空消息提示 -->
        <div class="empty-chat">
          <p>没有对话记录，开始聊天吧！</p>
        </div>
      </template>
      <template v-else>
        <!-- 渲染消息列表 -->
        <div 
          v-for="(message, index) in chatStore.messages" 
          :key="index" 
          :class="['message', message.type, { 'short-message': message.content.length <= 10 }]"
        >
          <!-- AI助手头像 -->
          <div v-if="message.type === 'assistant'" class="avatar">
            <img src="/avatars/agent.png" alt="Agent" />
          </div>
          <!-- 消息气泡 -->
          <div class="message-bubble">
            {{ message.content }}
          </div>
          <!-- 用户头像 -->
          <div v-if="message.type === 'user'" class="avatar">
            <img src="/avatars/user.png" alt="User" />
          </div>
        </div>
      </template>
      
      <!-- 加载状态显示 -->
      <div v-if="chatStore.loading" class="message assistant">
        <div class="avatar">
          <img src="/avatars/agent.png" alt="Agent" />
        </div>
        <div class="message-bubble">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
      
      <!-- 录音状态显示 -->
      <div v-if="isRecording && recordingText" class="message user recognizing">
        <div class="message-bubble">
          {{ recordingText }}
        </div>
        <div class="avatar">
          <img src="/avatars/user.png" alt="User" />
        </div>
      </div>
      
      <!-- 用于自动滚动的空div -->
      <div ref="messagesEndRef" />
    </div>
    
    <!-- 输入区域 -->
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
        :class="{ pressed: voiceButtonPressed }"
        :disabled="chatStore.loading"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
          <line x1="8" y1="23" x2="16" y2="23"></line>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'

const chatStore = useChatStore()

// 文本输入状态
const text = ref('')
// 录音状态
const isRecording = ref(false)
// 录音提示文本
const recordingText = ref('')
// 消息列表底部引用，用于自动滚动
const messagesEndRef = ref(null)
// 聊天面板引用
const chatPanelRef = ref(null)
// 媒体录制器
let mediaRecorder = null
// 语音按钮按压状态
const voiceButtonPressed = ref(false)

// 当消息列表更新时，自动滚动到底部
watch(() => chatStore.messages.length, async () => {
  await nextTick()
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
  }
})

// 开始录音的处理函数
const startRecording = async () => {
  try {
    // 请求麦克风权限并创建媒体流
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder = new MediaRecorder(stream)
    
    const audioChunks = []
    // 收集音频数据
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data)
      }
    }
    
    // 录音结束后的处理
    mediaRecorder.onstop = async () => {
      // 关闭麦克风
      stream.getTracks().forEach(track => track.stop())
      
      // 创建音频blob
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
      
      // 创建FormData对象
      const formData = new FormData()
      formData.append('audio', audioBlob)
      
      try {
        // 发送到后端进行语音识别
        const response = await fetch('http://localhost:8000/speech-to-text', {
          method: 'POST',
          body: formData
        })
        
        const result = await response.json()
        if (result.success && result.text) {
          chatStore.sendMessage(result.text)
        }
      } catch (error) {
        console.error('语音识别请求失败:', error)
      }
      
      recordingText.value = ''
    }
    
    // 开始录音
    mediaRecorder.start()
    isRecording.value = true
    recordingText.value = '正在录音...'
  } catch (error) {
    console.error('无法访问麦克风', error)
  }
}

// 结束录音的处理函数
const stopRecording = () => {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop()
    isRecording.value = false
  }
}

// 处理语音按钮按下事件
const handleVoiceButtonDown = () => {
  voiceButtonPressed.value = true
  startRecording()
}

// 处理语音按钮释放事件
const handleVoiceButtonUp = () => {
  voiceButtonPressed.value = false
  stopRecording()
}

// 处理文本消息发送
const handleSendText = () => {
  if (text.value.trim()) {
    chatStore.sendMessage(text.value.trim())
    text.value = ''
  }
}

// 处理回车键发送消息
const handleKeyDown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendText()
  }
}

onMounted(() => {
  // 在组件挂载后显示欢迎消息
  chatStore.showWelcomeMessage()
  
  // 初始滚动到底部
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'auto' })
  }
})

onUnmounted(() => {
  // 确保在组件卸载时停止录音
  if (isRecording.value) {
    stopRecording()
  }
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  width: 400px;
  height: 50vh;
  max-height: 50vh;
  background-color: rgba(30, 30, 30, 0.85);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  position: fixed;
  right: 30px;
  bottom: 30px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.empty-chat {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  opacity: 0.5;
  color: #cccccc;
}

.message {
  display: flex;
  align-items: flex-end;
  margin-bottom: 15px;
  max-width: 90%;
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-bubble {
  padding: 10px 15px;
  border-radius: 18px;
  background-color: #4a6fa5;
  color: white;
  max-width: 85%;
  word-break: break-word;
  line-height: 1.4;
}

.user .message-bubble {
  background-color: #2c7c7e;
  border-bottom-right-radius: 4px;
}

.assistant .message-bubble {
  background-color: #454654;
  border-bottom-left-radius: 4px;
}

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  margin: 0 8px;
  flex-shrink: 0;
  overflow: hidden;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.short-message .message-bubble {
  padding-left: 15px;
  padding-right: 15px;
}

.chat-input-area {
  padding: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(40, 40, 40, 0.5);
  display: flex;
  align-items: center;
  gap: 10px;
}

.input-container {
  flex: 1;
  position: relative;
  border-radius: 24px;
  background-color: rgba(60, 60, 60, 0.7);
  display: flex;
  align-items: center;
}

.input-container.recording {
  background-color: rgba(80, 40, 40, 0.7);
  padding: 12px 15px;
  justify-content: center;
}

textarea {
  width: 100%;
  border: none;
  background-color: transparent;
  padding: 12px 50px 12px 15px;
  color: white;
  resize: none;
  border-radius: 24px;
  outline: none;
  max-height: 120px;
  font-family: inherit;
  font-size: 14px;
}

.send-button {
  position: absolute;
  right: 5px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  background-color: #2c7c7e;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.3s;
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

.typing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  height: 20px;
}

.typing-indicator span {
  display: block;
  width: 8px;
  height: 8px;
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
  gap: 3px;
  height: 20px;
}

.voice-wave .wave {
  display: block;
  width: 3px;
  height: 20px;
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

.recognizing .message-bubble {
  background-color: #87556c;
  font-style: italic;
}
</style> 