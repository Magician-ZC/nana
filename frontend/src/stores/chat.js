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

// 添加获取当前API基础URL的函数
export function getApiBaseUrl() {
  // 使用相对路径，让Vite代理处理
  return "/api";
}

// 生成唯一ID
function generateUniqueId() {
  return Date.now().toString(36) + Math.random().toString(36).substring(2, 9);
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
  
  // 是否使用流式回复
  const useStreamResponse = ref(true)
  
  // 获取当前角色信息
  const currentAgentInfo = computed(() => 
    AGENT_WELCOME_MESSAGES[currentModel.value] || AGENT_WELCOME_MESSAGES.nanaA
  )
  
  // 方法
  function setTrackingStatus(status) {
    isTracking.value = status
  }
  
  // 播放音频
  function playAudio(base64Audio, highPriority = false) {
    if (!base64Audio) {
      console.warn('未收到音频数据，无法播放');
      return;
    }
    
    console.log('准备播放音频，数据长度:', base64Audio.length);
    console.log('base64Audio前20个字符:', base64Audio.substring(0, 20));
    
    try {
      // 停止当前正在播放的音频
      if (audioPlayer) {
        console.log('停止当前正在播放的音频');
        audioPlayer.pause();
        if (audioPlayer.src) {
          URL.revokeObjectURL(audioPlayer.src);
        }
        audioPlayer = null;
      }
      
      // 将Base64解码为二进制数据
      try {
        const audioData = atob(base64Audio);
        console.log('Base64解码成功，解码后长度:', audioData.length);
        
        const arrayBuffer = new ArrayBuffer(audioData.length);
        const uint8Array = new Uint8Array(arrayBuffer);
        
        for (let i = 0; i < audioData.length; i++) {
          uint8Array[i] = audioData.charCodeAt(i);
        }
        
        // 创建Blob对象
        const blob = new Blob([uint8Array], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(blob);
        console.log('创建音频URL成功:', audioUrl);
        
        // 创建并播放音频
        audioPlayer = new Audio();
        
        // 添加调试事件
        audioPlayer.addEventListener('loadstart', () => console.log('音频开始加载'));
        audioPlayer.addEventListener('durationchange', () => console.log('音频持续时间变化, 时长:', audioPlayer.duration));
        audioPlayer.addEventListener('loadedmetadata', () => console.log('音频元数据加载完成'));
        audioPlayer.addEventListener('loadeddata', () => console.log('音频数据加载完成'));
        audioPlayer.addEventListener('progress', () => console.log('音频下载中...'));
        audioPlayer.addEventListener('canplay', () => console.log('音频可以开始播放'));
        audioPlayer.addEventListener('canplaythrough', () => console.log('音频可以流畅播放'));
        audioPlayer.addEventListener('playing', () => console.log('音频开始播放'));
        audioPlayer.addEventListener('play', () => console.log('音频播放事件触发'));
        
        // 添加错误处理
        audioPlayer.addEventListener('error', (e) => {
          console.error('音频播放器错误:', e);
          console.error('错误代码:', audioPlayer.error ? audioPlayer.error.code : '未知');
          console.error('错误消息:', audioPlayer.error ? audioPlayer.error.message : '未知');
        });
        
        // 添加事件监听器
        if (highPriority) {
          // 高优先级模式，尽快播放，不等待完全加载
          audioPlayer.src = audioUrl;
          const playPromise = audioPlayer.play();
          if (playPromise !== undefined) {
            playPromise
              .then(() => console.log('高优先级音频播放成功启动'))
              .catch(error => {
                console.error('高优先级音频播放失败:', error);
                // 如果直接播放失败，回退到普通模式
                audioPlayer.addEventListener('canplaythrough', () => {
                  audioPlayer.play().catch(e => console.error('回退模式播放也失败:', e));
                });
              });
          }
        } else {
          // 普通模式，等待加载完成再播放
          audioPlayer.addEventListener('canplaythrough', () => {
            console.log('音频已加载，准备播放');
            try {
              const playPromise = audioPlayer.play();
              if (playPromise !== undefined) {
                playPromise
                  .then(() => console.log('音频播放成功启动'))
                  .catch(error => console.error('音频播放失败:', error));
              }
            } catch (playError) {
              console.error('播放时发生错误:', playError);
            }
          });
          
          audioPlayer.src = audioUrl;
        }
        
        // 触发音频准备就绪事件，让移动端组件也能获取到音频数据
        document.dispatchEvent(new CustomEvent('audio-ready', { 
          detail: { audio: base64Audio } 
        }));
        
      } catch (decodeError) {
        console.error('Base64解码或创建音频对象失败:', decodeError);
      }
    } catch (e) {
      console.error('播放音频时发生错误:', e);
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
  
  // 发送流式消息
  async function sendStreamMessage(message) {
    if (!message.trim()) return
    
    // 阻止连续请求，如果还有请求在处理中，则中断
    if (loading.value) {
      console.log('上一个请求还在处理中，请稍候')
      return
    }
    
    try {
      loading.value = true
      
      // 添加带时间戳的用户消息到聊天记录
      const userTimestamp = formatTime()
      console.log('添加用户消息:', message)
      messages.value.push({
        type: 'user',
        content: message,
        timestamp: userTimestamp,
        agentId: currentAgent.value
      })
      
      // 添加一个空的助手消息，用于逐步填充
      const assistantMessageIndex = messages.value.length
      const assistantId = generateUniqueId()
      console.log('创建空的助手消息，ID:', assistantId)
      messages.value.push({
        id: assistantId, // 添加唯一ID方便更新
        type: 'assistant',
        content: '正在思考中...', // 更改初始内容为"正在思考中"而不是"加载中..."
        isStreaming: true,
        timestamp: formatTime(),
        agentId: currentAgent.value
      })
      
      // 记录完整响应，防止流中断时丢失内容
      let fullResponse = '' // 初始化为空字符串，不再使用"加载中..."
      let expression = "思考" // 默认表情设为思考
      let guidanceMessage = null
      let audioData = null
      let guidanceAudio = null  // 存储引导决策的音频数据
      
      // 用于存储分片的音频数据
      let audioChunks = []
      let totalAudioChunks = 0
      
      // 获取当前角色的性格特点，用于指导AI回复风格
      const agentPersonality = AGENT_WELCOME_MESSAGES[currentModel.value]?.personality || ''
      
      // 检查是否是快捷提问类别
      const isQuickQuestion = [
        "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
        "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
      ].includes(message)
      
      // 创建流式请求
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30秒超时
      
      const response = await fetch(`${getApiBaseUrl()}/stream_chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: message,
          session_id: 'default',
          agent_type: currentAgent.value,
          personality: agentPersonality,
          is_category: isQuickQuestion
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        throw new Error(`网络响应错误: ${response.status}`)
      }
      
      if (!response.body) {
        throw new Error('不支持流式响应')
      }
      
      // 创建reader读取流
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      
      // 循环读取流数据
      let retryCount = 0
      const MAX_RETRIES = 3
      let partialLine = ''; // 用于存储不完整的行数据
      
      // 定义新的解析处理函数，确保不清除消息内容
      const processStreamData = (data) => {
        if (data.type === 'metadata') {
          // 处理元数据（表情和可能的引导消息）
          expression = data.expression || ""
          
          // 应用到消息对象
          if (assistantMessageIndex < messages.value.length) {
            messages.value[assistantMessageIndex].expression = expression
            // 使用后端生成的消息ID（如果有）
            if (data.message_id) {
              messages.value[assistantMessageIndex].messageId = data.message_id
            }
          }
          
          if (data.guidance_message) {
            guidanceMessage = data.guidance_message
            // 如果有引导决策的音频数据，保存它
            if (data.guidance_audio) {
              guidanceAudio = data.guidance_audio
              console.log('收到引导决策音频数据，长度:', data.guidance_audio.length)
            }
          }
        } 
        else if (data.type === 'chunk') {
          // 处理文本块
          if (data.content) {
            // 检查当前内容是否是初始的"正在思考中"或带省略号版本
            const isFirstChunk = fullResponse === '' || 
                                 (assistantMessageIndex < messages.value.length && 
                                 (messages.value[assistantMessageIndex].content === '正在思考中' ||
                                  messages.value[assistantMessageIndex].content === '正在思考中...'));
            
            if (isFirstChunk) {
              // 收到首个实际内容时，完全替换"正在思考中"
              // 同时清除可能的省略号前缀
              fullResponse = data.content.replace(/^\.{1,3}/, '');
              console.log(`收到首个内容块，完全替换"正在思考中"为: "${fullResponse}"`);

              // 确保消息对象仍然存在且是我们创建的那个
              if (assistantMessageIndex < messages.value.length) {
                // 使用updateMessageContent函数更新内容，确保正确替换
                console.log(`更新消息ID ${assistantId} 的内容，完全替换而不是累加`);
                
                // 直接创建新消息对象并替换，确保完全清除旧内容
                const updatedMessage = { 
                  ...messages.value[assistantMessageIndex],
                  content: fullResponse,
                  isStreaming: messages.value[assistantMessageIndex].isStreaming
                };
                messages.value.splice(assistantMessageIndex, 1, updatedMessage);
                
                // 强制更新
                messages.value = [...messages.value];
                console.log(`处理流数据：完全替换消息为新内容: "${fullResponse}"`);
              }
            } else {
              // 否则累加内容，同样清除可能的省略号
              const cleanContent = data.content.replace(/^\.{1,3}/, '');
              fullResponse += cleanContent;
              console.log(`累加内容块(已清除省略号): "${cleanContent}"`);
              
              // 使用常规更新方式
              updateMessageContent(assistantId, fullResponse);
            }
          } else {
            console.warn('收到空的文本块');
          }
        }
        else if (data.type === 'clear_previous') {
          // 忽略清除指令，只打日志
          console.log('收到清除消息指令，但为了保持消息气泡可见，忽略此指令');
        }
        else if (data.type === 'reset_content') {
          // 忽略重置指令，只打日志
          console.log('收到重置内容指令，但为了保持消息气泡可见，忽略此指令');
        }
        else if (data.type === 'audio') {
          // 处理完整的音频数据
          audioData = data.audio
          console.log('收到完整音频数据，长度:', data.audio.length);
          // 立即播放音频
          if (audioData && audioData.length > 100) {
            playAudio(audioData, true) // 使用高优先级播放音频
          }
        }
        else if (data.type === 'audio_chunk') {
          // 处理音频分片数据
          const chunkIndex = data.chunk_index
          const totalChunks = data.total_chunks
          
          if (totalChunks > 0) {
            totalAudioChunks = totalChunks
            
            // 存储当前分片
            if (chunkIndex < totalChunks) {
              audioChunks[chunkIndex] = data.chunk_data
              console.log(`接收到第 ${data.chunk_index + 1}/${totalAudioChunks} 个音频分片`);
            }
            
            // 检查是否已接收所有分片
            if (audioChunks.filter(chunk => chunk !== undefined).length === totalChunks) {
              // 所有分片已接收，合并为完整音频
              audioData = audioChunks.join('')
              console.log(`接收到最后一个音频分片 ${data.chunk_index + 1}/${totalAudioChunks}`);
              
              // 播放音频
              if (audioData && audioData.length > 100) {
                playAudio(audioData, true) // 使用高优先级播放音频
              }
            }
          }
        }
      };
      
      while (true) {
        try {
          const { done, value } = await reader.read()
          if (done) break
          
          // 解码收到的数据
          const text = decoder.decode(value)
          
          // 处理可能被分割的行，把partialLine和当前文本合并
          const fullText = partialLine + text;
          
          // 使用更准确的正则表达式匹配完整JSON对象，避免在音频数据中间分割
          // 匹配类型为"type"的JSON对象，以换行符结束
          const jsonRegex = /\{\s*"type"\s*:\s*"[^"]+"\s*,[\s\S]*?\}\n/g;
          const jsonLines = fullText.match(jsonRegex) || [];
          
          // 如果匹配到了完整的JSON对象
          if (jsonLines.length > 0) {
            console.log(`找到 ${jsonLines.length} 个完整JSON对象`);
            
            // 找出最后一个完整JSON的结束位置
            const lastJsonEnd = fullText.lastIndexOf(jsonLines[jsonLines.length - 1]) + jsonLines[jsonLines.length - 1].length;
            // 保存剩余不完整的部分
            partialLine = fullText.substring(lastJsonEnd);
            
            // 重置重试计数器
            retryCount = 0;
            
            // 处理每个完整的JSON
            for (const jsonLine of jsonLines) {
              const line = jsonLine.trim();
              if (!line) continue;
              
              try {
                const data = JSON.parse(line);
                console.log(`处理类型为 ${data.type} 的JSON数据`);
                
                // 使用新的处理函数，确保不清除消息内容
                processStreamData(data);
              } catch (e) {
                console.error('解析流数据时出错:', e, line.substring(0, 100) + '...');
              }
            }
          } else {
            // 如果没有完整的JSON对象，检查是否包含部分对象
            if (fullText.includes('{"type"')) {
              console.log('找到部分JSON对象，等待后续数据...');
              partialLine = fullText;
            } else {
              // 如果没有任何JSON标记，可能是纯文本或其他数据，重置partialLine
              console.log('未找到JSON格式数据');
              partialLine = fullText;
            }
          }
        } catch (error) {
          console.warn(`流读取错误(尝试${retryCount + 1}/${MAX_RETRIES}):`, error)
          
          if (retryCount >= MAX_RETRIES) {
            throw new Error('流读取失败，已达到最大重试次数')
          }
          
          retryCount++
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
      }
      
      // 如果结束时仍有未处理的部分行，尝试解析它
      if (partialLine.trim()) {
        try {
          const data = JSON.parse(partialLine.trim());
          // 使用新的处理函数处理最后的数据
          processStreamData(data);
        } catch (e) {
          console.warn('无法解析最后的不完整行:', partialLine.substring(0, 100) + '...');
        }
      }
      
      // 确保我们设置了最终的内容，以防流过早结束
      if (assistantMessageIndex < messages.value.length) {
        if (messages.value[assistantMessageIndex].isStreaming) {
          messages.value[assistantMessageIndex].isStreaming = false
        }
        
        // 如果内容为空或仍然是"正在思考中"，替换为有意义的内容
        if (!messages.value[assistantMessageIndex].content || 
            messages.value[assistantMessageIndex].content === '正在思考中...' ||
            messages.value[assistantMessageIndex].content.trim() === '') {
          if (fullResponse && fullResponse !== '正在思考中...' && fullResponse.trim() !== '') {
            messages.value[assistantMessageIndex].content = fullResponse;
          } else {
            // 如果没有有效的回复，设置一个默认提示
            messages.value[assistantMessageIndex].content = "抱歉，我暂时无法回答，请稍后再试。";
          }
        }
        
        // 如果有表情但尚未设置，设置它
        if (expression && !messages.value[assistantMessageIndex].expression) {
          messages.value[assistantMessageIndex].expression = expression
        }
      }
      
      // 如果有引导决策消息，添加为单独的一条助手消息
      if (guidanceMessage) {
        setTimeout(() => {
          const guidanceId = generateUniqueId();
          messages.value.push({ 
            id: guidanceId,
            type: 'assistant', 
            content: guidanceMessage,
            timestamp: formatTime(),
            agentId: currentAgent.value,
            expression: expression
          })
          
          // 如果有引导决策的音频数据，播放它
          if (guidanceAudio) {
            setTimeout(() => {
              playAudio(guidanceAudio, true)
            }, 50) // 使用更短的延迟，确保消息已添加但尽快播放
          }
        }, 500); // 添加500ms延迟，使其看起来像是分开发送的
      }
      
      return true
    } catch (error) {
      console.error('流式消息处理出错:', error)
      
      // 清除流式状态
      if (assistantMessageIndex < messages.value.length) {
        // 确保消息对象仍然存在
        messages.value[assistantMessageIndex].isStreaming = false
        
        // 如果内容为空或仍然是"正在思考中"，设置一个错误消息
        if (!messages.value[assistantMessageIndex].content || 
            messages.value[assistantMessageIndex].content === '正在思考中...' ||
            messages.value[assistantMessageIndex].content.trim() === '') {
          messages.value[assistantMessageIndex].content = "抱歉，我遇到了一些问题，请稍后再试。";
          messages.value[assistantMessageIndex].expression = "生气";
        }
      }
      
      return false
    } finally {
      loading.value = false
    }
  }
  
  async function sendMessage(message) {
    // 如果启用了流式回复，则使用流式API
    if (useStreamResponse.value) {
      return sendStreamMessage(message)
    }
    
    // 原始非流式处理逻辑
    if (!message.trim()) return
    
    console.log('发送普通消息:', message)
    
    // 检查是否已经有正在流式传输的消息
    const hasActiveStreamingMessage = messages.value.some(msg => msg.isStreaming === true)
    
    if (hasActiveStreamingMessage) {
      console.warn('已有正在流式传输的消息，等待完成后再发送新消息')
      return false
    }
    
    // 如果已经在加载中，不允许发送新消息
    if (loading.value) {
      console.warn('已有消息正在处理中，请等待完成')
      return false
    }
    
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
      
      const response = await fetch(`${getApiBaseUrl()}/chat`, {
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
      console.log('收到普通回复:', data)
      
      // 生成唯一ID
      const responseId = generateUniqueId();
      
      // 添加带时间戳和ID的助手回复到聊天记录
      messages.value.push({ 
        id: responseId,
        type: 'assistant', 
        content: data.message || '(无回复内容)',
        timestamp: formatTime(),
        agentId: currentAgent.value 
      })
      
      console.log(`添加普通回复消息: "${data.message}", ID: ${responseId}`);
      
      // 确保响应式更新
      messages.value = [...messages.value];
      
      // 如果收到音频数据，播放它
      if (data.audio) {
        playAudio(data.audio, true) // 使用高优先级播放音频
      }
      
      // 如果有引导决策消息，添加为单独的一条助手消息
      if (data.guidance_message) {
        setTimeout(() => {
          const guidanceId = generateUniqueId();
          messages.value.push({ 
            id: guidanceId,
            type: 'assistant', 
            content: data.guidance_message || '(无引导内容)',
            timestamp: formatTime(),
            agentId: currentAgent.value 
          })
          
          console.log(`添加引导消息: "${data.guidance_message}", ID: ${guidanceId}`);
          
          // 确保响应式更新
          messages.value = [...messages.value];
          
          // 如果收到引导决策的音频数据，等消息添加后播放(使用高优先级)
          if (data.guidance_audio) {
            setTimeout(() => {
              playAudio(data.guidance_audio, true)
            }, 50) // 使用更短的延迟，确保消息已添加但尽快播放
          }
        }, 500); // 添加500ms延迟，使其看起来像是分开发送的
      }
      
      return data
    } catch (error) {
      console.error('Error:', error)
      
      // 添加错误消息
      const errorId = generateUniqueId();
      messages.value.push({ 
        id: errorId,
        type: 'assistant', 
        content: "抱歉，我遇到了一些问题，请稍后再试。",
        timestamp: formatTime(),
        agentId: currentAgent.value 
      })
      
      // 确保响应式更新
      messages.value = [...messages.value];
      
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
      // 检查是否已经有相同agent的欢迎消息，避免重复添加
      const hasExistingWelcome = messages.value.some(
        msg => msg.isWelcomeMessage && msg.agentId === agentId
      );
      
      if (hasExistingWelcome) {
        console.log(`已存在 ${agentId} 的欢迎消息，不重复添加`);
        return;
      }
      
      // 生成唯一ID，用welcome前缀以便于识别
      const welcomeId = `welcome-${agentId}-${Date.now()}`;
      
      messages.value.push({ 
        id: welcomeId,
        type: 'assistant', 
        content: agentInfo.message,
        timestamp: formatTime(),
        agentId: agentId,
        isWelcomeMessage: true // 添加特殊标记，表示这是欢迎消息
      })
      // 记录已经显示过欢迎消息，此行可保留用于兼容性
      hasShownWelcome.value[agentId] = true
      
      // 为欢迎语请求TTS音频
      fetch(`${getApiBaseUrl()}/welcome_tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: agentInfo.message,
          agent_type: agentId
        }),
      })
      .then(response => response.json())
      .then(data => {
        if (data.audio) {
          playAudio(data.audio)
        }
      })
      .catch(error => {
        console.error('获取欢迎语音频失败:', error)
      })
    }
  }
  
  // 更新消息内容
  function updateMessageContent(messageId, content) {
    console.log(`尝试更新消息ID ${messageId} 的内容，长度: ${content?.length || 0}`);
    
    // 先按ID查找消息
    const messageIndex = messages.value.findIndex(msg => msg.id === messageId);
    
    if (messageIndex !== -1) {
      console.log(`找到ID为 ${messageId} 的消息，位于索引 ${messageIndex}`);
      
      // 确保内容不是空字符串
      if (!content || content.trim() === '') {
        content = '正在思考中...';
        console.log(`消息 ${messageId} 内容为空，设置为默认值`);
      }
      
      // 检查内容是否与当前内容相同
      if (messages.value[messageIndex].content === content) {
        console.log(`内容未变化，跳过更新`);
        return;
      }
      
      // 特殊处理"正在思考中"的情况
      if (messages.value[messageIndex].content === '正在思考中' || 
          messages.value[messageIndex].content === '正在思考中...') {
        console.log(`清除"正在思考中"或"正在思考中..."，完全替换为实际内容:"${content.substring(0, 30)}"`);
        
        // 先创建一个新的消息对象
        const updatedMessage = { ...messages.value[messageIndex] };
        // 更新内容
        updatedMessage.content = content;
        // 替换原有消息
        messages.value.splice(messageIndex, 1, updatedMessage);
      } else {
        // 非"正在思考中"的情况下，直接更新内容
        messages.value[messageIndex].content = content;
      }
      
      console.log(`已更新消息内容，新内容长度: ${content.length}`);
      
      // 强制触发响应式更新
      messages.value = [...messages.value];
    } else {
      // 找不到ID匹配的消息，进行额外诊断和尝试查找最近的助手消息
      console.warn(`找不到ID为 ${messageId} 的消息，尝试其他查找方式`);
      console.log(`当前消息列表长度: ${messages.value.length}`);
      
      // 打印所有消息的ID以便诊断
      messages.value.forEach((msg, idx) => {
        console.log(`消息 ${idx}: ID=${msg.id}, 类型=${msg.type}, 内容长度=${msg.content?.length || 0}`);
      });
      
      // 尝试查找最近的助手消息
      const recentAssistantMessages = messages.value.filter(msg => msg.type === 'assistant');
      
      if (recentAssistantMessages.length > 0) {
        const latestAssistantMsg = recentAssistantMessages[recentAssistantMessages.length - 1];
        console.log(`尝试更新最新的助手消息，ID=${latestAssistantMsg.id}`);
        
        // 特殊处理"正在思考中"的情况
        if (latestAssistantMsg.content === '正在思考中' || 
            latestAssistantMsg.content === '正在思考中...') {
          // 创建一个新的消息对象
          const updatedMessage = { ...latestAssistantMsg };
          // 完全替换内容
          updatedMessage.content = content;
          
          // 获取索引并替换
          const msgIndex = messages.value.findIndex(msg => msg.id === latestAssistantMsg.id);
          if (msgIndex !== -1) {
            messages.value.splice(msgIndex, 1, updatedMessage);
          } else {
            // 如果找不到索引，直接更新
            latestAssistantMsg.content = content;
          }
        } else {
          // 直接更新内容
          latestAssistantMsg.content = content;
        }
        
        // 强制触发响应式更新
        messages.value = [...messages.value];
        console.log(`已更新最新的助手消息内容`);
      } else {
        console.error('没有找到任何助手消息可以更新');
      }
    }
  }
  
  // 处理服务器事件
  const handleServerEvent = (data) => {
    try {
      if (data.includes('data:')) {
        // 提取事件数据
        const eventData = data.replace('data:', '').trim();
        if (eventData === '[DONE]') {
          // 流结束
          console.log('流式响应结束');
          // 更新消息状态，标记为非流式
          if (assistantMessageIndex < messages.value.length) {
            messages.value[assistantMessageIndex].isStreaming = false;
            
            // 确保最终消息内容非空
            if (!fullResponse || fullResponse.trim() === '') {
              updateMessageContent(assistantId, '(助手未返回内容)');
              console.log('流结束但没有内容，设置为默认值');
            } else {
              // 确保内容更新，并清除"正在思考中"
              if (messages.value[assistantMessageIndex].content === '正在思考中...') {
                console.log('流结束，清除"正在思考中..."，更新为最终内容');
              }
              updateMessageContent(assistantId, fullResponse);
              console.log(`流结束，最终内容: "${fullResponse}"`);
            }
          }
          
          // 音频处理
          if (audioData) {
            playAudio(audioData);
          }
          
          // 处理引导决策消息，如果有的话
          if (guidanceMessage) {
            setTimeout(() => {
              // 创建新的消息对象用于引导决策
              const guidanceId = generateUniqueId();
              messages.value.push({
                id: guidanceId,
                type: 'assistant',
                content: guidanceMessage || '(无引导内容)',
                timestamp: formatTime(),
                agentId: currentAgent.value
              });
              console.log(`添加引导消息: "${guidanceMessage}"`);
              
              // 如果有引导音频，播放它
              if (guidanceAudio) {
                setTimeout(() => {
                  playAudio(guidanceAudio, true);
                }, 50);
              }
            }, 500);
          }
          
          return;
        }
        
        try {
          // 解析JSON响应
          const jsonData = JSON.parse(eventData);
          console.log(`收到数据类型: ${jsonData.type}`);
          
          // 处理不同类型的数据
          if (jsonData.type === 'content') {
            // 检查是否是第一个内容块，如果是则完全替换"正在思考中"
            const isFirstContent = fullResponse === '' || 
                                    (assistantMessageIndex < messages.value.length && 
                                     (messages.value[assistantMessageIndex].content === '正在思考中' ||
                                      messages.value[assistantMessageIndex].content === '正在思考中...'));
            
            if (isFirstContent) {
              // 收到第一个内容块，完全替换之前的内容
              // 确保没有省略号残留
              fullResponse = jsonData.content.replace(/^\.{1,3}/, '');
              console.log(`收到第一个内容块，完全替换"正在思考中"为: "${fullResponse}"`);
              
              // 直接创建新消息对象并替换，确保完全清除旧内容
              if (assistantMessageIndex < messages.value.length) {
                const updatedMessage = { 
                  ...messages.value[assistantMessageIndex],
                  // 显式设置所有可能需要更新的字段
                  content: fullResponse,
                  isStreaming: messages.value[assistantMessageIndex].isStreaming
                };
                
                // 完全替换对象
                messages.value.splice(assistantMessageIndex, 1, updatedMessage);
                
                // 强制更新
                messages.value = [...messages.value];
                console.log(`已完全替换消息对象，新内容: "${fullResponse}"`);
              }
            } else {
              // 否则累加内容
              fullResponse += jsonData.content;
              console.log(`累加内容: "${jsonData.content}"`);
              
              // 使用新的updateMessageContent函数更新内容
              updateMessageContent(assistantId, fullResponse);
            }
            
            console.log(`当前全部内容(${fullResponse.length}字符): "${fullResponse.substring(0, 50)}${fullResponse.length > 50 ? '...' : ''}"`);
          } else if (jsonData.type === 'chunk') {
            // 累加消息内容 (兼容旧版API)
            if (jsonData.content) {
              // 检查是否是第一个内容块，如果是则完全替换"正在思考中"
              const isFirstChunk = fullResponse === '' || 
                                   (assistantMessageIndex < messages.value.length && 
                                    (messages.value[assistantMessageIndex].content === '正在思考中' ||
                                     messages.value[assistantMessageIndex].content === '正在思考中...'));
              
              if (isFirstChunk) {
                // 收到第一个内容块，完全替换之前的内容并清除省略号
                fullResponse = jsonData.content.replace(/^\.{1,3}/, '');
                console.log(`收到第一个chunk块，完全替换"正在思考中"为: "${fullResponse}"`);
                
                // 直接创建新消息对象并替换，确保完全清除旧内容
                if (assistantMessageIndex < messages.value.length) {
                  const updatedMessage = { 
                    ...messages.value[assistantMessageIndex],
                    // 显式设置所有可能需要更新的字段
                    content: fullResponse,
                    isStreaming: messages.value[assistantMessageIndex].isStreaming
                  };
                  
                  // 完全替换对象
                  messages.value.splice(assistantMessageIndex, 1, updatedMessage);
                  
                  // 强制更新
                  messages.value = [...messages.value];
                  console.log(`已完全替换消息对象，新内容: "${fullResponse}"`);
                }
              } else {
                // 否则累加内容，检查是否包含省略号
                const cleanContent = jsonData.content.replace(/^\.{1,3}/, '');
                fullResponse += cleanContent;
                console.log(`累加chunk内容: "${cleanContent}"`);
                
                // 使用updateMessageContent函数更新内容
                updateMessageContent(assistantId, fullResponse);
              }
              
              console.log(`当前全部内容(${fullResponse.length}字符): "${fullResponse.substring(0, 50)}${fullResponse.length > 50 ? '...' : ''}"`);
            }
          } else if (jsonData.type === 'expression') {
            // 处理表情变化事件
            expression = jsonData.expression;
            // 更新消息表情
            if (assistantMessageIndex < messages.value.length) {
              messages.value[assistantMessageIndex].expression = expression;
            }
            // 触发表情变化事件
            document.dispatchEvent(new CustomEvent('expression-update', {
              detail: { expression: expression }
            }));
          } else if (jsonData.type === 'guidance') {
            // 存储引导决策消息，稍后显示
            guidanceMessage = jsonData.content;
            console.log(`收到引导消息: "${jsonData.content}"`);
          } else if (jsonData.type === 'audio') {
            // 存储音频数据
            audioData = jsonData.audio;
          } else if (jsonData.type === 'guidance_audio') {
            // 存储引导决策的音频数据
            guidanceAudio = jsonData.audio;
          } else if (jsonData.type === 'clear_previous') {
            // 处理清除指令
            console.log('收到清除消息指令，但为避免消息气泡消失，不执行清除操作');
            
            // 如果服务器发送了强制清除，我们仍然需要重置内部的fullResponse变量
            // 但不清除显示的消息内容
            if (jsonData.force_clear && assistantMessageIndex < messages.value.length) {
              console.log('重置内部fullResponse变量，但保留显示的消息内容');
              fullResponse = messages.value[assistantMessageIndex]?.content || '';
            }
          } else if (jsonData.type === 'reset_content') {
            // 不再重置消息内容，只记录
            console.log('收到重置内容指令，但为避免消息气泡消失，不执行重置操作');
            
            // 确保消息继续流式传输
            if (assistantMessageIndex < messages.value.length) {
              // 确保消息被标记为流式传输中
              messages.value[assistantMessageIndex].isStreaming = true;
            }
          }
        } catch (parseError) {
          console.error('解析数据失败:', parseError, eventData.substring(0, 100));
        }
      }
    } catch (eventError) {
      console.error('处理事件数据失败:', eventError);
    }
  };
  
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
    useStreamResponse,
    // 方法
    setTrackingStatus,
    changeAgent,
    sendMessage,
    sendStreamMessage,
    showWelcomeMessage,
    loadCustomAgents,
    playAudio,
    updateMessageContent
  }
}) 