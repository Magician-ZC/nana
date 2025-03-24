import { useState, useRef, useEffect } from 'react'
import Live2DDisplay from './components/Live2DModel'
import './App.css'
import LoadingDots from './components/LoadingDots'
import AgentSelector from './components/AgentSelector'
import ChatPanel from './components/ChatPanel'

// 不同agent的欢迎语和性格特点
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

function App() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [currentModel, setCurrentModel] = useState('nanaA')
  const live2dRef = useRef(null)
  const [isTracking, setIsTracking] = useState(true)
  const hasShownWelcomeRef = useRef(false)

  // 调试输出当前状态
  useEffect(() => {
    console.log('当前状态:', { 
      messageCount: messages.length,
      currentModel, 
      isTracking
    })
  }, [messages, currentModel, isTracking])

  // 组件首次加载或agent改变时显示欢迎语
  useEffect(() => {
    // 如果有消息历史，就不显示欢迎语
    if (messages.length > 0) return;
    
    // 首次加载时显示欢迎语
    const agentInfo = AGENT_WELCOME_MESSAGES[currentModel] || AGENT_WELCOME_MESSAGES.nanaA;
    setMessages([
      { type: 'assistant', content: agentInfo.message }
    ]);
    
    // 如果是首次加载，设置合适的表情
    if (!hasShownWelcomeRef.current && live2dRef.current) {
      // 根据不同角色设置合适的表情
      const expression = currentModel === 'nanaA' ? '酷酷' : 
                        currentModel === 'nanaB' ? '开心' : '害羞';
      live2dRef.current.showExpression(expression);
      hasShownWelcomeRef.current = true;
    }
  }, [currentModel, messages.length]);

  useEffect(() => {
    const handleKeyPress = (e) => {
      if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        e.preventDefault() // 防止空格键触发其他操作
        setIsTracking(!isTracking)
        if (live2dRef.current) {
          live2dRef.current.setTracking(!isTracking)
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [isTracking])

  const handleAgentChange = (agentId) => {
    // 切换agent时，清空消息历史并重置状态
    setMessages([]);
    setCurrentModel(agentId);
    hasShownWelcomeRef.current = false;
    
    if (live2dRef.current) {
      live2dRef.current.changeModel(agentId)
    }
  }

  const handleSendMessage = async (message) => {
    if (!message.trim()) return
    
    console.log('发送消息:', message)
    
    // 添加用户消息到聊天记录
    setMessages(prevMessages => [
      ...prevMessages,
      { type: 'user', content: message }
    ])
    
    setLoading(true)
    try {
      // 获取当前角色的性格特点，用于指导AI回复风格
      const agentPersonality = AGENT_WELCOME_MESSAGES[currentModel]?.personality || '';
      
      const response = await fetch('http://localhost:8666/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: message,
          session_id: 'default',
          agent_type: currentModel,
          personality: agentPersonality
        }),
      })
      
      const data = await response.json()
      console.log('收到回复:', data)
      
      // 设置表情
      if (data.expression && live2dRef.current) {
        live2dRef.current.showExpression(data.expression)
      }
      
      // 检查音频数据是否存在且有效
      if (data.audio && data.audio.length > 0) {
        try {
          const audioBlob = new Blob(
            [Uint8Array.from(atob(data.audio), c => c.charCodeAt(0))],
            { type: 'audio/mpeg' }
          )
          const audioUrl = URL.createObjectURL(audioBlob)
          
          const audio = new Audio(audioUrl)
          audio.onerror = (e) => {
            console.error('Audio playback error:', e)
          }
          
          await audio.play()
          
          // 播放完成后释放 URL
          audio.onended = () => {
            URL.revokeObjectURL(audioUrl)
            // 音频播放结束后延迟1秒恢复默认表情
            setTimeout(() => {
              if (live2dRef.current) {
                // 恢复默认表情，不传入具体表情名称，会重置所有表情
                live2dRef.current.showExpression('default', false)
              }
            }, 1000)  // 1000ms = 1秒
          }
        } catch (audioError) {
          console.error('Audio processing error:', audioError)
        }
      }
      
      // 添加助手回复到聊天记录
      setMessages(prevMessages => [
        ...prevMessages,
        { type: 'assistant', content: data.message }
      ])
      
    } catch (error) {
      console.error('Error:', error)
      
      // 添加错误消息
      setMessages(prevMessages => [
        ...prevMessages,
        { type: 'assistant', content: "抱歉，我遇到了一些问题，请稍后再试。" }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="live2d-main">
        <Live2DDisplay ref={live2dRef} modelId={currentModel} />
        <AgentSelector onAgentChange={handleAgentChange} currentModel={currentModel} />
      </div>
      
      <ChatPanel 
        messages={messages}
        onSendMessage={handleSendMessage}
        loading={loading}
      />
    </div>
  )
}

export default App