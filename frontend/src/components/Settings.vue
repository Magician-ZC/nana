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
              <select 
                id="tts-voice"
                v-model="ttsVoice" 
                class="mt-1 block w-full rounded-md border-neutral-300 py-2 pl-3 pr-10 text-base focus:border-primary-500 focus:outline-none focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700 dark:text-white sm:text-sm"
              >
                <option 
                  v-for="voice in ttsVoiceList" 
                  :key="voice.value" 
                  :value="voice.value"
                >
                  {{ voice.name }}
                </option>
              </select>
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
              <select 
                id="super-tts-voice"
                v-model="superTtsVoice" 
                class="mt-1 block w-full rounded-md border-neutral-300 py-2 pl-3 pr-10 text-base focus:border-primary-500 focus:outline-none focus:ring-primary-500 dark:border-neutral-600 dark:bg-neutral-700 dark:text-white sm:text-sm"
              >
                <option 
                  v-for="voice in superTtsVoiceList" 
                  :key="voice.value" 
                  :value="voice.value"
                >
                  {{ voice.name }}
                </option>
              </select>
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
import { ref, onMounted, watch } from 'vue'
import { useChatStore } from '../stores/chat'

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

// 加载设置
onMounted(async () => {
  await loadSettings()
  // 初始化打字机效果设置
  useTypewriterEffect.value = chatStore.useStreamResponse
})

// 监听打开状态变化，打开时重新加载设置
watch(() => props.isOpen, async (newValue) => {
  if (newValue) {
    await loadSettings()
    // 重新同步打字机效果设置
    useTypewriterEffect.value = chatStore.useStreamResponse
  }
})

// 加载当前设置
async function loadSettings() {
  try {
    const response = await fetch('http://localhost:8666/api/tts_settings')
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
    
    const response = await fetch('http://localhost:8666/api/tts_settings', {
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
</style> 