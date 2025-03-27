<template>
  <div :class="['settings-panel', { 'open': isOpen }]">
    <div class="settings-content">
      <h3>语音设置</h3>
      <div class="settings-section">
        <div class="setting-item">
          <label>
            <input 
              type="checkbox" 
              v-model="enableTTS" 
              @change="handleTTSChange" 
              :disabled="enableSuperTTS"
            />
            启用普通语音
          </label>
        </div>
        <div class="setting-item">
          <label>
            <input 
              type="checkbox" 
              v-model="enableSuperTTS" 
              @change="handleSuperTTSChange" 
              :disabled="enableTTS"
            />
            启用超拟人语音
          </label>
          <div class="settings-note" v-if="enableSuperTTS">
            超拟人语音支持更自然的语气、语调变化和口语化表达
          </div>
        </div>
      </div>
      
      <div class="settings-actions">
        <button class="apply-button" @click="saveSettings">应用</button>
        <button class="close-button" @click="$emit('close')">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'settings-changed'])

// 设置状态
const enableTTS = ref(false)
const enableSuperTTS = ref(false)
const isSaving = ref(false)
const error = ref('')

// 加载设置
onMounted(async () => {
  await loadSettings()
})

// 监听打开状态变化，打开时重新加载设置
watch(() => props.isOpen, async (newValue) => {
  if (newValue) {
    await loadSettings()
  }
})

// 加载当前设置
async function loadSettings() {
  try {
    const response = await fetch('http://localhost:8666/api/tts_settings')
    const data = await response.json()
    
    enableTTS.value = data.enable_tts
    enableSuperTTS.value = data.enable_super_tts
    
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

// 保存设置
async function saveSettings() {
  isSaving.value = true
  error.value = ''
  
  try {
    const response = await fetch('http://localhost:8666/api/tts_settings', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        enable_tts: enableTTS.value,
        enable_super_tts: enableSuperTTS.value
      })
    })
    
    const result = await response.json()
    
    if (result.success) {
      // 通知父组件设置已更改
      emit('settings-changed', {
        enableTTS: enableTTS.value,
        enableSuperTTS: enableSuperTTS.value
      })
      
      // 关闭设置面板
      emit('close')
    } else {
      error.value = result.message || '保存设置失败'
    }
    
  } catch (error) {
    console.error('保存设置失败:', error)
    error.value = '保存设置时发生错误'
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
.settings-panel {
  position: fixed;
  top: 0;
  right: -350px;
  width: 300px;
  height: 100vh;
  background-color: rgba(30, 30, 30, 0.9);
  box-shadow: -2px 0 10px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  transition: right 0.3s ease;
  backdrop-filter: blur(10px);
  color: #fff;
  overflow-y: auto;
}

.settings-panel.open {
  right: 0;
}

.settings-content {
  padding: 20px;
}

h3 {
  margin-top: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  padding-bottom: 10px;
  margin-bottom: 15px;
}

.settings-section {
  margin-bottom: 20px;
}

.setting-item {
  margin-bottom: 12px;
  display: flex;
  flex-direction: column;
}

label {
  display: flex;
  align-items: center;
  cursor: pointer;
}

input[type="checkbox"] {
  margin-right: 8px;
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.settings-note {
  margin-top: 4px;
  font-size: 12px;
  color: #aaa;
  margin-left: 24px;
}

.settings-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.apply-button, .close-button {
  padding: 8px 15px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.apply-button {
  background-color: #2c7c7e;
  color: white;
}

.apply-button:hover {
  background-color: #3a9a9c;
}

.close-button {
  background-color: #444;
  color: white;
}

.close-button:hover {
  background-color: #555;
}

.error-message {
  color: #ff6b6b;
  margin-top: 10px;
  font-size: 14px;
}
</style> 