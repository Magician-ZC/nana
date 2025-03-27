<template>
  <!-- 遮罩层 -->
  <div v-if="isOpen" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-50 flex items-center justify-center transition-all duration-300 ease-in-out" @click="$emit('close')">
    <!-- 主内容区 -->
    <div class="w-full max-w-xl max-h-[90vh] overflow-y-auto bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in" @click.stop>
      <!-- 顶部标题栏 -->
      <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
        <h3 class="text-xl font-semibold text-neutral-800 dark:text-white">系统设置</h3>
        <button 
          @click="$emit('close')" 
          class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
        >
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- 内容区 -->
      <div class="p-6 space-y-6">
        <!-- 聊天效果设置 -->
        <div class="space-y-4">
          <h4 class="text-lg font-medium text-neutral-800 dark:text-neutral-200 border-b border-neutral-200 dark:border-neutral-700 pb-2">聊天效果</h4>
          
          <div class="space-y-4">
            <!-- 打字机效果设置 -->
            <div class="flex items-start">
              <div class="flex h-5 items-center">
                <input 
                  id="typewriter-effect"
                  type="checkbox" 
                  v-model="useTypewriterEffect" 
                  @change="handleTypewriterChange"
                  class="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700"
                />
              </div>
              <div class="ml-3 text-sm">
                <label for="typewriter-effect" class="font-medium text-neutral-700 dark:text-neutral-300">启用打字机效果</label>
                <p class="text-neutral-500 dark:text-neutral-400">启用后AI回复将逐字显示，模拟打字机效果</p>
              </div>
            </div>

            <!-- 打字速度控制 -->
            <div v-if="useTypewriterEffect" class="pl-7 space-y-2">
              <div class="flex justify-between items-center">
                <label for="typing-speed" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">打字速度</label>
                <span class="text-sm text-neutral-500 dark:text-neutral-400">{{ typingSpeed }}ms/字</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-xs text-neutral-500 dark:text-neutral-400">快</span>
                <input 
                  id="typing-speed"
                  type="range" 
                  v-model="typingSpeed" 
                  min="10" 
                  max="200" 
                  step="5"
                  class="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer dark:bg-neutral-700" 
                />
                <span class="text-xs text-neutral-500 dark:text-neutral-400">慢</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 语音设置 -->
        <div class="space-y-4">
          <h4 class="text-lg font-medium text-neutral-800 dark:text-neutral-200 border-b border-neutral-200 dark:border-neutral-700 pb-2">语音设置</h4>
          
          <div class="space-y-4">
            <!-- 普通语音设置 -->
            <div class="flex items-start">
              <div class="flex h-5 items-center">
                <input 
                  id="normal-tts"
                  type="checkbox" 
                  v-model="enableTTS" 
                  @change="handleTTSChange" 
                  :disabled="enableSuperTTS"
                  class="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700"
                />
              </div>
              <div class="ml-3 text-sm">
                <label for="normal-tts" class="font-medium text-neutral-700 dark:text-neutral-300">启用普通语音</label>
              </div>
            </div>

            <!-- 普通语音音色选择 -->
            <div v-if="enableTTS" class="pl-7 space-y-2">
              <label for="tts-voice" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">音色选择</label>
              <!-- 自定义下拉选择框 -->
              <div class="relative dropdown-container">
                <button 
                  type="button" 
                  @click="toggleDropdown('tts')"
                  class="relative w-full bg-white dark:bg-neutral-700 border border-neutral-300 dark:border-neutral-600 rounded-md py-2 pl-3 pr-10 text-left text-neutral-700 dark:text-white cursor-default focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                >
                  <span class="block truncate">{{ getTtsVoiceName(ttsVoice) }}</span>
                  <span class="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                    <i class="fa-solid fa-chevron-down text-neutral-400"></i>
                  </span>
                </button>
                
                <!-- 下拉选项列表 -->
                <div 
                  v-show="openDropdown === 'tts'"
                  class="absolute z-10 mt-1 w-full bg-white dark:bg-neutral-700 shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm"
                >
                  <div
                    v-for="voice in ttsVoiceList" 
                    :key="voice.value"
                    @click="selectVoice('tts', voice.value)"
                    :class="['cursor-pointer select-none relative py-2 pl-3 pr-9', 
                      ttsVoice === voice.value ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-200' : 'text-neutral-700 dark:text-white hover:bg-neutral-100 dark:hover:bg-neutral-600'
                    ]"
                  >
                    {{ voice.name }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 超拟人语音设置 -->
            <div class="flex items-start">
              <div class="flex h-5 items-center">
                <input 
                  id="super-tts"
                  type="checkbox" 
                  v-model="enableSuperTTS" 
                  @change="handleSuperTTSChange" 
                  :disabled="enableTTS"
                  class="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700"
                />
              </div>
              <div class="ml-3 text-sm">
                <label for="super-tts" class="font-medium text-neutral-700 dark:text-neutral-300">启用超拟人语音</label>
                <p v-if="enableSuperTTS" class="text-neutral-500 dark:text-neutral-400">超拟人语音支持更自然的语气、语调变化和口语化表达</p>
              </div>
            </div>

            <!-- 超拟人语音音色选择 -->
            <div v-if="enableSuperTTS" class="pl-7 space-y-2">
              <label for="super-tts-voice" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300">音色选择</label>
              <!-- 自定义下拉选择框 -->
              <div class="relative dropdown-container">
                <button 
                  type="button" 
                  @click="toggleDropdown('super')"
                  class="relative w-full bg-white dark:bg-neutral-700 border border-neutral-300 dark:border-neutral-600 rounded-md py-2 pl-3 pr-10 text-left text-neutral-700 dark:text-white cursor-default focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
                >
                  <span class="block truncate">{{ getSuperTtsVoiceName(superTtsVoice) }}</span>
                  <span class="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
                    <i class="fa-solid fa-chevron-down text-neutral-400"></i>
                  </span>
                </button>
                
                <!-- 下拉选项列表 -->
                <div 
                  v-show="openDropdown === 'super'"
                  class="absolute z-10 mt-1 w-full bg-white dark:bg-neutral-700 shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm"
                >
                  <div
                    v-for="voice in superTtsVoiceList" 
                    :key="voice.value"
                    @click="selectVoice('super', voice.value)"
                    :class="['cursor-pointer select-none relative py-2 pl-3 pr-9', 
                      superTtsVoice === voice.value ? 'bg-primary-100 dark:bg-primary-900/50 text-primary-700 dark:text-primary-200' : 'text-neutral-700 dark:text-white hover:bg-neutral-100 dark:hover:bg-neutral-600'
                    ]"
                  >
                    {{ voice.name }}
                  </div>
                </div>
              </div>
            </div>

            <!-- 语速控制 -->
            <div v-if="enableTTS || enableSuperTTS" class="pl-7 space-y-2">
              <div class="flex justify-between items-center">
                <label for="tts-speed" class="text-sm font-medium text-neutral-700 dark:text-neutral-300">语速</label>
                <span class="text-sm text-neutral-500 dark:text-neutral-400">{{ ttsSpeed }}</span>
              </div>
              <div class="flex items-center space-x-2">
                <span class="text-xs text-neutral-500 dark:text-neutral-400">慢</span>
                <input 
                  id="tts-speed"
                  type="range" 
                  v-model="ttsSpeed" 
                  min="0" 
                  max="100" 
                  step="5"
                  class="w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer dark:bg-neutral-700" 
                />
                <span class="text-xs text-neutral-500 dark:text-neutral-400">快</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部按钮栏 -->
      <div class="flex items-center justify-end p-5 border-t border-neutral-200 dark:border-neutral-700 gap-3">
        <button 
          @click="$emit('close')" 
          class="px-4 py-2 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all duration-200 font-medium"
        >
          取消
        </button>
        <button 
          @click="saveSettings" 
          :disabled="isSaving"
          class="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white transition-all duration-200 font-medium flex items-center disabled:opacity-50 disabled:pointer-events-none"
        >
          <i class="fa-solid fa-save mr-2"></i>
          {{ isSaving ? '保存中...' : '应用' }}
        </button>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="p-3 mb-4 mx-5 bg-red-100 border border-red-200 text-red-700 rounded-md dark:bg-red-900/30 dark:border-red-800 dark:text-red-300">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onUnmounted } from 'vue'
import { useChatStore, getApiBaseUrl } from '../stores/chat'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'settings-changed'])
const chatStore = useChatStore()

// 打字机效果设置
const useTypewriterEffect = ref(true)
const typingSpeed = ref(38) // 打字速度，默认38ms/字

// 设置状态
const enableTTS = ref(false)
const enableSuperTTS = ref(false)
const ttsVoice = ref('xiaoyan')
const superTtsVoice = ref('x4_lingfeiyi_oral')
const ttsVoiceList = ref([])
const superTtsVoiceList = ref([])
const ttsSpeed = ref(50) // 语速，默认50
const isSaving = ref(false)
const error = ref('')
const isDarkMode = ref(false)
const openDropdown = ref(null)

// 检测当前模式是否为暗色模式
const checkDarkMode = () => {
  isDarkMode.value = document.documentElement.classList.contains('dark')
}

// 加载设置
onMounted(async () => {
  await loadSettings()
  // 初始化打字机效果设置
  useTypewriterEffect.value = chatStore.useStreamResponse
  // 检测暗色模式
  checkDarkMode()
  // 监听暗色模式变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', checkDarkMode)
  // 添加点击事件监听，用于关闭下拉菜单
  document.addEventListener('click', handleOutsideClick, true)
})

// 组件卸载时清除监听器
onUnmounted(() => {
  window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', checkDarkMode)
  document.removeEventListener('click', handleOutsideClick, true)
})

// 监听打开状态变化，打开时重新加载设置
watch(() => props.isOpen, async (newValue) => {
  if (newValue) {
    await loadSettings()
    // 重新同步打字机效果设置
    useTypewriterEffect.value = chatStore.useStreamResponse
    // 重新检测暗色模式
    checkDarkMode()
  }
})

// 加载当前设置
async function loadSettings() {
  try {
    const response = await fetch(`${getApiBaseUrl()}/api/tts_settings`)
    const data = await response.json()
    
    enableTTS.value = data.enable_tts
    enableSuperTTS.value = data.enable_super_tts
    ttsVoice.value = data.tts_voice || 'xiaoyan'
    superTtsVoice.value = data.super_tts_voice || 'x4_lingfeiyi_oral'
    ttsVoiceList.value = data.tts_voice_list || []
    superTtsVoiceList.value = data.super_tts_voice_list || []
    ttsSpeed.value = data.tts_speed || 50
    typingSpeed.value = data.typing_speed || 38
    
  } catch (error) {
    console.error('加载设置失败:', error)
  }
}

// 处理普通TTS切换
function handleTTSChange() {
  if (enableTTS.value) {
    enableSuperTTS.value = false
  }
}

// 处理超拟人TTS切换
function handleSuperTTSChange() {
  if (enableSuperTTS.value) {
    enableTTS.value = false
  }
}

// 处理打字机效果切换
function handleTypewriterChange() {
  chatStore.useStreamResponse = useTypewriterEffect.value
}

// 保存设置
async function saveSettings() {
  isSaving.value = true
  error.value = ''
  
  try {
    // 更新打字机效果设置
    chatStore.useStreamResponse = useTypewriterEffect.value
    
    const response = await fetch(`${getApiBaseUrl()}/api/tts_settings`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        enable_tts: enableTTS.value,
        enable_super_tts: enableSuperTTS.value,
        tts_voice: ttsVoice.value,
        super_tts_voice: superTtsVoice.value,
        tts_speed: ttsSpeed.value,
        typing_speed: typingSpeed.value
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      // 通知父组件设置已更改
      emit('settings-changed', {
        enableTTS: enableTTS.value,
        enableSuperTTS: enableSuperTTS.value,
        ttsVoice: ttsVoice.value,
        superTtsVoice: superTtsVoice.value,
        ttsSpeed: ttsSpeed.value,
        typingSpeed: typingSpeed.value,
        useTypewriterEffect: useTypewriterEffect.value
      })
      
      // 关闭设置面板
      emit('close')
      
      // 显示成功消息
      showToast('设置已保存', 'success')
    } else {
      error.value = result.message || '保存设置失败'
    }
    
  } catch (err) {
    console.error('保存设置失败:', err)
    error.value = '保存设置时发生错误'
  } finally {
    isSaving.value = false
  }
}

// 显示消息通知
function showToast(message, type = 'success') {
  const toastEl = document.createElement('div')
  toastEl.className = `fixed bottom-4 right-4 ${type === 'success' ? 'bg-green-500' : 'bg-red-500'} text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in`
  toastEl.textContent = message
  document.body.appendChild(toastEl)
  
  setTimeout(() => {
    toastEl.remove()
  }, 3000)
}

// 自定义下拉选择框
function toggleDropdown(type) {
  openDropdown.value = type
}

// 获取TTS语音名称
function getTtsVoiceName(value) {
  const voice = ttsVoiceList.value.find(v => v.value === value)
  return voice ? voice.name : '未选择'
}

// 获取超拟人语音名称
function getSuperTtsVoiceName(value) {
  const voice = superTtsVoiceList.value.find(v => v.value === value)
  return voice ? voice.name : '未选择'
}

// 选择语音
function selectVoice(type, value) {
  if (type === 'tts') {
    ttsVoice.value = value
  } else if (type === 'super') {
    superTtsVoice.value = value
  }
  openDropdown.value = null
}

// 处理点击外部关闭下拉菜单
function handleOutsideClick(e) {
  if (openDropdown.value && !e.target.closest('.dropdown-container')) {
    openDropdown.value = null
  }
}
</script>

<style scoped>
/* 淡入动画 */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}

/* 修改range滑块的默认样式 */
input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #2c7c7e;
  cursor: pointer;
  transition: background-color 0.2s;
}

input[type="range"]::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #2c7c7e;
  cursor: pointer;
  transition: background-color 0.2s;
}

:deep(.dark) input[type="range"]::-webkit-slider-thumb {
  background: #4a9a9c;
}

:deep(.dark) input[type="range"]::-moz-range-thumb {
  background: #4a9a9c;
}

/* 全局修复select和option样式 */
:deep(select) {
  background-color: white !important;
  color: black !important;
  border-color: #d1d5db !important;
}

:deep(select option) {
  background-color: white !important;
  color: black !important;
  padding: 8px !important;
}

/* 暗色模式覆盖 */
:deep(.dark select) {
  background-color: #374151 !important;
  color: white !important;
  border-color: #4b5563 !important;
}

:deep(.dark select option) {
  background-color: #374151 !important;
  color: white !important;
}

/* 特别针对语音设置中的select */
#tts-voice,
#super-tts-voice {
  background-color: white !important;
  color: black !important;
}

.dark #tts-voice,
.dark #super-tts-voice {
  background-color: #374151 !important;
  color: white !important;
}
</style> 