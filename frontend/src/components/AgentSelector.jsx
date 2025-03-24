import { useState } from 'react'
import '../assets/AgentSelector.css'

const AgentSelector = ({ onAgentChange, currentModel }) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState(currentModel || 'nanaA')

  const agents = [
    { id: 'nanaA', name: '娜娜A', description: '傲娇猫娘' },
    { id: 'nanaB', name: '娜娜B', description: '知性大姐姐' },
    { id: 'nanaC', name: '娜娜C', description: '元气少女' }
  ]

  const handleAgentSelect = async (agentId) => {
    if (agentId === selectedAgent) {
      setIsOpen(false)
      return
    }

    try {
      const response = await fetch('http://192.168.3.238:8666/api/change_agent', {
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
        setSelectedAgent(agentId)
        if (onAgentChange) {
          onAgentChange(agentId)
        }
      } else {
        console.error('切换智能体失败:', data.message)
      }
    } catch (error) {
      console.error('切换智能体错误:', error)
    }
    
    setIsOpen(false)
  }

  return (
    <div className="agent-selector">
      <div 
        className="agent-selector-button" 
        onClick={() => setIsOpen(!isOpen)}
      >
        {agents.find(agent => agent.id === selectedAgent)?.name || '选择角色'}
      </div>
      
      {isOpen && (
        <div className="agent-dropdown">
          {agents.map(agent => (
            <div 
              key={agent.id}
              className={`agent-option ${selectedAgent === agent.id ? 'selected' : ''}`}
              onClick={() => handleAgentSelect(agent.id)}
            >
              <div className="agent-name">{agent.name}</div>
              <div className="agent-description">{agent.description}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AgentSelector 