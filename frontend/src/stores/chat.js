import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// agent角色配置
const AGENT_WELCOME_MESSAGES = {
  nanaA: {
    message: '哼~又是无聊的一天呢，有什么事吗？别浪费我时间哦。',
    personality: '傲娇，有点酷，略带不耐烦但内心善良'
  },
  nanaB: {
    message: '你好啊！今天天气真不错，有什么我能帮到你的吗？我很乐意帮忙哦~',
    personality: '阳光开朗，热情活泼，乐于助人'
  },
  nanaC: {
    message: '主人好~人家今天也会努力为您服务的，有什么需要帮忙的呢？',
    personality: '温柔可爱，略带羞涩，说话方式偏萌系'
  }
}

// 格式化时间函数
function formatTime() {
  const now = new Date()
  return {
    time: now,
    hours: now.getHours().toString().padStart(2, '0'),
    minutes: now.getMinutes().toString().padStart(2, '0')
  }
}

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref([])
  const loading = ref(false)
  const currentModel = ref('nanaA')
  const currentAgent = ref('nanaA')
  const isTracking = ref(true)
  const hasShownWelcome = ref({})  // 改为对象，记录每个agent是否显示过欢迎消息
  
  // 获取当前角色信息
  const currentAgentInfo = computed(() => 
    AGENT_WELCOME_MESSAGES[currentModel.value] || AGENT_WELCOME_MESSAGES.nanaA
  )
  
  // 方法
  function setTrackingStatus(status) {
    isTracking.value = status
  }
  
  function changeAgent(agentId, modelId) {
    // 不再清空消息历史，只切换角色
    currentAgent.value = agentId
    
    // 如果提供了modelId，使用它。否则默认使用agentId
    const newModelId = modelId || agentId
    
    console.log(`Chat Store - changeAgent: agentId=${agentId}, modelId=${newModelId}`)
    currentModel.value = newModelId
    
    // 检查是否需要显示欢迎消息
    if (!hasShownWelcome.value[agentId]) {
      showWelcomeMessage()
    }
  }
  
  async function sendMessage(message) {
    if (!message.trim()) return
    
    console.log('发送消息:', message)
    
    // 添加带时间戳的用户消息到聊天记录
    messages.value.push({ 
      type: 'user', 
      content: message,
      timestamp: formatTime(),
      agentId: currentAgent.value 
    })
    
    loading.value = true
    try {
      // 获取当前角色的性格特点，用于指导AI回复风格
      const agentPersonality = AGENT_WELCOME_MESSAGES[currentModel.value]?.personality || ''
      
      // 检查是否是快捷提问类别
      const isQuickQuestion = [
        "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
        "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
      ].includes(message)
      
      const response = await fetch('http://localhost:8666/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: message,
          session_id: 'default',
          agent_type: currentAgent.value,  // 使用agent ID而不是model ID
          personality: agentPersonality,
          is_category: isQuickQuestion
        }),
      })
      
      const data = await response.json()
      console.log('收到回复:', data)
      
      // 添加带时间戳的助手回复到聊天记录
      messages.value.push({ 
        type: 'assistant', 
        content: data.message,
        timestamp: formatTime(),
        agentId: currentAgent.value 
      })
      
      // 如果有引导决策消息，添加为单独的一条助手消息
      if (data.guidance_message) {
        setTimeout(() => {
          messages.value.push({ 
            type: 'assistant', 
            content: data.guidance_message,
            timestamp: formatTime(),
            agentId: currentAgent.value 
          })
        }, 500); // 添加500ms延迟，使其看起来像是分开发送的
      }
      
      return data
    } catch (error) {
      console.error('Error:', error)
      
      // 添加错误消息
      messages.value.push({ 
        type: 'assistant', 
        content: "抱歉，我遇到了一些问题，请稍后再试。",
        timestamp: formatTime(),
        agentId: currentAgent.value 
      })
      
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 显示欢迎消息
  function showWelcomeMessage() {
    const agentId = currentAgent.value
    const agentInfo = AGENT_WELCOME_MESSAGES[currentModel.value]
    
    if (agentInfo && !hasShownWelcome.value[agentId]) {
      messages.value.push({ 
        type: 'assistant', 
        content: agentInfo.message,
        timestamp: formatTime(),
        agentId: agentId
      })
      hasShownWelcome.value[agentId] = true
    }
  }
  
  return {
    // 状态
    messages,
    loading,
    currentModel,
    currentAgent,
    isTracking,
    hasShownWelcome,
    currentAgentInfo,
    // 方法
    setTrackingStatus,
    changeAgent,
    sendMessage,
    showWelcomeMessage
  }
}) 