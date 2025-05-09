import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { getApiUrl } from '../utils/api'
import { useUserStore } from './user'

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

// Add a parseJsonResponse helper function at the top of the file, before the store definition
function parseJsonResponse(text) {
  if (!text || typeof text !== 'string') return { success: false, data: text };
  
  const trimmed = text.trim();
  let jsonText = trimmed;
  
  // Handle double-braced format {{...}}
  if (trimmed.startsWith('{{') && trimmed.endsWith('}}')) {
    jsonText = trimmed.substring(2, trimmed.length - 2);
  }
  // Handle standard format {...}
  else if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) {
    return { success: false, data: text };
  }
  
  try {
    const parsed = JSON.parse(jsonText);
    return { 
      success: true, 
      data: parsed,
      reply: parsed.reply || null,
      expression: parsed.expression || null
    };
  } catch (e) {
    console.error('JSON parsing failed:', e);
    return { success: false, data: text };
  }
}

// 添加节流函数
const debounce = (fn, delay) => {
  let timer = null
  return function() {
    const context = this
    const args = arguments
    clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(context, args)
    }, delay)
  }
}

export const useChatStore = defineStore('chat', () => {
  // 获取用户存储
  const userStore = useUserStore()
  
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
  
  // 初始化聊天存储
  function initializeChat() {
    console.log('初始化聊天存储')
    // 不再重置欢迎语状态，保持一天只显示一次
    
    // 检查用户是否已登录
    if (userStore.isLoggedIn && userStore.userProfile) {
      console.log('用户已登录，尝试加载聊天记录')
      // 加载用户的聊天记录
      const loaded = loadMessages()
      
      // 如果没有历史记录或记录为空，显示欢迎消息
      if (!loaded || messages.value.length === 0) {
        console.log('没有历史记录，显示欢迎消息')
        showWelcomeMessage()
      } else {
        console.log('已加载历史记录，消息数:', messages.value.length)
        // 不再强制显示欢迎语，而是检查今天是否已经显示过
      }
    } else {
      console.log('用户未登录，显示欢迎消息')
      // 未登录时清空消息，显示欢迎消息
      messages.value = []
      showWelcomeMessage()
    }
  }
  
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
        
        // 添加错误处理
        audioPlayer.addEventListener('error', (e) => {
          console.error('音频播放器错误:', e);
        });
        
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
      const response = await fetch(getApiUrl('list_custom_agents'))
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
    
    // 检查该角色今天是否已经显示过欢迎语
    if (messages.value.length === 0) {
      // 当没有消息时才显示欢迎语
      showWelcomeMessage()
    }
  }
  
  // 添加一个新函数用于检查当前是否处于引导会话中
  function isInGuidanceMode() {
    // 检查最近的消息，判断是否处于引导式会话中
    if (messages.value.length === 0) return false
    
    // 获取最后的几条用户消息
    const recentUserMessages = messages.value
      .filter(msg => msg.type === 'user')
      .slice(-5)
    
    // 检查是否有快捷提问类别
    const guidanceCategories = [
      "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
      "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
    ]
    
    // 检查最近的消息中是否有引导式会话结束的标志
    const hasEndGuidanceCommand = recentUserMessages.some(msg => 
      ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"].includes(msg.content.trim())
    )
    
    // 如果有结束指令，则不再处于引导模式
    if (hasEndGuidanceCommand) {
      console.log("检测到用户已发送结束引导指令，不再处于引导模式")
      return false
    }
    
    // 检查是否有快捷提问类别的消息
    const hasGuidanceCategory = recentUserMessages.some(msg => 
      guidanceCategories.includes(msg.content)
    )
    
    // 检查最后5条助手消息是否有引导结束的迹象
    const recentAssistantMessages = messages.value
      .filter(msg => msg.type === 'assistant')
      .slice(-5)
    
    const endKeywords = [
      "已结束当前话题", "已经结束话题", "话题已结束", 
      "结束了本次", "结束了这个话题", "已经为您结束",
      "确定要结束", "确认结束", "要结束这个话题", 
      "确定不继续", "结束引导", "退出引导",
      "总结一下", "总结如下", "总结这次", 
      "建议如下", "还有其他想讨论", "还有什么想讨论",
      "有其他想讨论", "已结束本次", "希望我的回答", 
      "希望我的建议", "希望对您有所帮助", "结束了引导"
    ]
    
    const assistantIndicatesEnd = recentAssistantMessages.some(msg => 
      endKeywords.some(keyword => msg.content.includes(keyword))
    )
    
    if (assistantIndicatesEnd) {
      console.log("检测到助手回复中已结束引导对话，不再处于引导模式")
      return false
    }
    
    return hasGuidanceCategory && !hasEndGuidanceCommand && !assistantIndicatesEnd
  }

  // 发送流式消息
  async function sendStreamMessage(message) {
    if (!message.trim()) return
    
    console.log('发送流式消息:', message)
    
    // 检查是否已经有正在流式传输的消息
    const hasActiveStreamingMessage = messages.value.some(msg => msg.isStreaming === true)
    
    if (hasActiveStreamingMessage) {
      console.warn('已有正在流式传输的消息，等待完成后再发送新消息')
      return false
    }
    
    // 检查当前是否在引导模式下
    const currentlyInGuidanceMode = isInGuidanceMode()
    
    // 检查是否是直接结束引导的指令
    const directEndCommands = ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"]
    const isEndGuidanceCommand = directEndCommands.includes(message.toLowerCase().trim())
    
    if (isEndGuidanceCommand) {
      console.log("检测到用户结束引导指令，将在消息发送后结束引导")
      // 发送结束引导的事件
      setTimeout(() => {
        forceEndGuidance()
      }, 100)
    }
    
    // 添加带时间戳的用户消息到聊天记录
    messages.value.push({ 
      type: 'user', 
      content: message,
      timestamp: formatTime(),
      agentId: currentAgent.value 
    })
    
    // 创建一个空的助手回复消息占位
    const assistantMessageIndex = messages.value.length
    messages.value.push({ 
      type: 'assistant', 
      content: '',
      timestamp: formatTime(),
      agentId: currentAgent.value,
      isStreaming: true, // 标记为正在流式传输
      messageId: Date.now() // 添加唯一标识符
    })
    
    // 添加消息变化监视器，仅用于调试
    const messageChangeInterval = setInterval(() => {
      if (assistantMessageIndex < messages.value.length) {
        const msg = messages.value[assistantMessageIndex]
        console.log(`[调试] 消息内容 (${msg.isStreaming ? '流式中' : '完成'}):", ${msg.content.substring(0, 30)}${msg.content.length > 30 ? '...' : ''}`)
      }
    }, 1000)
    
    loading.value = true
    
    // 记录完整响应，防止流中断时丢失内容
    let fullResponse = ''
    let expression = ""
    let guidanceMessage = null
    let audioData = null
    
    // 用于存储分片的音频数据
    let audioChunks = []
    let totalAudioChunks = 0
    
    try {
      // 获取当前角色的性格特点，用于指导AI回复风格
      const agentPersonality = AGENT_WELCOME_MESSAGES[currentModel.value]?.personality || ''
      
      // 检查是否是快捷提问类别
      const isQuickQuestion = [
        "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
        "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
      ].includes(message)
      
      // 当前的引导模式状态：如果是快捷提问则开始新引导，如果是结束指令则强制结束，否则使用当前状态
      const guidanceMode = isQuickQuestion ? true : (isEndGuidanceCommand ? false : currentlyInGuidanceMode)
      
      console.log(`发送消息: ${message}, 是否是快捷提问: ${isQuickQuestion}, 当前引导模式: ${guidanceMode}`)
      
      // 创建流式请求
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30秒超时
      
      const response = await fetch(getApiUrl('stream_chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: message,
          session_id: 'default',
          agent_type: currentAgent.value,
          personality: agentPersonality,
          is_category: isQuickQuestion,
          in_guidance_mode: guidanceMode, // 添加当前是否在引导模式下的标记
          // 确保所有必要的字段都被传递
          model: currentModel.value,
          agent_id: currentAgent.value
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
      
      console.log('开始读取流数据...')
      
      while (true) {
        try {
          const { done, value } = await reader.read()
          if (done) {
            console.log('流数据读取完成')
            break
          }
          
          // 解码收到的数据
          const text = decoder.decode(value)
          console.log('收到原始流数据:', text.substring(0, 200)) // 只打印前200个字符以避免过长
          
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
                console.log(`处理类型为 ${data.type} 的JSON数据:`, JSON.stringify(data).substring(0, 100));
                
                if (data.type === 'start') {
                  // 开始接收消息，清空之前可能的累积内容以确保干净开始
                  console.log('开始接收流式消息');
                  fullResponse = '';
                  
                  // 重置消息内容
                  if (assistantMessageIndex < messages.value.length) {
                    messages.value[assistantMessageIndex].content = '';
                  }
                }
                else if (data.type === 'content') {
                  // Process text content
                  if (data.content !== undefined) {
                    console.log('Received content data:', data.content);
                    
                    // Update accumulated text
                    fullResponse += data.content;
                    
                    // Try to parse the entire response so far as JSON
                    let parsedContent = fullResponse;
                    
                    // Check if it might be JSON format (either standard or double-braced)
                    if ((fullResponse.trim().startsWith('{') && fullResponse.trim().endsWith('}')) ||
                        (fullResponse.trim().startsWith('{{') && fullResponse.trim().endsWith('}}'))) {
                      
                      try {
                        // Handle double-braced format
                        let jsonContent = fullResponse.trim();
                        if (jsonContent.startsWith('{{') && jsonContent.endsWith('}}')) {
                          jsonContent = jsonContent.substring(2, jsonContent.length - 2);
                        } else if (jsonContent.startsWith('{') && jsonContent.endsWith('}')) {
                          // Standard JSON, keep as is
                        }
                        
                        // Try to parse the JSON
                        const parsedJson = JSON.parse(jsonContent);
                        
                        // Extract the reply field if it exists
                        if (parsedJson.reply) {
                          parsedContent = parsedJson.reply;
                          console.log('Successfully extracted reply from JSON:', parsedContent.substring(0, 30));
                          
                          // Update expression if available
                          if (parsedJson.expression && assistantMessageIndex < messages.value.length) {
                            messages.value[assistantMessageIndex].expression = parsedJson.expression;
                          }
                        }
                      } catch (e) {
                        // If parsing fails, it's likely incomplete JSON - keep accumulating
                        console.log('JSON parsing failed, likely incomplete:', e.message);
                        // Continue using the raw text
                      }
                    }
                    
                    // Update message content with either parsed reply or raw text
                    if (assistantMessageIndex < messages.value.length) {
                      messages.value[assistantMessageIndex].content = parsedContent;
                    }
                  }
                }
                else if (data.type === 'end') {
                  // Text content streaming has finished
                  console.log('Stream text content completed');
                  
                  // Mark message as no longer streaming
                  if (assistantMessageIndex < messages.value.length) {
                    messages.value[assistantMessageIndex].isStreaming = false;
                    
                    // 最终处理完整消息，确保内容是纯文本
                    let finalContent = messages.value[assistantMessageIndex].content;
                    let finalExpression = messages.value[assistantMessageIndex].expression;
                    let isSummary = false;
                    
                    // 检查是否是JSON格式并提取纯文本
                    try {
                      // 首先检查是双花括号还是标准JSON
                      if (finalContent.trim().startsWith('{{') && finalContent.trim().endsWith('}}')) {
                        // 处理双花括号格式
                        const jsonContent = finalContent.trim().substring(2, finalContent.trim().length - 2);
                        const parsedData = JSON.parse(jsonContent);
                        
                        if (parsedData.reply) {
                          finalContent = parsedData.reply;
                          console.log('从最终消息的双花括号JSON提取reply:', finalContent.substring(0, 30));
                          
                          if (parsedData.expression) {
                            finalExpression = parsedData.expression;
                          }
                          
                          if (parsedData.is_summary === true) {
                            isSummary = true;
                          }
                        }
                      } 
                      else if (finalContent.trim().startsWith('{') && finalContent.trim().endsWith('}')) {
                        // 处理标准JSON格式
                        const parsedData = JSON.parse(finalContent);
                        
                        if (parsedData.reply) {
                          finalContent = parsedData.reply;
                          console.log('从最终消息的标准JSON提取reply:', finalContent.substring(0, 30));
                          
                          if (parsedData.expression) {
                            finalExpression = parsedData.expression;
                          }
                          
                          if (parsedData.is_summary === true) {
                            isSummary = true;
                          }
                        }
                      }
                    } catch (e) {
                      console.log('最终消息不是有效的JSON格式或解析失败:', e.message);
                      // 不是有效JSON，保持原始内容
                    }
                    
                    // 更新消息内容为纯文本
                    messages.value[assistantMessageIndex].content = finalContent;
                    
                    // 更新表情
                    if (finalExpression) {
                      messages.value[assistantMessageIndex].expression = finalExpression;
                    }
                    
                    // 处理引导式对话结束
                    if (isSummary) {
                      console.log('Detected guided conversation end (summary)');
                      
                      // 触发引导结束事件
                      setTimeout(() => {
                        const guidanceEndEvent = new CustomEvent('guidance-end', {
                          detail: { type: 'summary', category: currentAgent.value }
                        });
                        window.dispatchEvent(guidanceEndEvent);
                      }, 500);
                    }
                  }
                }
                else if (data.type === 'metadata') {
                  // 处理元数据（表情和可能的引导消息）
                  expression = data.expression || "";
                  
                  // 应用到消息对象
                  if (assistantMessageIndex < messages.value.length) {
                    messages.value[assistantMessageIndex].expression = expression;
                    // 使用后端生成的消息ID（如果有）
                    if (data.message_id) {
                      messages.value[assistantMessageIndex].messageId = data.message_id;
                    }
                  }
                  
                  if (data.guidance_message) {
                    guidanceMessage = data.guidance_message;
                    // 如果有引导决策的音频数据，保存它
                    if (data.guidance_audio) {
                      guidanceAudio = data.guidance_audio;
                      console.log('收到引导决策音频数据，长度:', data.guidance_audio.length);
                    }
                  }
                } 
                else if (data.type === 'chunk') {
                  // 兼容旧版API，处理文本块
                  if (data.content) {
                    console.log('收到chunk数据:', data.content);
                    fullResponse += data.content;
                    
                    // 确保消息对象仍然存在且是我们创建的那个
                    if (assistantMessageIndex < messages.value.length) {
                      messages.value[assistantMessageIndex].content = fullResponse;
                    }
                  }
                }
                else if (data.type === 'audio') {
                  // 处理完整的音频数据
                  if (data.audio_data) {
                    console.log('收到完整音频数据，长度:', data.audio_data.length);
                    audioData = data.audio_data;
                    // 立即播放音频
                    playAudio(data.audio_data);
                  } else if (data.audio) {
                    // 兼容旧版API
                    console.log('收到完整音频数据(旧版格式)，长度:', data.audio.length);
                    audioData = data.audio;
                    // 立即播放音频
                    playAudio(data.audio);
                  } else {
                    console.warn('收到音频消息但不包含音频数据');
                  }
                }
                else if (data.type === 'audio_start') {
                  // 开始接收分片音频数据
                  console.log(`开始接收分片音频数据，总共 ${data.total_chunks} 个分片`);
                  audioChunks = new Array(data.total_chunks);
                  totalAudioChunks = data.total_chunks;
                  
                  // 存储第一个分片
                  if (data.audio_chunk) {
                    audioChunks[data.chunk_index] = data.audio_chunk;
                    console.log(`接收到第 ${data.chunk_index + 1}/${totalAudioChunks} 个音频分片`);
                  }
                }
                else if (data.type === 'audio_chunk') {
                  // 处理中间音频分片
                  if (data.audio_chunk && audioChunks) {
                    audioChunks[data.chunk_index] = data.audio_chunk;
                    console.log(`接收到第 ${data.chunk_index + 1}/${totalAudioChunks} 个音频分片`);
                  }
                }
                else if (data.type === 'audio_end') {
                  // 处理最后一个音频分片并合并播放
                  if (data.audio_chunk && audioChunks) {
                    audioChunks[data.chunk_index] = data.audio_chunk;
                    console.log(`接收到最后一个音频分片 ${data.chunk_index + 1}/${totalAudioChunks}`);
                    
                    // 检查是否所有分片都已接收
                    const hasAllChunks = audioChunks.every(chunk => chunk !== undefined);
                    
                    if (hasAllChunks) {
                      // 合并所有分片
                      const completeAudio = audioChunks.join('');
                      console.log(`所有音频分片接收完成，合并后长度: ${completeAudio.length}`);
                      
                      // 存储完整音频数据
                      audioData = completeAudio;
                      
                      // 播放合并后的音频
                      playAudio(completeAudio);
                    } else {
                      console.warn('音频分片接收不完整，缺少部分分片');
                      // 统计已接收的分片
                      const receivedChunks = audioChunks.filter(chunk => chunk !== undefined).length;
                      console.log(`已接收 ${receivedChunks}/${totalAudioChunks} 个分片`);
                      
                      // 尝试使用已接收的分片播放
                      if (receivedChunks > 0) {
                        const partialAudio = audioChunks.filter(chunk => chunk !== undefined).join('');
                        console.log(`使用部分分片播放音频，长度: ${partialAudio.length}`);
                        audioData = partialAudio;
                        playAudio(partialAudio);
                      }
                    }
                  }
                }
                else if (data.type === 'f5_tts_notification') {
                  // 处理F5-TTS通知，说明语音已通过流式TTS播放
                  console.log('收到F5-TTS流式语音通知:', data.message);
                  // 这里无需再播放音频，F5-TTS已经在服务端播放了
                }
                else if (data.type === 'complete') {
                  // 处理完成标记
                  if (assistantMessageIndex < messages.value.length) {
                    messages.value[assistantMessageIndex].isStreaming = false
                  }
                  
                  // 检查是否还需要处理音频数据（兼容旧版本）
                  if (data.audio && !audioData) {
                    audioData = data.audio
                    // 立即播放音频
                    playAudio(data.audio)
                  }
                }
              } catch (e) {
                console.error('解析流数据时出错:', e, line.substring(0, 100) + '...');
                // 尝试进行修复 - 检查是否是完整的JSON对象被截断
                try {
                  // 尝试修复被截断的JSON，通过在末尾添加缺失的大括号
                  if (line.indexOf('{') === 0 && line.lastIndexOf('}') < line.length - 1) {
                    const fixedLine = line.substring(0, line.lastIndexOf('}') + 1);
                    console.log('尝试修复截断的JSON:', fixedLine.substring(0, 50) + '...');
                    const data = JSON.parse(fixedLine);
                    console.log('JSON修复成功，类型:', data.type);
                    
                    // 处理修复后的数据（与上面相同的逻辑）
                    if (data.type === 'metadata') {
                      // ... same code as above ...
                    } 
                    // ... handle other types the same way ...
                  }
                } catch (repairError) {
                  console.error('尝试修复JSON失败:', repairError);
                }
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
          // 处理最后一个可能的数据包
          if (data.type === 'complete') {
            if (assistantMessageIndex < messages.value.length) {
              messages.value[assistantMessageIndex].isStreaming = false;
            }
          }
        } catch (e) {
          console.warn('无法解析最后的不完整行:', partialLine.substring(0, 100) + '...');
        }
      }
      
      // 确保我们设置了最终的内容，以防流过早结束
      if (assistantMessageIndex < messages.value.length) {
        if (messages.value[assistantMessageIndex].isStreaming) {
          messages.value[assistantMessageIndex].isStreaming = false
        }
        
        // 如果内容为空但我们有完整响应，则使用它
        if (!messages.value[assistantMessageIndex].content && fullResponse) {
          messages.value[assistantMessageIndex].content = fullResponse
        }
        
        // 如果有表情但尚未设置，设置它
        if (expression && !messages.value[assistantMessageIndex].expression) {
          messages.value[assistantMessageIndex].expression = expression
        }
      }
      
      // 如果有引导决策消息，添加为单独的一条助手消息
      if (guidanceMessage) {
        setTimeout(() => {
          messages.value.push({ 
            type: 'assistant', 
            content: guidanceMessage,
            timestamp: formatTime(),
            agentId: currentAgent.value,
            expression: expression,
            messageId: Date.now() + 1 // 使用不同的ID
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
        
        // 如果内容为空但我们有部分响应，使用它
        if (!messages.value[assistantMessageIndex].content && fullResponse) {
          messages.value[assistantMessageIndex].content = parseJsonResponse(fullResponse) || "抱歉，我遇到了一些问题，请稍后再试。"
          messages.value[assistantMessageIndex].expression = expression || "生气"
        } else if (!messages.value[assistantMessageIndex].content) {
          // 完全没有收到任何内容
          messages.value[assistantMessageIndex].content = "抱歉，我遇到了一些问题，请稍后再试。"
          messages.value[assistantMessageIndex].expression = "生气"
        }
      }
      
      return false
    } finally {
      loading.value = false
      
      // 清除调试定时器
      if (typeof messageChangeInterval !== 'undefined') {
        clearInterval(messageChangeInterval);
        console.log('[调试] 监视器已清除');
      }
    }
  }
  
  async function sendMessage(message) {
    // 如果启用了流式回复，则使用流式API
    if (useStreamResponse.value) {
      return sendStreamMessage(message)
    }
    
    // 原始非流式处理逻辑
    if (!message.trim()) return
    
    console.log('发送消息:', message)
    
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
    
    // 检查当前是否在引导模式下
    const currentlyInGuidanceMode = isInGuidanceMode()
    
    // 检查是否是直接结束引导的指令
    const directEndCommands = ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"]
    const isEndGuidanceCommand = directEndCommands.includes(message.toLowerCase().trim())
    
    if (isEndGuidanceCommand) {
      console.log("检测到用户结束引导指令，将在消息发送后结束引导")
      // 发送结束引导的事件
      setTimeout(() => {
        forceEndGuidance()
      }, 100)
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
      
      // 当前的引导模式状态：如果是快捷提问则开始新引导，如果是结束指令则强制结束，否则使用当前状态
      const guidanceMode = isQuickQuestion ? true : (isEndGuidanceCommand ? false : currentlyInGuidanceMode)
      
      console.log(`发送普通消息: ${message}, 是否是快捷提问: ${isQuickQuestion}, 当前引导模式: ${guidanceMode}`)
      
      const response = await fetch(getApiUrl('chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          message: message,
          session_id: 'default',
          agent_type: currentAgent.value,  // 使用agent ID而不是model ID
          personality: agentPersonality,
          is_category: isQuickQuestion,
          in_guidance_mode: guidanceMode // 添加当前是否在引导模式下的标记
        }),
      })
      
      const data = await response.json()
      console.log('收到回复:', data)
      
      // Process possible JSON response
      if (typeof data.message === 'string') {
        const result = parseJsonResponse(data.message);
        
        // If we successfully parsed JSON with a reply field, update the message
        if (result.success && result.reply) {
          data.message = result.reply;
          console.log('Updated message from JSON:', result.reply);
          
          // Update expression if available
          if (result.expression) {
            data.expression = result.expression;
            console.log('Updated expression from JSON:', result.expression);
          }
        }
      }
      
      // 添加带时间戳的助手回复到聊天记录
      // 对于心理医生的引导式对话，使用打字机效果
      const isGuidanceMode = isQuickQuestion || messages.value.some(msg => 
        msg.type === 'user' && [
          "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
          "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
        ].includes(msg.content)
      )
      
      if (isGuidanceMode) {
        // 先添加一个空消息
        const messageIndex = messages.value.length
        messages.value.push({
          type: 'assistant',
          content: '',
          timestamp: formatTime(),
          agentId: currentAgent.value,
          isStreaming: true
        })
        
        // 逐字显示文本
        const content = data.message
        const charDelay = 30  // 每个字符的延迟时间(毫秒)
        
        for (let i = 0; i < content.length; i++) {
          await new Promise(resolve => setTimeout(resolve, charDelay))
          messages.value[messageIndex].content = content.substring(0, i + 1)
        }
        
        // 完成流式显示
        messages.value[messageIndex].isStreaming = false
      } else {
        // 常规响应模式，直接显示完整回复
        messages.value.push({ 
          type: 'assistant', 
          content: data.message,
          timestamp: formatTime(),
          agentId: currentAgent.value,
          // 如果是快捷提问类别，添加标记
          isQuickQuestion: isQuickQuestion 
        })
      }
      
      // 处理语音输出
      if (data.use_f5_tts) {
        // 如果使用了F5TTS，音频已在服务器端播放，前端不需要做任何处理
        console.log('使用F5TTS播放语音，无需前端处理');
      } else if (data.audio) {
        // 常规TTS，前端播放音频
        playAudio(data.audio)
      }
      
      // 如果有引导决策消息，添加为单独的一条助手消息
      if (data.guidance_message) {
        setTimeout(() => {
          if (isGuidanceMode) {
            // 对引导消息也使用打字机效果
            const guidanceIndex = messages.value.length
            messages.value.push({
              type: 'assistant',
              content: '',
              timestamp: formatTime(),
              agentId: currentAgent.value,
              isStreaming: true
            })
            
            // 逐字显示文本
            const content = data.guidance_message
            const charDelay = 30
            
            // 使用异步IIFE处理引导消息的打字机效果
            (async () => {
              for (let i = 0; i < content.length; i++) {
                await new Promise(resolve => setTimeout(resolve, charDelay))
                messages.value[guidanceIndex].content = content.substring(0, i + 1)
              }
              
              // 完成流式显示
              messages.value[guidanceIndex].isStreaming = false
              
              // 如果收到引导决策的音频数据，等消息显示完成后播放(使用高优先级)
              if (data.guidance_audio) {
                playAudio(data.guidance_audio, true)
              }
            })()
          } else {
            messages.value.push({ 
              type: 'assistant', 
              content: data.guidance_message,
              timestamp: formatTime(),
              agentId: currentAgent.value 
            })
            
            // 如果收到引导决策的音频数据，等消息添加后播放(使用高优先级)
            if (data.guidance_audio) {
              setTimeout(() => {
                playAudio(data.guidance_audio, true)
              }, 50) // 使用更短的延迟，确保消息已添加但尽快播放
            }
          }
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
      // 检查今天是否已经显示过欢迎语
      const today = new Date().toLocaleDateString()
      const welcomeLastShownKey = `welcome_shown_${agentId}`
      const welcomeLastShown = localStorage.getItem(welcomeLastShownKey)
      
      // 检查是否需要显示欢迎消息
      const shouldShowWelcome = !welcomeLastShown || welcomeLastShown !== today
      
      // 检查页面刷新后是否已经有欢迎消息
      const hasWelcomeMessage = messages.value.some(msg => 
        msg.type === 'assistant' && msg.isWelcomeMessage && msg.agentId === agentId
      )
      
      // 如果今天已经显示过且当前消息列表中没有欢迎消息，则不再显示
      if (!shouldShowWelcome && !hasWelcomeMessage) {
        console.log(`今天(${today})已经显示过${agentId}的欢迎语，不再重复显示`)
        return
      }
      
      // 如果消息列表中已有欢迎消息，不再添加新的
      if (hasWelcomeMessage) {
        console.log(`当前消息列表中已有${agentId}的欢迎消息，不再添加`)
        return
      }
      
      console.log(`显示${agentId}的欢迎语，并记录显示日期: ${today}`)
      
      // 显示欢迎语并记录今天已显示
      messages.value.push({ 
        type: 'assistant', 
        content: agentInfo.message,
        timestamp: formatTime(),
        agentId: agentId,
        isWelcomeMessage: true // 标记为欢迎消息
      })
      
      // 记录今天已经显示过欢迎消息
      localStorage.setItem(welcomeLastShownKey, today)
      hasShownWelcome.value[agentId] = true
      
      // 只有在确实添加了欢迎消息到界面时，才请求欢迎语音频
      console.log(`请求${agentId}的欢迎语音频`)
      fetch(getApiUrl('welcome_tts'), {
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
          console.log(`收到${agentId}的欢迎语音频，长度:`, data.audio.length)
          playAudio(data.audio)
        }
      })
      .catch(error => {
        console.error('获取欢迎语音频失败:', error)
      })
    }
  }
  
  // 强制结束引导式会话
  function forceEndGuidance() {
    console.log('强制结束引导式会话')
    
    // 主动发送一个结束指令到后端
    // 这个请求可以是一个简单的通知，不需要等待响应
    try {
      fetch(getApiUrl('end_guidance'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          session_id: 'default',
          agent_type: currentAgent.value
        }),
      }).catch(err => console.error('发送结束引导请求失败:', err))
    } catch (e) {
      console.error('发送结束引导请求出错:', e)
    }
    
    // 触发引导式会话结束事件
    setTimeout(() => {
      const guidanceEndEvent = new CustomEvent('guidance-end', {
        detail: { type: 'force-end', category: null }
      })
      window.dispatchEvent(guidanceEndEvent)
      console.log('已发送强制结束引导事件')
    }, 100)
  }
  
  // 保存消息到localStorage和后端
  async function saveMessages() {
    // 防止重复保存 - 使用一个标志控制
    if (saveMessages.isSaving) {
      console.log('已有保存操作正在进行中，跳过')
      return
    }

    // 使用用户名作为唯一标识符，这样每个账号都有自己的历史记录
    const username = userStore.userProfile?.username || userStore.userProfile?.name || 'guest'
    if (username === 'guest') {
      console.log('未登录用户，不保存聊天记录')
      return // 不保存未登录用户的聊天记录
    }
    
    // 如果没有消息，不需要保存
    if (messages.value.length === 0) {
      console.log('没有消息需要保存')
      return
    }
    
    // 检查是否有正在流式传输的消息，如果有则不保存
    const hasStreamingMessage = messages.value.some(msg => msg.isStreaming === true)
    if (hasStreamingMessage) {
      console.log('有消息正在流式传输中，延迟保存')
      return
    }
    
    // 设置保存标志
    saveMessages.isSaving = true
    
    try {
      // 向消息对象添加元数据标记，确保所有类型的消息都能被正确处理
      const messagesWithMetadata = messages.value.map(msg => {
        // 检查是否是主题提问类消息
        const isQuickQuestion = [
          "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
          "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
        ].includes(msg.content);
        
        return {
          ...msg,
          isQuickQuestion: msg.isQuickQuestion || isQuickQuestion,
          saveTime: new Date().toISOString()
        }
      })
      
      // 1. 首先存储到后端数据库
      try {
        // 导入API模块
        const apiModule = await import('../utils/api')
        const apiUrl = apiModule.getApiUrl('save_chat_history')
        
        // 发送保存请求
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            username: username,
            messages: messagesWithMetadata
          })
        })
        
        const result = await response.json()
        if (result.success) {
          console.log('聊天历史成功保存到后端数据库', new Date().toLocaleTimeString())
        } else {
          console.warn('保存聊天历史到后端数据库失败，将回退到localStorage:', result.message)
          // 保存失败时，回退到localStorage
          saveToLocalStorage(username, messagesWithMetadata)
        }
      } catch (error) {
        console.error('保存聊天历史到后端数据库时出错，将回退到localStorage:', error)
        // 出错时回退到localStorage
        saveToLocalStorage(username, messagesWithMetadata)
      }
    } finally {
      // 无论成功失败，清除保存标志
      saveMessages.isSaving = false
    }
  }
  
  // 辅助函数：保存到localStorage
  function saveToLocalStorage(username, messagesData) {
    try {
      const key = `chat_history_${username}`
      localStorage.setItem(key, JSON.stringify({
        messages: messagesData,
        timestamp: Date.now()
      }))
      console.log('聊天历史已保存到localStorage备份')
    } catch (e) {
      console.error('保存到localStorage失败:', e)
    }
  }
  
  // 加载消息，首先尝试从后端加载，如果失败则从localStorage加载
  async function loadMessages() {
    // 使用用户名作为唯一标识符
    const username = userStore.userProfile?.username || userStore.userProfile?.name || 'guest'
    if (username === 'guest') {
      console.log('未登录用户，不加载聊天记录')
      return false
    }
    
    // 记录加载开始时间，用于调试
    const startTime = Date.now()
    
    // 1. 尝试从后端数据库加载
    try {
      // 导入API模块
      const apiModule = await import('../utils/api')
      const apiUrl = apiModule.getApiUrl(`load_chat_history/${username}`)
      
      // 发送加载请求
      const response = await fetch(apiUrl)
      const result = await response.json()
      
      if (result.success && Array.isArray(result.messages) && result.messages.length > 0) {
        // 使用从后端加载的消息替换当前消息
        messages.value = result.messages
        console.log(`从后端数据库加载了${result.messages.length}条消息历史，耗时${Date.now() - startTime}ms`)
        return true
      } else {
        console.log('后端未找到聊天历史或历史为空，尝试从localStorage加载')
        // 从后端加载失败，尝试从localStorage加载
        return loadMessagesFromLocalStorage(username)
      }
    } catch (error) {
      console.error('从后端加载聊天历史失败，尝试从localStorage加载:', error)
      // 出错时尝试从localStorage加载
      return loadMessagesFromLocalStorage(username)
    }
  }
  
  // 从localStorage加载消息的辅助函数
  function loadMessagesFromLocalStorage(username) {
    try {
      const key = `chat_history_${username}`
      const savedData = localStorage.getItem(key)
      
      if (savedData) {
        const data = JSON.parse(savedData)
        if (Array.isArray(data.messages) && data.messages.length > 0) {
          // 使用从localStorage加载的消息替换当前消息
          messages.value = data.messages
          console.log(`从localStorage加载了${data.messages.length}条消息历史`)
          return true
        }
      }
      
      console.log('localStorage中没有找到聊天历史')
      return false
    } catch (e) {
      console.error('从localStorage加载聊天历史失败:', e)
      return false
    }
  }
  
  // 与后端同步消息
  async function syncMessages(username, messagesData) {
    if (!username || username === 'guest' || !Array.isArray(messagesData)) {
      console.log('无效的同步参数，跳过同步操作')
      return false
    }
    
    try {
      // 导入API模块
      const apiModule = await import('../utils/api')
      
      // 发送同步请求
      const response = await fetch(apiModule.getApiUrl('save_chat_history'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          username: username,
          messages: messagesData
        })
      })
      
      const result = await response.json()
      console.log('消息同步结果:', result.success ? '成功' : '失败')
      return result.success
    } catch (error) {
      console.error('同步消息失败:', error)
      return false
    }
  }
  
  // 监听消息变化，保存到localStorage
  watch(messages, debounce(() => {
    // 检查是否有流式消息正在处理中
    const hasStreamingMessage = messages.value.some(msg => msg.isStreaming)
    if (hasStreamingMessage) {
      console.log('有消息正在流式处理中，延迟保存')
      return
    }
    
    // 检查是否有消息
    if (messages.value.length === 0) {
      console.log('没有消息需要保存')
      return
    }
    
    // 所有消息都完成后再保存
    console.log('所有消息流式处理已完成，保存消息')
    saveMessages()
  }, 2000), { deep: true }) // 延迟2秒，确保流式消息完全加载完毕
  
  // 监听用户变化，加载对应用户的消息
  watch(() => userStore.userProfile, () => {
    loadMessages()
  }, { deep: true })
  
  // 清空聊天记录
  async function clearMessages() {
    console.log('清空聊天记录')
    // 使用用户名作为唯一标识符
    const username = userStore.userProfile?.username || userStore.userProfile?.name || 'guest'
    if (username !== 'guest') {
      // 清除localStorage中的记录
      const key = `chat_history_${username}`
      localStorage.removeItem(key)
      console.log(`已清除用户 ${username} 的localStorage聊天记录`)
      
      // 注意：我们不再清除后端数据库中的记录，只清空前端显示
      console.log('保留后端数据库中的聊天记录，仅清空前端显示')
    }
    
    // 清空内存中的消息
    messages.value = []
    
    // 清空后只有在需要时才显示欢迎语
    showWelcomeMessage()
    
    return true
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
    useStreamResponse,
    // 方法
    initializeChat,
    setTrackingStatus,
    changeAgent,
    sendMessage,
    sendStreamMessage,
    showWelcomeMessage,
    loadCustomAgents,
    playAudio,
    forceEndGuidance,
    saveMessages,
    loadMessages,
    clearMessages
  }
}) 