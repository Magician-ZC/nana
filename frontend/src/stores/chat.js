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
  const agents = ref([
    { id: 'nanaA', name: '娜娜A', description: '傲娇猫娘' },
    { id: 'nanaB', name: '娜娜B', description: '知性大姐姐' },
    { id: 'nanaC', name: '娜娜C', description: '元气少女' }
  ])
  
  // 音频播放器
  let audioPlayer = null
  
  // 获取当前角色信息
  const currentAgentInfo = computed(() => 
    AGENT_WELCOME_MESSAGES[currentModel.value] || AGENT_WELCOME_MESSAGES.nanaA
  )
  
  // 方法
  function setTrackingStatus(status) {
    isTracking.value = status
  }
  
  // 播放音频
  function playAudio(base64Audio) {
    if (!base64Audio) return
    
    try {
      // 停止当前正在播放的音频
      if (audioPlayer) {
        audioPlayer.pause()
        audioPlayer = null
      }
      
      // 将Base64解码为二进制数据
      const audioData = atob(base64Audio)
      const arrayBuffer = new ArrayBuffer(audioData.length)
      const uint8Array = new Uint8Array(arrayBuffer)
      
      for (let i = 0; i < audioData.length; i++) {
        uint8Array[i] = audioData.charCodeAt(i)
      }
      
      // 创建Blob对象
      const blob = new Blob([uint8Array], { type: 'audio/mp3' })
      const audioUrl = URL.createObjectURL(blob)
      
      // 创建并播放音频
      audioPlayer = new Audio(audioUrl)
      audioPlayer.addEventListener('ended', () => {
        // 播放结束后释放资源
        URL.revokeObjectURL(audioUrl)
        audioPlayer = null
      })
      
      audioPlayer.addEventListener('error', (e) => {
        console.error('音频播放错误:', e)
        URL.revokeObjectURL(audioUrl)
        audioPlayer = null
      })
      
      // 开始播放
      audioPlayer.play()
      
    } catch (error) {
      console.error('处理音频数据出错:', error)
    }
  }
  
  // 加载自定义角色列表
  async function loadCustomAgents() {
    try {
      const response = await fetch('http://localhost:8666/api/list_custom_agents')
      const data = await response.json()
      
      if (data.success && data.agents) {
        // 过滤掉已存在的自定义角色
        const existingCustomIds = agents.value
          .filter(agent => agent.id.startsWith('custom_'))
          .map(agent => agent.id)
        
        // 添加新的自定义角色
        data.agents.forEach(agent => {
          if (!existingCustomIds.includes(agent.id)) {
            agents.value.push(agent)
          }
        })
      }
    } catch (error) {
      console.error('加载自定义角色列表失败:', error)
    }
  }
  
  function changeAgent(agentId, modelId) {
    // 如果切换到当前角色，不做任何操作
    if (currentAgent.value === agentId) {
      return
    }
    
    // 不再清空消息历史，只切换角色
    currentAgent.value = agentId
    
    // 如果提供了modelId，使用它。否则默认使用agentId
    const newModelId = modelId || agentId
    
    console.log(`Chat Store - changeAgent: agentId=${agentId}, modelId=${newModelId}`)
    currentModel.value = newModelId
    
    // 每次切换角色都显示欢迎消息，不再检查是否已经显示过
    showWelcomeMessage()
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
      
      // 如果收到音频数据，播放它
      if (data.audio) {
        playAudio(data.audio)
      }
      
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
    // 获取当前角色信息，如果没有预设则使用默认欢迎语
    let agentInfo = AGENT_WELCOME_MESSAGES[currentModel.value]
    
    // 如果是自定义角色且没有预设欢迎语
    if (!agentInfo && agentId.startsWith('custom_')) {
      // 从agents中查找自定义角色的名称
      const customAgent = agents.value.find(agent => agent.id === agentId)
      const customName = customAgent ? customAgent.name : '自定义角色'
      
      // 创建默认欢迎语
      agentInfo = {
        message: `您好，我是${customName}，很高兴为您服务。有什么我可以帮助您的吗？`,
        personality: '友好、乐于助人'
      }
    }
    
    if (agentInfo) {
      messages.value.push({ 
        type: 'assistant', 
        content: agentInfo.message,
        timestamp: formatTime(),
        agentId: agentId
      })
      // 记录已经显示过欢迎消息，此行可保留用于兼容性
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
    agents,
    // 方法
    setTrackingStatus,
    changeAgent,
    sendMessage,
    showWelcomeMessage,
    loadCustomAgents,
    playAudio
  }
}) 