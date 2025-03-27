<template>
  <div class="chat-panel" ref="chatPanelRef">
    <!-- 消息列表区域，仅在非移动端显示 -->
    <div v-if="!isMobile" class="chat-messages" ref="chatMessagesRef" @scroll="handleScroll">
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
              <div v-if="message.content || message.isStreaming" 
                   :class="['message-bubble', { 
                     'typing': message.isStreaming,
                     'cleared': message.shouldClear 
                   }]">
                {{ message.shouldClear ? '' : (message.content || '') }}
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
      <div v-if="chatInputAreaRef && chatInputAreaRef.isRecording && chatInputAreaRef.recordingText">
        <!-- 时间戳 -->
        <div class="message-timestamp">
          {{ formatDisplayTime(formatTime()) }}
        </div>
        
        <div class="message user recognizing">
          <div class="message-content">
            <div class="message-bubble">
              {{ chatInputAreaRef.recordingText }}
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
    
    <!-- 使用新的输入区域组件 -->
    <ChatInputArea ref="chatInputAreaRef" :is-mobile="isMobile" />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatInputArea from './ChatInputArea.vue'

const props = defineProps({
  isMobile: {
    type: Boolean,
    default: false
  }
})

const chatStore = useChatStore()

// 检测设备类型
// const isMobile = ref(/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent))
const isIOS = ref(/iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream)
const isAndroid = ref(/Android/.test(navigator.userAgent))
const isSecureContext = ref(window.isSecureContext)

// 保留消息列表底部引用，用于自动滚动
const messagesEndRef = ref(null)
// 聊天面板引用
const chatPanelRef = ref(null)
// 消息容器引用
const chatMessagesRef = ref(null)

// 引用ChatInputArea组件
const chatInputAreaRef = ref(null)

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
  
  if (agentId === 'nanaA') return '/avatars/agent.png'
  if (agentId === 'nanaB') return '/avatars/agent.png'
  if (agentId === 'nanaC') return '/avatars/agent.png'
  
  // 对于自定义agent，从store中获取头像
  if (agentId?.startsWith('custom_')) {
    const customAgent = chatStore.agents?.find(agent => agent.id === agentId)
    return customAgent?.avatar || '/avatars/agent.png'
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

// 监听消息变化，自动滚动到底部
watch(() => chatStore.messages.length, () => {
  nextTick(() => {
    if (messagesEndRef.value) {
      messagesEndRef.value.scrollIntoView({ behavior: 'smooth' });
    }
  });
});

// 监听正在流式传输的消息变化，保持滚动到底部
watch(hasStreamingMessage, (newVal) => {
  if (newVal) {
    nextTick(() => {
      if (messagesEndRef.value) {
        messagesEndRef.value.scrollIntoView({ behavior: 'smooth' });
      }
    });
  }
});

// 监听最新消息的内容变化，确保在流式传输过程中保持滚动
watch(
  () => {
    const lastMsg = chatStore.messages[chatStore.messages.length - 1];
    return lastMsg ? lastMsg.content : null;
  },
  () => {
    if (chatStore.messages.length > 0) {
      const lastMsg = chatStore.messages[chatStore.messages.length - 1];
      if (lastMsg && lastMsg.isStreaming) {
        nextTick(() => {
          if (messagesEndRef.value) {
            messagesEndRef.value.scrollIntoView({ behavior: 'smooth' });
          }
        });
      }
    }
  }
);

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
  
  // 添加消息发送事件监听器，用于滚动到底部
  document.addEventListener('message-sent', handleMessageSent);
})

onUnmounted(() => {
  // 移除事件监听器
  document.removeEventListener('message-sent', handleMessageSent);
})

// 处理消息发送事件
function handleMessageSent() {
  nextTick(() => {
    if (messagesEndRef.value) {
      messagesEndRef.value.scrollIntoView({ behavior: 'smooth' });
    }
  });
}
</script>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  width: 400px;
  height: auto;
  max-height: 80vh;
  background-color: transparent; /* 完全透明 */
  border-radius: 20px;
  overflow: hidden;
  box-shadow: none; /* 移除阴影 */
  backdrop-filter: none; /* 移除背景模糊效果 */
  position: fixed;
  right: 30px;
  bottom: 30px;
  z-index: 10; /* 从1000降低到10，放置在底层 */
  pointer-events: none; /* 整个面板默认不捕获事件 */
}

/* 移动端适配 */
@media (max-width: 768px) {
  .chat-panel {
    width: 100%;
    right: 0;
    left: 0;
    bottom: 70px; /* 放在发送区域上方 */
    max-height: 60vh; /* 调整最大高度 */
    padding: 0 10px;
  }
  
  .chat-messages {
    mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 85%, rgba(0, 0, 0, 0) 100%);
    -webkit-mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 85%, rgba(0, 0, 0, 0) 100%);
  }
}

/* 移除之前添加的before伪元素 */
.chat-panel::before {
  display: none;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 5px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 70%, rgba(0, 0, 0, 0) 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 70%, rgba(0, 0, 0, 0) 100%);
  z-index: 12;
  position: relative;
  pointer-events: auto; /* 消息区域可以捕获事件 */
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
  margin-bottom: 8px;
  position: relative;
  align-items: flex-start;
  transition: opacity 0.3s ease, transform 0.3s ease;
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
  width: 36px;
  height: 36px;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 5px;
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
  max-width: 75%;
  position: relative;
  z-index: 13; /* 确保消息内容可见并可交互 */
}

/* 发送者名称 */
.message-sender {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
  margin-bottom: 2px;
  padding-left: 10px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

/* 消息气泡 */
.message-bubble {
  padding: 6px 12px;
  border-radius: 16px;
  position: relative;
  word-break: break-word;
  line-height: 1.4;
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

/* 已清除消息的样式 */
.message-bubble.cleared {
  min-height: 20px;
  min-width: 20px;
  background: transparent;
  border: none;
  box-shadow: none;
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
  background-color: rgba(149, 236, 105, 0.8);
  color: #000;
}

.assistant .message-bubble {
  background-color: rgba(255, 255, 255, 0.8);
  color: #000;
}

/* 时间戳 */
.message-timestamp {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.7);
  margin-top: 2px;
  display: block;
  text-align: center;
  padding: 5px 0;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

/* 其他agent的消息样式 */
.message.other-agent .message-bubble {
  background-color: rgba(240, 240, 240, 0.8);
}

/* agent变更提示 */
.agent-change-notice {
  width: fit-content;
  text-align: center;
  font-size: 12px;
  color: #fff;
  margin: 5px auto;
  padding: 3px 8px;
  background-color: rgba(80, 80, 80, 0.7);
  border-radius: 12px;
  position: relative;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

/* 针对短消息的特殊样式 */
.short-message .message-bubble {
  padding: 5px 10px;
}

/* 录音中的样式 */
.recognizing .message-bubble {
  background-color: rgba(149, 236, 105, 0.7);
}

/* 添加打字指示器样式 */
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

/* 确保所有消息元素可交互 */
.message, .message-bubble {
  pointer-events: auto;
}
</style> 