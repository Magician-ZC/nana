<template>
  <div class="agent-selector">
    <div 
      class="agent-selector-button" 
      @click="isOpen = !isOpen"
    >
      {{ selectedAgentName }}
    </div>
    
    <div v-if="isOpen" class="agent-dropdown-container">
      <div class="agent-dropdown">
        <div 
          v-for="agent in agents" 
          :key="agent.id"
          :class="['agent-option', { selected: selectedAgent === agent.id }]"
          @click="handleAgentSelect(agent.id)"
        >
          <div class="agent-name">{{ agent.name }}</div>
          <div class="agent-description">{{ agent.description }}</div>
          <div v-if="agent.id.startsWith('custom_')" class="agent-actions">
            <div class="edit-btn" @click.stop="handleEditAgent(agent)">
              <span>✎</span>
            </div>
            <div class="delete-btn" @click.stop="handleDeleteAgent(agent.id)">
              <span>×</span>
            </div>
          </div>
        </div>
      </div>
      
      <div class="custom-agent-option" @click="showCustomForm = true">
        <div class="agent-name">自定义角色</div>
        <div class="agent-description">创建你自己的角色</div>
      </div>
    </div>

    <CustomAgentForm
      v-if="showCustomForm"
      :edit-agent="editingAgent"
      @close="handleCustomFormClose"
      @save="handleCustomAgentSave"
    />
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits, onMounted } from 'vue'
import { useChatStore } from '../stores/chat'
import CustomAgentForm from './CustomAgentForm.vue'

const props = defineProps({
  currentModel: {
    type: String,
    default: 'nanaA'
  }
})

const emit = defineEmits(['agent-change'])
const chatStore = useChatStore()

const isOpen = ref(false)
const showCustomForm = ref(false)
const selectedAgent = ref(props.currentModel || 'nanaA')
const editingAgent = ref(null)

const agents = ref([
  { id: 'nanaA', name: '娜娜A', description: '傲娇猫娘' },
  { id: 'nanaB', name: '娜娜B', description: '知性大姐姐' },
  { id: 'nanaC', name: '娜娜C', description: '元气少女' },
])

const selectedAgentName = computed(() => {
  const agent = agents.value.find(agent => agent.id === selectedAgent.value)
  return agent ? agent.name : '选择角色'
})

const handleAgentSelect = async (agentId) => {
  if (agentId === selectedAgent.value) {
    isOpen.value = false
    return
  }

  try {
    // 找到选中的agent完整信息
    const selectedAgentData = agents.value.find(agent => agent.id === agentId)
    if (!selectedAgentData) {
      console.error('找不到agent信息:', agentId)
      return
    }
    
    // 自定义agent需要使用它们的model字段
    const actualModelId = selectedAgentData.id.startsWith('custom_') 
      ? selectedAgentData.model // 使用自定义agent的model字段
      : agentId                 // 对于内置agent，直接使用id

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
      // 通知父组件，传递正确的模型ID
      emit('agent-change', actualModelId)
      // 同时更新store
      chatStore.changeAgent(agentId, actualModelId)
    } else {
      console.error('切换智能体失败:', data.message)
    }
  } catch (error) {
    console.error('切换智能体错误:', error)
  }
  
  isOpen.value = false
}

const handleEditAgent = (agent) => {
  // 确保agent包含所有必要字段
  const fullAgent = {
    id: agent.id,
    name: agent.name || '',
    description: agent.description || '',
    model: agent.model || 'nanaA',
    personality: agent.personality || '',
    interests: agent.interests || '',
    lifestyle: agent.lifestyle || '',
    values: agent.values || ''
  }
  
  // 设置当前编辑的agent
  editingAgent.value = fullAgent
  showCustomForm.value = true
}

const handleCustomFormClose = () => {
  showCustomForm.value = false
  editingAgent.value = null
}

const handleDeleteAgent = async (agentId) => {
  if (!confirm('确定要删除这个角色吗？')) {
    return
  }
  
  try {
    const response = await fetch(`http://localhost:8666/api/delete_custom_agent/${agentId}`, {
      method: 'DELETE'
    })
    
    const data = await response.json()
    
    if (data.success) {
      // 从列表中移除该角色
      agents.value = agents.value.filter(agent => agent.id !== agentId)
      
      // 如果当前选中的是被删除的角色，切换到默认角色
      if (selectedAgent.value === agentId) {
        await handleAgentSelect('nanaA')
      }
    } else {
      console.error('删除角色失败:', data.message)
    }
  } catch (error) {
    console.error('删除角色错误:', error)
  }
}

const handleCustomAgentSave = async (customAgent) => {
  try {
    let response
    let savedAgentId = null
    
    if (editingAgent.value) {
      // 更新现有角色
      response = await fetch(`http://localhost:8666/api/update_custom_agent/${editingAgent.value.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(customAgent),
      })
      savedAgentId = editingAgent.value.id
    } else {
      // 创建新角色
      response = await fetch('http://localhost:8666/api/create_custom_agent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(customAgent),
      })
    }
    
    const data = await response.json()
    
    if (data.success) {
      if (editingAgent.value) {
        // 更新现有角色
        const index = agents.value.findIndex(agent => agent.id === editingAgent.value.id)
        if (index !== -1) {
          agents.value[index] = {
            id: editingAgent.value.id,
            name: customAgent.name,
            description: customAgent.description,
            model: customAgent.model,
            personality: customAgent.personality,
            interests: customAgent.interests,
            lifestyle: customAgent.lifestyle,
            values: customAgent.values
          }
          
          // 如果当前选中的是被编辑的角色，立即应用新的model
          if (selectedAgent.value === editingAgent.value.id) {
            console.log('更新后立即应用新model:', customAgent.model)
            // 更新Live2D模型
            emit('agent-change', customAgent.model)
            // 更新store中的model ID
            chatStore.changeAgent(editingAgent.value.id, customAgent.model)
          }
        }
      } else {
        // 添加新角色
        savedAgentId = data.agent_id
        const newAgent = {
          id: data.agent_id,
          name: customAgent.name,
          description: customAgent.description,
          model: customAgent.model,
          personality: customAgent.personality,
          interests: customAgent.interests,
          lifestyle: customAgent.lifestyle,
          values: customAgent.values
        }
        agents.value.push(newAgent)
        
        // 选择新角色
        await handleAgentSelect(newAgent.id)
      }
    } else {
      console.error('保存角色失败:', data.message)
    }
  } catch (error) {
    console.error('保存角色错误:', error)
  }
  
  handleCustomFormClose()
}

// 组件挂载时加载自定义角色列表
onMounted(async () => {
  try {
    const response = await fetch('http://localhost:8666/api/list_custom_agents')
    const data = await response.json()
    
    if (data.success && data.agents) {
      // 添加自定义角色到列表
      data.agents.forEach(agent => {
        agents.value.push(agent)
      })
    }
  } catch (error) {
    console.error('加载自定义角色列表失败:', error)
  }
})
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

.agent-dropdown-container {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 5px;
  background-color: rgba(30, 30, 30, 0.95);
  border-radius: 10px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  width: 220px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.agent-dropdown {
  max-height: 230px; /* 大约可显示4个选项 */
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.3) transparent;
}

/* 滚动条样式 */
.agent-dropdown::-webkit-scrollbar {
  width: 6px;
}

.agent-dropdown::-webkit-scrollbar-track {
  background: transparent;
}

.agent-dropdown::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 6px;
}

.agent-dropdown::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255, 255, 255, 0.5);
}

.agent-option {
  padding: 10px 15px;
  padding-right: 65px; /* 为按钮留出空间 */
  cursor: pointer;
  transition: all 0.3s;
  position: relative;
  display: flex;
  flex-direction: column;
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

.agent-actions {
  position: absolute;
  top: 50%;
  right: 15px;
  transform: translateY(-50%);
  display: flex;
  gap: 8px;
  z-index: 2; /* 确保按钮始终在顶层 */
}

.edit-btn, .delete-btn {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.edit-btn {
  background-color: rgba(76, 175, 80, 0.3);
  color: white;
}

.edit-btn:hover {
  background-color: rgba(76, 175, 80, 0.8);
  transform: scale(1.1);
}

.delete-btn {
  background-color: rgba(255, 0, 0, 0.3);
  color: white;
}

.delete-btn:hover {
  background-color: rgba(255, 0, 0, 0.8);
  transform: scale(1.1);
}

.custom-agent-option {
  padding: 10px 15px;
  cursor: pointer;
  transition: all 0.3s;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.custom-agent-option:hover {
  background-color: rgba(60, 60, 60, 0.7);
}

/* 移除旧的自定义agent样式 */
.custom-agent {
  display: none;
}
</style> 