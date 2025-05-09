<template>
  <div class="app" :class="{ 'dark': isDarkMode }">
    <!-- 深色模式切换按钮 -->
    <button 
      @click="toggleDarkMode" 
      class="theme-toggle-btn"
      :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
    >
      <i :class="isDarkMode ? 'fa-solid fa-sun' : 'fa-solid fa-moon'"></i>
    </button>
    
    <div class="live2d-main">
      <!-- 权限测试组件 - 仅在开发环境中显示 -->
      <PermissionTest v-if="showPermissionTest" class="permission-test-container" />
    
      <!-- 添加情绪评估和心理评估按钮 -->
      <AssessmentButtons />
    
      <TimeWeather />
      <QuickQuestions />
      <Live2DModel ref="live2dRef" :modelId="chatStore.currentModel" />
      <div class="controls-container">
        <AgentSelector @agent-change="handleAgentChange" :currentModel="chatStore.currentAgent" />
        <SettingsButton class="settings-button" />
        <!-- 添加退出按钮 -->
        <button 
          @click="logout" 
          class="logout-button"
          title="退出登录"
        >
          <i class="fa-solid fa-sign-out-alt"></i>
        </button>
      </div>
      <ChatPanel />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from '../stores/chat'
import { useAssessmentStore } from '../stores/assessment'
import { useUserStore } from '../stores/user'
import { useRouter } from 'vue-router'
import Live2DModel from '../components/Live2DModel.vue'
import AgentSelector from '../components/AgentSelector.vue'
import ChatPanel from '../components/ChatPanel.vue'
import TimeWeather from '../components/TimeWeather.vue'
import QuickQuestions from '../components/QuickQuestions.vue'
import SettingsButton from '../components/SettingsButton.vue'
import AssessmentButtons from '../components/AssessmentButtons.vue'
import PermissionTest from '../components/PermissionTest.vue'
import { getApiUrl } from '../utils/api'

const router = useRouter()
const chatStore = useChatStore()
const assessmentStore = useAssessmentStore()
const userStore = useUserStore()
const live2dRef = ref(null)
const isDarkMode = ref(false)
// 权限测试组件显示控制 - 通过URL参数控制
const showPermissionTest = ref(false)

// 退出登录
const logout = async () => {
  await userStore.logout()
  router.push('/login')
}

// 初始化音频上下文
function initAudioContext() {
  console.log('初始化音频上下文...');
  try {
    // 创建音频上下文
    window.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    console.log('音频上下文创建成功:', window.audioContext.state);
    
    // 为初始用户交互设置事件
    const resumeAudioContext = () => {
      console.log('用户交互，恢复音频上下文');
      if (window.audioContext && window.audioContext.state === 'suspended') {
        window.audioContext.resume().then(() => {
          console.log('音频上下文已恢复到:', window.audioContext.state);
        });
      }
      
      // 尝试播放一个静音音频来解锁移动设备的音频
      try {
        const silentBuffer = window.audioContext.createBuffer(1, 1, 22050);
        const source = window.audioContext.createBufferSource();
        source.buffer = silentBuffer;
        source.connect(window.audioContext.destination);
        source.start(0);
        console.log('播放静音音频成功');
      } catch (e) {
        console.warn('播放静音音频失败:', e);
      }
      
      // 移除事件监听器
      document.removeEventListener('click', resumeAudioContext);
      document.removeEventListener('touchstart', resumeAudioContext);
      document.removeEventListener('keydown', resumeAudioContext);
    };
    
    // 添加事件监听器
    document.addEventListener('click', resumeAudioContext);
    document.addEventListener('touchstart', resumeAudioContext);
    document.addEventListener('keydown', resumeAudioContext);
  } catch (e) {
    console.error('初始化音频上下文失败:', e);
  }
}

// 请求欢迎语音频的函数
function requestWelcomeAudio() {
  // 获取当前角色信息
  const agentId = chatStore.currentAgent;
  const agentInfo = chatStore.currentAgentInfo;
  
  if (agentInfo && agentInfo.message) {
    // 检查今天是否已经显示过欢迎语
    const today = new Date().toLocaleDateString();
    const welcomeLastShownKey = `welcome_shown_${agentId}`;
    const welcomeLastShown = localStorage.getItem(welcomeLastShownKey);
    
    // 检查是否需要显示欢迎消息
    const shouldShowWelcome = !welcomeLastShown || welcomeLastShown !== today;
    
    // 检查页面刷新后是否已经有欢迎消息
    const hasWelcomeMessage = chatStore.messages.some(msg => 
      msg.type === 'assistant' && msg.isWelcomeMessage && msg.agentId === agentId
    );
    
    // 只有在需要显示欢迎消息的情况下才请求音频
    // 条件必须与showWelcomeMessage函数中的一致
    if ((!shouldShowWelcome && !hasWelcomeMessage) || hasWelcomeMessage) {
      console.log('不需要播放欢迎语音频，今天已经显示过或消息列表中已有欢迎消息');
      return; // 不播放欢迎音频
    }
    
    console.log('请求欢迎语音频...');
    // 在获取音频之前，可以显示加载状态
    if (live2dRef.value) {
      live2dRef.value.showExpression('default');
    }
    
    // 直接请求欢迎语音频
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
        console.log('欢迎语音频获取成功，准备播放');
        // 使用高优先级播放欢迎语音频
        chatStore.playAudio(data.audio, true);
        
        // 根据欢迎语内容设置表情
        const message = agentInfo.message;
        if (message.includes('？') || message.includes('?')) {
          live2dRef.value?.showExpression('惊讶');
        } else if (message.includes('！') || message.includes('!')) {
          live2dRef.value?.showExpression('兴奋');
        } else {
          // 默认表情
          const defaultExpressions = {
            'nanaA': '酷酷',
            'nanaB': '开心',
            'nanaC': '害羞',
          };
          live2dRef.value?.showExpression(defaultExpressions[chatStore.currentModel] || '酷酷');
        }
        
        // 1.5秒后恢复默认表情
        setTimeout(() => {
          live2dRef.value?.showExpression('default', false);
        }, 1500);
      }
    })
    .catch(error => {
      console.error('初始欢迎语音频失败:', error);
      // 错误时恢复默认表情
      live2dRef.value?.showExpression('default', false);
    });
  }
}

// 切换深色/浅色模式
const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value
  // 保存用户偏好到本地存储
  localStorage.setItem('darkMode', isDarkMode.value)
  updateTheme()
}

// 更新主题
const updateTheme = () => {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// 检查系统偏好
const checkSystemPreference = () => {
  // 先检查用户之前的设置
  const savedPreference = localStorage.getItem('darkMode')
  
  if (savedPreference !== null) {
    // 如果有保存的设置，使用它
    isDarkMode.value = savedPreference === 'true'
  } else {
    // 否则使用系统偏好
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDarkMode.value = prefersDark
  }
  
  updateTheme()
}

// 当收到消息更新和表情设置
watch(() => chatStore.messages, async (newMessages, oldMessages) => {
  // 仅在有新增消息且是助手消息的情况下处理
  if (newMessages.length > oldMessages.length && 
      newMessages[newMessages.length - 1].type === 'assistant') {
    
    const lastMessage = newMessages[newMessages.length - 1].content
    
    // 根据消息内容设置不同表情
    if (lastMessage.includes('？') || lastMessage.includes('?')) {
      // 问句使用惊讶表情
      live2dRef.value?.showExpression('惊讶')
    } else if (lastMessage.includes('！') || lastMessage.includes('!')) {
      // 感叹句使用兴奋表情
      live2dRef.value?.showExpression('兴奋')
    } else if (lastMessage.length < 10) {
      // 短句使用傲娇表情
      live2dRef.value?.showExpression('傲娇')
    } else {
      // 默认表情
      const defaultExpressions = {
        'nanaA': '酷酷',
        'nanaB': '开心',
        'nanaC': '害羞',
      }
      live2dRef.value?.showExpression(defaultExpressions[chatStore.currentModel] || '酷酷')
    }
    
    // 1.5秒后恢复默认表情
    setTimeout(() => {
      live2dRef.value?.showExpression('default', false)
    }, 1500)
  }
}, { deep: true })

// 处理agent变更
const handleAgentChange = (modelId) => {
  console.log('App收到形象变更:', modelId)
  if (live2dRef.value) {
    live2dRef.value.changeModel(modelId)
  }
}

// 设置键盘快捷键（空格键）控制模型的跟踪功能
const handleKeyPress = (e) => {
  if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
    e.preventDefault() // 防止空格键触发其他操作
    const newTrackingStatus = !chatStore.isTracking
    chatStore.setTrackingStatus(newTrackingStatus)
    if (live2dRef.value) {
      live2dRef.value.setTracking(newTrackingStatus)
    }
  }
}

onMounted(async () => {
  // 检查URL参数，决定是否显示权限测试
  const urlParams = new URLSearchParams(window.location.search);
  showPermissionTest.value = urlParams.has('test-permissions');
  
  // 初始化音频上下文
  initAudioContext()
  
  // 确保聊天历史已加载
  if (userStore.isLoggedIn) {
    console.log('Home组件挂载: 用户已登录，尝试加载聊天历史')
    try {
      const loaded = await chatStore.loadMessages()
      
      // 加载后再检查是否需要显示欢迎消息
      const hasMessages = chatStore.messages.length > 0
      const hasWelcomeMessage = chatStore.messages.some(msg => msg.isWelcomeMessage)
      
      if (!loaded || !hasMessages) {
        console.log('Home组件挂载: 没有聊天历史或加载失败，显示欢迎消息')
        chatStore.showWelcomeMessage()
      } else if (!hasWelcomeMessage) {
        // 有聊天记录但没有欢迎消息，添加欢迎消息
        console.log('Home组件挂载: 有聊天历史但没有欢迎消息，添加欢迎消息')
        chatStore.showWelcomeMessage()
      } else {
        console.log('Home组件挂载: 已成功加载聊天历史，消息数量:', chatStore.messages.length)
      }
    } catch (error) {
      console.error('Home组件挂载: 加载聊天历史失败', error)
      chatStore.showWelcomeMessage()
    }
  } else {
    console.log('Home组件挂载: 用户未登录，不加载聊天历史')
  }
  
  // 检查并应用主题设置
  checkSystemPreference()
  
  // 初始化评估状态
  try {
    await assessmentStore.initialize()
  } catch (e) {
    console.error('初始化评估状态失败:', e)
  }
  
  window.addEventListener('keydown', handleKeyPress)
  // 加载自定义角色列表
  chatStore.loadCustomAgents()
  
  // 监听系统主题变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
    // 只有当用户没有手动设置过主题时，才跟随系统变化
    if (localStorage.getItem('darkMode') === null) {
      isDarkMode.value = e.matches
      updateTheme()
    }
  })
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyPress)
})
</script>

<style scoped>
.logout-button {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.logout-button:hover {
  transform: scale(1.1);
  background-color: #f05252;
}

.dark .logout-button {
  background-color: rgba(255, 255, 255, 0.2);
}

.dark .logout-button:hover {
  background-color: #f05252;
}
</style> 