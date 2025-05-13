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
      
      <!-- 录音状态显示 - 只有在录音且有文本且不是加载状态时显示 -->
      <div v-if="isRecording && recordingText && !chatStore.loading">
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
    
    <!-- 语音录制组件 -->
    <SensevoiceRecorder 
      ref="sensevoiceRecorderRef"
      :voiceInputMode="voiceInputMode"
      :voiceTimeout="voiceInputTimeout"
      :isLoading="chatStore.loading"
      @transcript-result="handleTranscriptResult"
      @recording-state-change="handleRecordingStateChange"
      @send-transcript="handleSendTranscript"
    />
    
    <!-- 输入区域 -->
    <div class="chat-input-area">
      <div :class="['input-container', { recording: isRecording, 'voice-mode': voiceInputMode }]">
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
          <!-- 文本输入框 - 仅在文本模式显示 -->
          <textarea 
            v-if="!voiceInputMode"
            v-model="text" 
            @keydown="handleKeyDown" 
            placeholder="输入消息或按住语音按钮说话..." 
            rows="1"
          ></textarea>
          
          <!-- 语音模式提示 - 仅在语音模式显示 -->
          <div v-else class="voice-mode-hint">
            <span>按住麦克风按钮开始说话... <small class="opacity-75">({{ voiceInputTimeout }}秒停顿后自动发送)</small></span>
          </div>
          
          <!-- 发送按钮 -->
          <button 
            class="send-button" 
            @click="handleSendText" 
            :disabled="(!text.trim() && !voiceInputMode) || chatStore.loading"
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
        @click="handleVoiceButtonClick"
        :class="{ pressed: voiceButtonPressed || (voiceInputMode && isRecording), 'voice-mode': voiceInputMode }"
        :disabled="chatStore.loading"
        :title="voiceInputMode ? (isRecording ? '点击停止录音' : '点击开始录音') : '按住说话'"
      >
        <i class="uil" :class="isRecording ? 'uil-microphone-slash' : 'uil-microphone'"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { useChatStore } from '../stores/chat'
import SensevoiceRecorder from './SensevoiceRecorder.vue'

const chatStore = useChatStore()

// 文本输入状态
const text = ref('')
// 录音状态
const isRecording = ref(false)
// 录音提示文本
const recordingText = ref('')
// 录音错误状态
const recordingError = ref(false)
// 消息列表底部引用，用于自动滚动
const messagesEndRef = ref(null)
// 聊天面板引用
const chatPanelRef = ref(null)
// 消息容器引用
const chatMessagesRef = ref(null)
// 语音按钮按压状态
const voiceButtonPressed = ref(false)
// 语音输入模式状态 - 从localStorage获取
const voiceInputMode = ref(localStorage.getItem('voiceInputMode') === 'false' ? false : true)
// 语音输入超时时间（秒）
const voiceInputTimeout = ref(parseInt(localStorage.getItem('voiceTimeout')) || 5)
// SensevoiceRecorder组件引用
const sensevoiceRecorderRef = ref(null)

// 添加上次发送的消息内容和时间戳，用于去重
let lastSentMessage = '';
let lastSentTime = 0;
let isMessageSending = false; // 防止重复发送

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

// 处理按键事件
function handleKeyDown(e) {
  // 只有在文本模式下才处理按键事件
  if (voiceInputMode.value) return;
  
  // 按下回车键且未按下Shift键时发送消息
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendText()
  }
}

// 发送文本消息
function handleSendText() {
  // 检查是否有文本内容，或者是否处于语音模式
  if (voiceInputMode.value) {
    // 在语音模式下，提示用户按住语音按钮
    if (!isRecording.value) {
      // 可以添加一个提示效果，如闪烁语音按钮
      flashVoiceButton();
    }
    return;
  }
  
  // 检查文本内容
  const trimmedText = text.value.trim()
  if (!trimmedText || chatStore.loading) return
  
  // 发送消息
  chatStore.sendMessage(trimmedText)
  
  // 清空输入框
  text.value = ''
}

// 闪烁语音按钮提示
function flashVoiceButton() {
  const voiceBtn = document.querySelector('.voice-button');
  if (!voiceBtn) return;
  
  // 添加闪烁动画类
  voiceBtn.classList.add('flash-animation');
  
  // 1秒后移除动画类
  setTimeout(() => {
    voiceBtn.classList.remove('flash-animation');
  }, 1000);
}

// 处理语音按钮点击事件
const handleVoiceButtonClick = () => {
  // 只在语音模式下处理点击事件
  if (voiceInputMode.value) {
    sensevoiceRecorderRef.value.toggleRecording()
  }
}

// 发送语音消息的封装函数，添加去重逻辑
function sendVoiceMessage(message, forcedGuidanceMode = null) {
  if (!message || !message.trim()) {
    console.log('消息为空，不发送');
    return;
  }
  
  if (isMessageSending) {
    console.log('消息正在发送中，忽略此次请求');
    return;
  }
  
  const now = Date.now();
  const messageText = message.trim();
  
  // 如果与上次发送的消息相同且时间间隔小于5秒，则忽略这次发送
  if (messageText === lastSentMessage && (now - lastSentTime) < 5000) {
    console.log('检测到重复消息，已忽略:', messageText);
    return;
  }
  
  // 标记发送状态
  isMessageSending = true;
  
  // 更新上次发送的消息和时间
  lastSentMessage = messageText;
  lastSentTime = now;
  
  // 检查是否是结束引导命令
  const endCommands = ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"];
  const isEndCommand = endCommands.some(cmd => messageText.includes(cmd));
  
  // 只有结束命令时才明确传递false，其他情况不传递引导模式状态，让后端维持当前状态
  const guidanceMode = isEndCommand ? false : null;
  
  console.log('发送语音消息:', messageText, 
              isEndCommand ? '明确结束引导模式' : '不干预引导模式，使用后端当前状态');
  
  // 实际发送消息，只有明确结束命令时才传递引导模式状态
  chatStore.sendStreamMessage(messageText, guidanceMode)
    .finally(() => {
      isMessageSending = false;
    });
}

// 处理语音按钮按下事件
const handleVoiceButtonDown = () => {
  voiceButtonPressed.value = true

  // 如果已经在录音，先停止
  if (isRecording.value) {
    sensevoiceRecorderRef.value.stopRecording()
    return
  }
  // 开始录音
  sensevoiceRecorderRef.value.startRecording()
}

// 处理语音按钮释放事件
const handleVoiceButtonUp = () => {
  voiceButtonPressed.value = false
  
  // 如果在语音输入模式下，不要停止录音
  if (voiceInputMode.value) {
    return
  }
  
  // 非语音输入模式下，释放按钮时停止录音
  if (isRecording.value) {
    sensevoiceRecorderRef.value.stopRecording()
  }
}

// 处理语音识别文本更新
const handleTranscriptResult = (text) => {
  recordingText.value = text
}

// 处理录音状态变化
const handleRecordingStateChange = (isRec) => {
  isRecording.value = isRec
}

// 处理发送语音文本
const handleSendTranscript = (text, options = {}) => {
  if (text && text.trim()) {
    console.log('处理语音发送文本:', text);
    
    // 检查是否是结束引导命令，只有明确的结束命令才会传递引导模式状态
    const endCommands = ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"];
    const isEndCommand = endCommands.some(cmd => text.includes(cmd));
    
    // 只有结束命令时才传递明确的false，否则不传递引导模式状态，让后端保持当前状态
    const guidanceMode = isEndCommand ? false : null;
    
    console.log('发送语音文本:', text, 
                isEndCommand ? '明确结束引导模式' : '不干预引导模式，使用后端当前状态');
    
    // 调用语音消息发送函数
    sendVoiceMessage(text, guidanceMode);
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

// 切换输入模式
function toggleInputMode() {
  voiceInputMode.value = !voiceInputMode.value
  // 保存用户偏好设置
  localStorage.setItem('voiceInputMode', voiceInputMode.value.toString())
  
  // 如果切换到语音模式，立即启动录音
  if (voiceInputMode.value && !isRecording.value) {
    console.log('切换到语音模式，立即启动录音');
    sensevoiceRecorderRef.value.startRecording();
  }
}

// 处理全局键盘快捷键
function handleGlobalKeyDown(e) {
  // Alt+V 切换输入模式已移动到设置中，这里可以保留或删除
}

// 监听设置变化
function handleSettingsChanged(newSettings) {
  if (newSettings.voiceInputMode !== undefined) {
    voiceInputMode.value = newSettings.voiceInputMode;
    localStorage.setItem('voiceInputMode', newSettings.voiceInputMode.toString());
  }
  
  if (newSettings.voiceTimeout !== undefined) {
    voiceInputTimeout.value = newSettings.voiceTimeout;
    localStorage.setItem('voiceTimeout', newSettings.voiceTimeout.toString());
  }
}

// 监听语音输入模式变化
watch(voiceInputMode, (newMode) => {
  if (newMode) {
    // 如果启用了语音输入模式，自动开始录音
    if (!isRecording.value && !chatStore.loading && sensevoiceRecorderRef.value) {
      console.log('切换到语音模式，自动开始录音');
      setTimeout(() => {
        sensevoiceRecorderRef.value.startRecording();
      }, 300); // 延迟300ms确保UI已更新
    }
  } else {
    // 如果禁用了语音输入模式，停止录音
    if (isRecording.value && sensevoiceRecorderRef.value) {
      console.log('切换到文本模式，停止录音');
      sensevoiceRecorderRef.value.stopRecording(false); // 停止录音但不发送当前内容
    }
  }
})

// 监听loading状态变化
watch(() => chatStore.loading, (isLoading) => {
  if (isLoading) {
    // 当开始加载时，如果有正在进行的录音，先停止录音
    if (isRecording.value && sensevoiceRecorderRef.value) {
      console.log('检测到加载开始，暂停录音');
      // 仅停止录音但不发送消息
      sensevoiceRecorderRef.value.stopRecording(false);
      isRecording.value = false;
      recordingText.value = '';
    }
  } else if (voiceInputMode.value && !isRecording.value && sensevoiceRecorderRef.value) {
    // 当加载结束并且在语音模式下，但没有录音时，自动启动录音
    console.log('对话加载完成，自动启动语音识别');
    setTimeout(() => {
      if (voiceInputMode.value && !isRecording.value && !chatStore.loading) {
        sensevoiceRecorderRef.value.startRecording();
      }
    }, 500);
  }
});

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
  
  // 监听设置变化事件
  window.addEventListener('settings-changed', (event) => {
    if (event.detail) {
      handleSettingsChanged(event.detail);
    }
  });
  
  // 确保初始状态正确
  isRecording.value = false;
  recordingText.value = '';
  
  // 如果启用了语音输入模式，SensevoiceRecorder组件会自行处理录音
  console.log('ChatPanel已挂载，当前语音模式:', voiceInputMode.value);
})

onUnmounted(() => {
  // 确保在组件卸载时停止录音
  if (isRecording.value && sensevoiceRecorderRef.value) {
    sensevoiceRecorderRef.value.stopRecording(false);
  }
  
  // 移除设置变化事件监听
  window.removeEventListener('settings-changed', handleSettingsChanged);
})
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
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
}

.voice-button:hover {
  background-color: #5788cc;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}

.voice-button.pressed {
  background-color: #953e3e;
  transform: scale(1.1);
  box-shadow: 0 2px 8px rgba(149, 62, 62, 0.5);
}

.voice-button:disabled {
  background-color: #444;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.voice-button.voice-mode {
  background-color: #953e3e;
  transform: scale(1.1);
  box-shadow: 0 3px 12px rgba(149, 62, 62, 0.4);
}

.voice-button.voice-mode:hover {
  background-color: #b54a4a;
  transform: scale(1.15) translateY(-2px);
  box-shadow: 0 5px 15px rgba(149, 62, 62, 0.5);
}

.flash-animation {
  animation: flash 1s;
}

@keyframes flash {
  0%, 50%, 100% {
    background-color: #953e3e;
    transform: scale(1.1);
    box-shadow: 0 3px 12px rgba(149, 62, 62, 0.5);
  }
  25%, 75% {
    background-color: #444;
    transform: scale(1.0);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }
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
.send-button, .voice-button, textarea, .message, .message-bubble {
  pointer-events: auto;
}

.mode-toggle-button {
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
}

.mode-toggle-button:hover {
  background-color: #5788cc;
}

.mode-toggle-button:disabled {
  background-color: #444;
  cursor: not-allowed;
}

.voice-mode-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px 16px;
  border-radius: 24px;
  background-color: rgba(60, 60, 60, 0.8);
  color: white;
  font-size: 14px;
  line-height: 1.4;
  box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.2);
}

.input-container.voice-mode {
  background-color: rgba(40, 40, 40, 0.9);
  border: 1px solid #953e3e;
  box-shadow: 0 0 0 1px rgba(149, 62, 62, 0.3);
  transition: all 0.3s ease;
}
</style> 