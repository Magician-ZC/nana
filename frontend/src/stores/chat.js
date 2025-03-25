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

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref([])
  const loading = ref(false)
  const currentModel = ref('nanaA')
  const isTracking = ref(true)
  const hasShownWelcome = ref(false)
  
  // 获取当前角色信息
  const currentAgentInfo = computed(() => 
    AGENT_WELCOME_MESSAGES[currentModel.value] || AGENT_WELCOME_MESSAGES.nanaA
  )
  
  // 方法
  function setTrackingStatus(status) {
    isTracking.value = status
  }
  
  function changeAgent(agentId) {
    // 切换agent时，清空消息历史并重置状态
    messages.value = []
    currentModel.value = agentId
    hasShownWelcome.value = false
  }
  
  async function sendMessage(message) {
    if (!message.trim()) return
    
    console.log('发送消息:', message)
    
    // 添加用户消息到聊天记录
    messages.value.push({ type: 'user', content: message })
    
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
          agent_type: currentModel.value,
          personality: agentPersonality,
          is_category: isQuickQuestion
        }),
      })
      
      const data = await response.json()
      console.log('收到回复:', data)
      
      // 添加助手回复到聊天记录
      messages.value.push({ type: 'assistant', content: data.message })
      
      // 如果有引导决策消息，添加为单独的一条助手消息
      if (data.guidance_message) {
        setTimeout(() => {
          messages.value.push({ type: 'assistant', content: data.guidance_message })
        }, 500); // 添加500ms延迟，使其看起来像是分开发送的
      }
      
      return data
    } catch (error) {
      console.error('Error:', error)
      
      // 添加错误消息
      messages.value.push({ 
        type: 'assistant', 
        content: "抱歉，我遇到了一些问题，请稍后再试。" 
      })
      
      return null
    } finally {
      loading.value = false
    }
  }
  
  // 显示欢迎消息
  function showWelcomeMessage() {
    if (messages.value.length === 0 && !hasShownWelcome.value) {
      const agentInfo = AGENT_WELCOME_MESSAGES[currentModel.value]
      messages.value.push({ 
        type: 'assistant', 
        content: agentInfo.message 
      })
      hasShownWelcome.value = true
    }
  }
  
  return {
    // 状态
    messages,
    loading,
    currentModel,
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