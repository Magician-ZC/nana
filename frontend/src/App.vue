<template>
  <div class="app" :class="{ 'dark': isDarkMode }">
    <!-- 深色模式切换按钮 -->
    <button 
      @click="toggleDarkMode" 
      class="theme-toggle-btn"
      :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
    >
      <i :class="isDarkMode ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"></i>
    </button>
    
    <TimeWeather />
    <QuickQuestions />
    <div class="live2d-main">
      <Live2DModel ref="live2dRef" :modelId="chatStore.currentModel" />
      <AgentSelector @agent-change="handleAgentChange" :currentModel="chatStore.currentAgent" />
    </div>
    
    <ChatPanel />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from './stores/chat'
import Live2DModel from './components/Live2DModel.vue'
import AgentSelector from './components/AgentSelector.vue'
import ChatPanel from './components/ChatPanel.vue'
import TimeWeather from './components/TimeWeather.vue'
import QuickQuestions from './components/QuickQuestions.vue'

const chatStore = useChatStore()
const live2dRef = ref(null)
const isDarkMode = ref(false)

// 切换深色/浅色模式
const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value
  // 保存用户偏好到本地存储
  localStorage.setItem('darkMode', isDarkMode.value)
  updateTheme()
}

// 更新主题
const updateTheme = () => {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// 检查系统偏好
const checkSystemPreference = () => {
  // 先检查用户之前的设置
  const savedPreference = localStorage.getItem('darkMode')
  
  if (savedPreference !== null) {
    // 如果有保存的设置，使用它
    isDarkMode.value = savedPreference === 'true'
  } else {
    // 否则使用系统偏好
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDarkMode.value = prefersDark
  }
  
  updateTheme()
}

// 当收到消息更新和表情设置
watch(() => chatStore.messages, async (newMessages, oldMessages) => {
  // 仅在有新增消息且是助手消息的情况下处理
  if (newMessages.length > oldMessages.length && 
      newMessages[newMessages.length - 1].type === 'assistant') {
    
    const lastMessage = newMessages[newMessages.length - 1].content
    
    // 根据消息内容设置不同表情
    if (lastMessage.includes('？') || lastMessage.includes('?')) {
      // 问句使用惊讶表情
      live2dRef.value?.showExpression('惊讶')
    } else if (lastMessage.includes('！') || lastMessage.includes('!')) {
      // 感叹句使用兴奋表情
      live2dRef.value?.showExpression('兴奋')
    } else if (lastMessage.length < 10) {
      // 短句使用傲娇表情
      live2dRef.value?.showExpression('傲娇')
    } else {
      // 默认表情
      const defaultExpressions = {
        'nanaA': '酷酷',
        'nanaB': '开心',
        'nanaC': '害羞',
      }
      live2dRef.value?.showExpression(defaultExpressions[chatStore.currentModel] || '酷酷')
    }
    
    // 1.5秒后恢复默认表情
    setTimeout(() => {
      live2dRef.value?.showExpression('default', false)
    }, 1500)
  }
}, { deep: true })

// 处理agent变更
const handleAgentChange = (modelId) => {
  console.log('App收到形象变更:', modelId)
  if (live2dRef.value) {
    live2dRef.value.changeModel(modelId)
  }
}

// 设置键盘快捷键（空格键）控制模型的跟踪功能
const handleKeyPress = (e) => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
    e.preventDefault() // 防止空格键触发其他操作
    const newTrackingStatus = !chatStore.isTracking
    chatStore.setTrackingStatus(newTrackingStatus)
    if (live2dRef.value) {
      live2dRef.value.setTracking(newTrackingStatus)
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyPress)
  // 加载自定义角色列表
  chatStore.loadCustomAgents()
  
  // 检查并应用主题设置
  checkSystemPreference()
  
  // 监听系统主题变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    // 只有当用户没有手动设置过主题时，才跟随系统变化
    if (localStorage.getItem('darkMode') === null) {
      isDarkMode.value = e.matches
      updateTheme()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})
</script>

<style>
:root {
  --primary-color: #2c7c7e;
  --secondary-color: #4a6fa5;
  --background-color: #1a1a1a;
  --text-color: #ffffff;
  --accent-color: #f06292;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--background-color);
  color: var(--text-color);
  overflow: hidden;
}

.app {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(90deg, #d4c1ec 0%, #a6c1f4 100%);
}

.live2d-main {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background-color: transparent;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(80, 80, 80, 0.5);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 100, 100, 0.7);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .chat-panel {
    width: 100% !important;
    height: 100vh !important;
    max-height: none !important;
    right: 0 !important;
    bottom: 0 !important;
    border-radius: 0 !important;
  }
}

/* 深色模式切换按钮 */
.theme-toggle-btn {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 100;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.theme-toggle-btn:hover {
  transform: scale(1.1);
  background-color: rgba(50, 50, 50, 0.8);
}

.dark .theme-toggle-btn {
  background-color: rgba(255, 255, 255, 0.2);
}

.dark .theme-toggle-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
}
</style> 