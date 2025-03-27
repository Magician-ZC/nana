<template>
  <div class="chat-panel" ref="chatPanelRef">
    <!-- 消息列表区域 -->
    <div class="chat-messages" ref="chatMessagesRef" @scroll="handleScroll">
      <template v-if="chatStore.messages.length === 0">
        <!-- 空消息提示 -->
        <div class="empty-chat">
          <p>没有对话记录，开始聊天吧！</p>
        </div>
      </template>
      <template v-else>
        <!-- 渲染消息列表 -->
        <div 
          v-for="(message, index) in sortedMessages" 
          :key="index" 
        >
          <!-- 消息时间戳，独立于消息之外，在消息上方显示 -->
          <div v-if="shouldShowTimestamp(message, index)" class="message-timestamp">
            {{ formatDisplayTime(message.timestamp) }}
          </div>
          
          <!-- 消息分组 - 显示agent变更 -->
          <div v-if="shouldShowAgentChange(message, index)" class="agent-change-notice">
            切换到 {{ getAgentName(message.agentId) }}
          </div>
          
          <div :class="['message', message.type, { 
            'short-message': message.content && message.content.length <= 10,
            'current-agent': message.agentId === chatStore.currentAgent,
            'other-agent': message.agentId && message.agentId !== chatStore.currentAgent
          }]">
            <!-- AI助手头像 -->
            <div v-if="message.type === 'assistant'" class="avatar">
              <img :src="getAgentAvatar(message.agentId)" :alt="getAgentName(message.agentId)" />
            </div>
            
            <!-- 消息内容区域 -->
            <div class="message-content">
              <!-- 所有助手消息都显示名称 -->
              <div v-if="message.type === 'assistant'" class="message-sender">
                {{ getAgentName(message.agentId) }}
              </div>
              
              <!-- 消息气泡 -->
              <div v-if="message.content || message.isStreaming" :class="['message-bubble', { 'typing': message.isStreaming }]">
                {{ message.content || '' }}
              </div>
            </div>
            
            <!-- 用户头像 -->
            <div v-if="message.type === 'user'" class="avatar">
              <img src="/avatars/user.png" alt="User" />
            </div>
          </div>
        </div>
      </template>
      
      <!-- 加载状态显示 -->
      <div v-if="chatStore.loading && !hasStreamingMessage">
        <!-- 时间戳 -->
        <div class="message-timestamp">
          {{ formatDisplayTime(formatTime()) }}
        </div>
        
        <div class="message assistant">
          <div class="avatar">
            <img :src="getAgentAvatar(chatStore.currentAgent)" :alt="getAgentName(chatStore.currentAgent)" />
          </div>
          <div class="message-content">
            <div class="message-bubble">
              <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 录音状态显示 -->
      <div v-if="isRecording && recordingText">
        <!-- 时间戳 -->
        <div class="message-timestamp">
          {{ formatDisplayTime(formatTime()) }}
        </div>
        
        <div class="message user recognizing">
          <div class="message-content">
            <div class="message-bubble">
              {{ recordingText }}
            </div>
          </div>
          <div class="avatar">
            <img src="/avatars/user.png" alt="User" />
          </div>
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
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
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
// 消息容器引用
const chatMessagesRef = ref(null)
// 媒体录制器
let mediaRecorder = null
// 语音按钮按压状态
const voiceButtonPressed = ref(false)

// 添加formatTime函数
function formatTime() {
  const now = new Date()
  return {
    time: now,
    hours: now.getHours().toString().padStart(2, '0'),
    minutes: now.getMinutes().toString().padStart(2, '0')
  }
}

// 格式化显示时间
function formatDisplayTime(timestamp) {
  if (!timestamp || !timestamp.time) return ''
  
  const now = new Date()
  const messageTime = new Date(timestamp.time)
  
  // 检查是否为同一天
  const isToday = messageTime.getDate() === now.getDate() && 
                  messageTime.getMonth() === now.getMonth() && 
                  messageTime.getFullYear() === now.getFullYear()
  
  // 检查是否为昨天
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const isYesterday = messageTime.getDate() === yesterday.getDate() && 
                      messageTime.getMonth() === yesterday.getMonth() && 
                      messageTime.getFullYear() === yesterday.getFullYear()
  
  if (isToday) {
    return `${timestamp.hours}:${timestamp.minutes}`
  } else if (isYesterday) {
    return `昨天 ${timestamp.hours}:${timestamp.minutes}`
  } else {
    // 其他日期显示完整日期
    const month = (messageTime.getMonth() + 1).toString().padStart(2, '0')
    const day = messageTime.getDate().toString().padStart(2, '0')
    return `${month}-${day} ${timestamp.hours}:${timestamp.minutes}`
  }
}

// 判断是否需要显示agent变更提示
function shouldShowAgentChange(message, index) {
  if (index === 0 || !message.agentId) return false
  
  // 如果当前消息的agentId与前一条不同，则显示变更提示
  const prevMessage = chatStore.messages[index - 1]
  return message.agentId !== prevMessage.agentId && message.type === 'assistant'
}

// 获取agent名称
function getAgentName(agentId) {
  if (!agentId) return '未知'
  
  const agentNames = {
    'nanaA': '娜娜A - 傲娇猫娘',
    'nanaB': '娜娜B - 知性大姐姐',
    'nanaC': '娜娜C - 元气少女'
  }
  
  // 对于自定义agent，从store中获取名称
  if (agentId?.startsWith('custom_')) {
    const customAgent = chatStore.agents?.find(agent => agent.id === agentId)
    return customAgent ? customAgent.name : '自定义角色'
  }
  
  return agentNames[agentId] || agentId
}

// 获取agent头像
function getAgentAvatar(agentId) {
  if (!agentId) return '/avatars/nanaA.png'
  
  if (agentId === 'nanaA') return '/avatars/nanaA.png'
  if (agentId === 'nanaB') return '/avatars/nanaB.png'
  if (agentId === 'nanaC') return '/avatars/nanaC.png'
  
  // 对于自定义agent，从store中获取头像
  if (agentId?.startsWith('custom_')) {
    const customAgent = chatStore.agents?.find(agent => agent.id === agentId)
    return customAgent?.avatar || '/avatars/default.png'
  }
  
  return '/avatars/default.png'
}

// 判断是否显示时间戳
function shouldShowTimestamp(message, index) {
  // 第一条消息总是显示时间戳
  if (index === 0) return true
  
  // 如果没有时间戳，不显示
  if (!message.timestamp || !message.timestamp.time) return false
  
  const prevMessage = chatStore.messages[index - 1]
  
  // 如果前一条没有时间戳，显示当前时间戳
  if (!prevMessage.timestamp || !prevMessage.timestamp.time) return true
  
  // 计算与前一条消息的时间差
  const currTime = new Date(message.timestamp.time)
  const prevTime = new Date(prevMessage.timestamp.time)
  const diffMinutes = (currTime - prevTime) / (1000 * 60)
  
  // 如果时间差大于5分钟，显示时间戳
  return diffMinutes > 5
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
  chatStore.sendUserMessage(trimmedText, formatTime())
  
  // 清空输入框
  text.value = ''
  
  // 滚动到底部
  nextTick(() => {
    if (messagesEndRef.value) {
      messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
    }
  })
}

// 语音按钮按下事件
function handleVoiceButtonDown() {
  if (chatStore.loading) return
  
  voiceButtonPressed.value = true
  startRecording()
}

// 语音按钮释放事件
function handleVoiceButtonUp() {
  if (!isRecording.value) return
  
  voiceButtonPressed.value = false
  stopRecording()
}

// 开始录音
async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    
    // 创建媒体录制器
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
      chatStore.sendUserMessage(message, formatTime())
      
      // 重置录音状态
      isRecording.value = false
      recordingText.value = ''
      
      // 滚动到底部
      nextTick(() => {
        if (messagesEndRef.value) {
          messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
        }
      })
    })
    
    // 开始录音
    mediaRecorder.start()
    isRecording.value = true
    
    // 开始语音识别
    startSpeechRecognition()
  } catch (error) {
    console.error('录音失败:', error)
    alert('无法访问麦克风，请检查浏览器权限设置。')
  }
}

// 停止录音
function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
    stopSpeechRecognition()
  }
}

// 语音识别实例
let recognition = null

// 开始语音识别
function startSpeechRecognition() {
  // 检查浏览器是否支持语音识别
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    console.error('浏览器不支持语音识别')
    return
  }
  
  // 创建识别实例
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true
  
  // 处理识别结果
  recognition.onresult = (event) => {
    let interimTranscript = ''
    let finalTranscript = ''
    
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      const transcript = event.results[i][0].transcript
      if (event.results[i].isFinal) {
        finalTranscript += transcript
      } else {
        interimTranscript += transcript
      }
    }
    
    // 更新显示文本
    recordingText.value = finalTranscript || interimTranscript
  }
  
  // 处理错误
  recognition.onerror = (event) => {
    console.error('语音识别错误:', event.error)
  }
  
  // 开始识别
  recognition.start()
}

// 停止语音识别
function stopSpeechRecognition() {
  if (recognition) {
    recognition.stop()
    recognition = null
  }
}

// 处理消息容器滚动事件，实现消息透明度渐变效果
function handleScroll() {
  if (!chatMessagesRef.value) return;
  
  const messages = chatMessagesRef.value.querySelectorAll('.message');
  const scrollTop = chatMessagesRef.value.scrollTop;
  const containerHeight = chatMessagesRef.value.clientHeight;
  
  messages.forEach(message => {
    // 获取消息的位置信息
    const rect = message.getBoundingClientRect();
    const messageTop = rect.top;
    const panelTop = chatPanelRef.value.getBoundingClientRect().top;
    
    // 计算消息距离顶部的相对位置
    const relativePosition = messageTop - panelTop;
    
    // 根据消息位置计算透明度
    // 当消息接近顶部时，增加透明度
    let opacity = 1;
    if (relativePosition < containerHeight * 0.3) {
      // 在容器30%高度内开始渐变
      opacity = relativePosition / (containerHeight * 0.3);
      opacity = Math.max(0.2, opacity); // 最小透明度为0.2
    }
    
    // 设置消息和头像的透明度
    message.style.setProperty('--message-opacity', opacity);
    const avatar = message.querySelector('.avatar');
    if (avatar) {
      avatar.style.setProperty('--avatar-opacity', opacity);
    }
  });
}

// 计算按时间排序的消息列表
const sortedMessages = computed(() => {
  return [...chatStore.messages].sort((a, b) => {
    // 如果两者都有时间戳，按时间排序
    if (a.timestamp && b.timestamp) {
      return new Date(a.timestamp.time) - new Date(b.timestamp.time);
    }
    // 如果没有时间戳，按原始顺序排序
    return chatStore.messages.indexOf(a) - chatStore.messages.indexOf(b);
  });
})

// 检查是否有正在流式传输的消息
const hasStreamingMessage = computed(() => {
  return chatStore.messages.some(message => message.isStreaming === true);
})

onMounted(() => {
  // 在组件挂载后显示欢迎消息
  chatStore.showWelcomeMessage()
  
  // 初始滚动到底部
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'auto' })
  }
  
  // 初始化透明度效果
  nextTick(() => {
    handleScroll();
  });
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
  height: auto; /* 不再限制固定高度 */
  max-height: 80vh; /* 调整为更大的值，但仍设置最大高度防止超出屏幕 */
  background-color: rgba(30, 30, 30, 0.5); /* 增加透明度 */
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  position: fixed;
  right: 30px;
  bottom: 30px;
  z-index: 1000;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 5px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 60%, rgba(0, 0, 0, 0) 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 60%, rgba(0, 0, 0, 0) 100%);
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
  margin-bottom: 16px;
  position: relative;
  align-items: flex-start;
  transition: opacity 0.3s ease;
}

.message.user {
  flex-direction: row;
  justify-content: flex-end;
}

.message.assistant {
  flex-direction: row;
  justify-content: flex-start;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 8px;
  flex-shrink: 0;
  position: relative;
  top: 0;
  transition: opacity 0.3s ease;
  opacity: var(--avatar-opacity, 1);
}

.message.assistant .avatar {
  margin-top: 0;
}

.message.user .avatar {
  margin-top: 0;
}

.avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 消息内容区域 */
.message-content {
  display: flex;
  flex-direction: column;
  max-width: 70%;
}

/* 发送者名称 */
.message-sender {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
  padding-left: 10px;
}

/* 消息气泡 */
.message-bubble {
  padding: 10px 15px;
  border-radius: 18px;
  position: relative;
  word-break: break-word;
  line-height: 1.5;
  font-size: 15px;
}

/* 添加打字机光标效果 */
.message-bubble.typing::after {
  content: "|";
  animation: blink 0.7s infinite;
  font-weight: bold;
  margin-left: 1px;
  display: inline-block;
  vertical-align: middle;
  line-height: 1;
  font-size: 16px;
  height: 16px;
}

.user .message-bubble.typing::after {
  color: #000;
}

.assistant .message-bubble.typing::after {
  color: #000;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.user .message-bubble {
  background-color: #95ec69;
  color: #000;
}

.assistant .message-bubble {
  background-color: #fff;
  color: #000;
}

/* 时间戳 */
.message-timestamp {
  font-size: 12px;
  color: #999;
  margin-top: 5px;
  display: block;
  text-align: center;
  padding: 10px 0;
}

/* 其他agent的消息样式 */
.message.other-agent .message-bubble {
  background-color: #f0f0f0;
}

/* agent变更提示 */
.agent-change-notice {
  width: 70%;
  text-align: center;
  font-size: 12px;
  color: #fff;
  margin: 10px auto;
  padding: 5px 10px;
  background-color: rgba(80, 80, 80, 0.7);
  border-radius: 12px;
  position: relative;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

/* 针对短消息的特殊样式 */
.short-message .message-bubble {
  padding: 8px 12px;
}

/* 录音中的样式 */
.recognizing .message-bubble {
  background-color: rgba(149, 236, 105, 0.7);
}

.chat-input-area {
  padding: 15px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background-color: rgba(40, 40, 40, 1); /* 完全不透明 */
  display: flex;
  align-items: center;
  gap: 10px;
  position: relative;
  z-index: 2;
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
</style> 