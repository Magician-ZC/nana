<template>
  <div class="agent-selector">
    <div 
      class="agent-selector-button" 
      @click="isOpen = !isOpen"
    >
      {{ selectedAgentName }}
    </div>
    
    <div v-if="isOpen" class="agent-dropdown">
      <div 
        v-for="agent in agents" 
        :key="agent.id"
        :class="['agent-option', { selected: selectedAgent === agent.id }]"
        @click="handleAgentSelect(agent.id)"
      >
        <div class="agent-name">{{ agent.name }}</div>
        <div class="agent-description">{{ agent.description }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue'
import { useChatStore } from '../stores/chat'

const props = defineProps({
  currentModel: {
    type: String,
    default: 'nanaA'
  }
})

const emit = defineEmits(['agent-change'])
const chatStore = useChatStore()

const isOpen = ref(false)
const selectedAgent = ref(props.currentModel || 'nanaA')

const agents = [
  { id: 'nanaA', name: '娜娜A', description: '傲娇猫娘' },
  { id: 'nanaB', name: '娜娜B', description: '知性大姐姐' },
  { id: 'nanaC', name: '娜娜C', description: '元气少女' }
]

const selectedAgentName = computed(() => {
  const agent = agents.find(agent => agent.id === selectedAgent.value)
  return agent ? agent.name : '选择角色'
})

const handleAgentSelect = async (agentId) => {
  if (agentId === selectedAgent.value) {
    isOpen.value = false
    return
  }

  try {
    const response = await fetch('http://localhost:8666/api/change_agent', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        agent_name: agentId,
        session_id: 'default'
      }),
    })
    
    const data = await response.json()
    
    if (data.success) {
      selectedAgent.value = agentId
      // 通知父组件
      emit('agent-change', agentId)
      // 同时更新store
      chatStore.changeAgent(agentId)
    } else {
      console.error('切换智能体失败:', data.message)
    }
  } catch (error) {
    console.error('切换智能体错误:', error)
  }
  
  isOpen.value = false
}
</script>

<style scoped>
.agent-selector {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
}

.agent-selector-button {
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 15px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.agent-selector-button:hover {
  background-color: rgba(50, 50, 50, 0.8);
}

.agent-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 5px;
  background-color: rgba(30, 30, 30, 0.95);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 180px;
}

.agent-option {
  padding: 10px 15px;
  cursor: pointer;
  transition: all 0.3s;
}

.agent-option:hover {
  background-color: rgba(60, 60, 60, 0.7);
}

.agent-option.selected {
  background-color: rgba(80, 80, 80, 0.7);
}

.agent-name {
  font-weight: bold;
  color: white;
  font-size: 14px;
}

.agent-description {
  color: #ccc;
  font-size: 12px;
  margin-top: 2px;
}
</style> 