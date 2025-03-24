import { useState, useRef, useEffect } from 'react'
import '../assets/ChatPanel.css'

// 聊天面板组件，接收消息列表、发送消息回调和加载状态作为props
const ChatPanel = ({ messages = [], onSendMessage, loading }) => {
  // 文本输入状态
  const [text, setText] = useState('')
  // 录音状态
  const [isRecording, setIsRecording] = useState(false)
  // 录音提示文本
  const [recordingText, setRecordingText] = useState('')
  // 消息列表底部引用，用于自动滚动
  const messagesEndRef = useRef(null)
  // 聊天面板引用
  const chatPanelRef = useRef(null)
  // 媒体录制器引用
  const mediaRecorderRef = useRef(null)
  // 语音按钮按压状态
  const [voiceButtonPressed, setVoiceButtonPressed] = useState(false)

  // 当消息列表更新时，自动滚动到底部
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages])

  // 开始录音的处理函数
  const startRecording = async () => {
    try {
      // 请求麦克风权限并创建媒体流
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaRecorderRef.current = new MediaRecorder(stream)
      
      const audioChunks = []
      // 收集音频数据
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data)
        }
      }
      
      // 录音结束后的处理
      mediaRecorderRef.current.onstop = async () => {
        // 关闭麦克风
        stream.getTracks().forEach(track => track.stop())
        
        // 创建音频blob
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' })
        
        // 创建FormData对象
        const formData = new FormData()
        formData.append('audio', audioBlob)
        
        try {
          // 发送到后端进行语音识别
          const response = await fetch('http://localhost:8000/speech-to-text', {
            method: 'POST',
            body: formData
          })
          
          const result = await response.json()
          if (result.success && result.text) {
            onSendMessage(result.text)
          }
        } catch (error) {
          console.error('语音识别请求失败:', error)
        }
        
        setRecordingText('')
      }
      
      // 开始录音
      mediaRecorderRef.current.start()
      setIsRecording(true)
      setRecordingText('正在录音...')
    } catch (error) {
      console.error('无法访问麦克风', error)
    }
  }

  // 结束录音的处理函数
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      setIsRecording(false)
    }
  }

  // 处理语音按钮按下事件
  const handleVoiceButtonDown = () => {
    startRecording()
  }

  // 处理语音按钮释放事件
  const handleVoiceButtonUp = () => {
    stopRecording()
  }

  // 处理文本消息发送
  const handleSendText = () => {
    if (text.trim()) {
      onSendMessage(text.trim())
      setText('')
    }
  }

  // 处理回车键发送消息
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendText()
    }
  }

  return (
    <div className="chat-panel" ref={chatPanelRef}>
      {/* 聊天面板头部 */}
      <div className="chat-header">
        <h3>与AI助手对话</h3>
      </div>
      
      {/* 消息列表区域 */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          // 空消息提示
          <div className="empty-chat">
            <p>没有对话记录，开始聊天吧！</p>
          </div>
        ) : (
          // 渲染消息列表
          messages.map((message, index) => {
            const isShortMessage = message.content.length <= 10
            return (
              // 消息容器，包含类型和长度标识
              <div key={index} className={`message ${message.type} ${isShortMessage ? 'short-message' : ''}`}>
                {/* AI助手头像 */}
                {message.type === 'assistant' && (
                  <div className="avatar">
                    <img src="/avatars/agent.png" alt="Agent" />
                  </div>
                )}
                {/* 消息气泡 */}
                <div className="message-bubble">
                  {message.content}
                </div>
                {/* 用户头像 */}
                {message.type === 'user' && (
                  <div className="avatar">
                    <img src="/avatars/user.png" alt="User" />
                  </div>
                )}
              </div>
            )
          })
        )}
        
        {/* 加载状态显示 */}
        {loading && (
          <div className="message assistant">
            <div className="avatar">
              <img src="/avatars/agent.png" alt="Agent" />
            </div>
            <div className="message-bubble">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        {/* 录音状态显示 */}
        {isRecording && recordingText && (
          <div className="message user recognizing">
            <div className="message-bubble">
              {recordingText}
            </div>
            <div className="avatar">
              <img src="/avatars/user.png" alt="User" />
            </div>
          </div>
        )}
        
        {/* 用于自动滚动的空div */}
        <div ref={messagesEndRef} />
      </div>
      
      {/* 输入区域 */}
      <div className="chat-input-area">
        <div className={`input-container ${isRecording ? 'recording' : ''}`}>
          {isRecording ? (
            // 录音波形动画
            <div className="voice-wave">
              <div className="wave"></div>
              <div className="wave"></div>
              <div className="wave"></div>
              <div className="wave"></div>
              <div className="wave"></div>
            </div>
          ) : (
            // 文本输入框
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息..."
              rows={1}
              style={{ minHeight: '24px', maxHeight: '80px' }}
            />
          )}
          
          {/* 发送按钮 */}
          <button 
            className="send-button"
            onClick={handleSendText}
            disabled={!text.trim() || isRecording}
          >
            <svg viewBox="0 0 24 24" height="24" width="24">
              <path fill="currentColor" d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path>
            </svg>
          </button>
          
          {/* 语音按钮 */}
          <button 
            className={`voice-button ${isRecording ? 'pressed' : ''}`}
            onMouseDown={handleVoiceButtonDown}
            onMouseUp={handleVoiceButtonUp}
            onMouseLeave={handleVoiceButtonUp}
            onTouchStart={handleVoiceButtonDown}
            onTouchEnd={handleVoiceButtonUp}
          >
            <img src="/images/voice.png" alt="Voice" />
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatPanel 