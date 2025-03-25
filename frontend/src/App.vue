<template>
  <div class="app">
    <TimeWeather />
    <QuickQuestions />
    <div class="live2d-main">
      <Live2DModel ref="live2dRef" :modelId="chatStore.currentModel" />
      <AgentSelector @agent-change="handleAgentChange" :currentModel="chatStore.currentModel" />
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
        'nanaC': '害羞'
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
const handleAgentChange = (agentId) => {
  if (live2dRef.value) {
    live2dRef.value.changeModel(agentId)
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
</style> 