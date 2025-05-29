<template>
  <div class="agent-market-container">
    <div class="title-area">
      <div class="circle-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>
      <span>智能体广场</span>
      <!-- 只在选择了智能体时显示退出按钮 -->
      <div class="close-button-container">
        <button 
          v-if="currentAgentId"
          @click="resetCurrentAgent" 
          class="close-button"
          @mouseenter="showTooltip = true"
          @mouseleave="showTooltip = false"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6 6 18"></path>
            <path d="m6 6 12 12"></path>
          </svg>
        </button>
        <div class="tooltip" v-show="showTooltip && currentAgentId">退出当前智能体</div>
      </div>
    </div>
    
    <div class="agents-list" v-if="!loading">
      <button 
        v-for="agent in agents" 
        :key="agent.id" 
        class="agent-button"
        @click="handleAgentClick(agent)"
        :class="{ 'active': currentAgentId === agent.id }"
      >
        <div class="agent-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="12" cy="10" r="3"></circle>
            <path d="M7 21v-2a3 3 0 0 1 3-3h4a3 3 0 0 1 3 3v2"></path>
          </svg>
        </div>
        <span>{{ agent.name }}</span>
      </button>
    </div>
    <div class="loading-container" v-else>
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup>
import { useChatStore } from '../stores/chat'
import { ref, onMounted, onUnmounted } from 'vue'
import { getApiUrl } from '../utils/api'

// 定义emit
const emit = defineEmits(['close'])

const chatStore = useChatStore()

// 提示框显示状态
const showTooltip = ref(false)

// 外部智能体列表
const agents = ref([])
const loading = ref(true)
const currentAgentId = ref(null)

// 加载智能体列表
const loadAgents = async () => {
  try {
    loading.value = true
    const response = await fetch(getApiUrl('/api/external_agents'), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    const data = await response.json()
    if (data.success && Array.isArray(data.agents)) {
      agents.value = data.agents
      console.log('加载了', agents.value.length, '个外部智能体')
    } else {
      console.error('加载外部智能体失败:', data.message)
    }
  } catch (error) {
    console.error('加载外部智能体时出错:', error)
  } finally {
    loading.value = false
  }
}

// 处理智能体点击事件
const handleAgentClick = async (agent) => {
  try {
    loading.value = true
    console.log('切换到外部智能体:', agent.name)
    
    // 检查必要的字段是否存在
    if (!agent.id || !agent.name) {
      console.error('智能体数据不完整:', agent)
      chatStore.addSystemMessage(`切换智能体失败: 智能体数据不完整`)
      loading.value = false
      return
    }

    // 构建请求数据，包含所有可能需要的字段
    const agentData = {
      agent_id: agent.id,
      name: agent.name,
      description: agent.description || '',
      prompt: agent.pre_prompt || '', // 原始字段
      pre_prompt: agent.pre_prompt || '', // 添加pre_prompt作为备用
      session_id: chatStore.sessionId || 'default'
    }
    
    console.log('发送智能体数据:', agentData)
    
    // 发送请求切换外部智能体
    const response = await fetch(getApiUrl('/api/switch_external_agent'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(agentData)
    })
    
    const data = await response.json()
    if (data.success) {
      currentAgentId.value = agent.id
      // 更新chatStore中的currentAgent，确保发送消息时使用正确的智能体
      const customAgentId = `custom_external_${agent.id}`
      chatStore.changeAgent(customAgentId)
      console.log('更新全局智能体状态为:', customAgentId)
      
      // 发送系统消息告知用户已切换智能体
      chatStore.addSystemMessage(`已切换到智能体: ${agent.name}`)
      console.log('成功切换到智能体:', agent.name)
    } else {
      console.error('切换智能体失败:', data.message)
      // 显示更详细的错误信息
      chatStore.addSystemMessage(`切换智能体失败: ${data.message || '未知错误'}`)
    }
  } catch (error) {
    console.error('切换智能体时出错:', error)
    // 提供更具体的错误信息
    let errorMessage = '切换智能体时出错，请稍后再试'
    if (error.message) {
      errorMessage += ` (${error.message})`
    }
    chatStore.addSystemMessage(errorMessage)
  } finally {
    loading.value = false
  }
}

// 处理关闭按钮事件
const resetCurrentAgent = async () => {
  try {
    loading.value = true
    console.log('重置当前智能体')
    
    // 重置为默认智能体
    currentAgentId.value = null
    chatStore.changeAgent('nanaA')
    
    // 发送系统消息告知用户已重置为默认智能体
    chatStore.addSystemMessage('已重置为默认智能体')
    console.log('成功重置为默认智能体')
  } catch (error) {
    console.error('重置智能体时出错:', error)
    chatStore.addSystemMessage('重置智能体时出错，请稍后再试')
  } finally {
    loading.value = false
  }
}

// 关闭面板函数 - 当需要关闭整个智能体广场时使用
const closePanel = () => {
  console.log('关闭智能体广场面板')
  emit('close')
}

// 组件挂载时加载智能体列表
onMounted(() => {
  loadAgents()
  
  // 添加周期性刷新，每5分钟刷新一次
  const refreshInterval = setInterval(loadAgents, 5 * 60 * 1000)
  
  // 组件销毁时清除定时器
  onUnmounted(() => {
    clearInterval(refreshInterval)
  })
})
</script>

<style scoped>
.agent-market-container {
  position: fixed;
  left: 30px;
  top: 120px;
  width: 260px;
  background-color: rgba(30, 30, 30, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
  z-index: 10;
  color: white;
  transition: all 0.3s ease;
}

.title-area {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  position: relative;
}

.circle-icon {
  width: 28px;
  height: 28px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 10px;
}

.title-area span {
  font-size: 16px;
  font-weight: 600;
}

.close-button-container {
  margin-left: auto;
  position: relative;
}

.close-button {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.1);
  border: none;
  cursor: pointer;
  color: white;
  padding: 0;
  transition: all 0.2s;
}

.close-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
  transform: scale(1.05);
}

.tooltip {
  position: absolute;
  bottom: 30px;
  right: 0;
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 5px 10px;
  border-radius: 5px;
  font-size: 12px;
  white-space: nowrap;
}

.agents-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
  overflow-y: auto;
}

.agent-button {
  display: flex;
  align-items: center;
  background-color: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 10px;
  padding: 10px;
  color: white;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s;
}

.agent-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
}

.agent-button.active {
  background-color: rgba(100, 160, 255, 0.3);
  border: 1px solid rgba(100, 160, 255, 0.5);
}

.agent-icon {
  width: 24px;
  height: 24px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin-right: 10px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top: 3px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 10px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 定制滚动条 */
.agents-list::-webkit-scrollbar {
  width: 6px;
}

.agents-list::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.agents-list::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.agents-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}
</style> 