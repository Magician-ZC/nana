<template>
  <div class="settings-container">
    <button 
      @click="toggleSettings" 
      class="settings-toggle-btn"
      :title="isSettingsOpen ? '关闭设置' : '打开设置'"
    >
      <i class="fa-solid fa-cog"></i>
    </button>
    
    <Settings 
      :isOpen="isSettingsOpen" 
      @close="closeSettings"
      @settings-changed="handleSettingsChanged"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Settings from './Settings.vue'

const isSettingsOpen = ref(false)

function toggleSettings() {
  isSettingsOpen.value = !isSettingsOpen.value
}

function closeSettings() {
  isSettingsOpen.value = false
}

function handleSettingsChanged(settings) {
  console.log('设置已更改:', settings)
  if (settings.enableTTS) {
    console.log('已启用普通语音，选择音色:', settings.ttsVoice)
  } else if (settings.enableSuperTTS) {
    console.log('已启用超拟人语音，选择音色:', settings.superTtsVoice)
  } else {
    console.log('已禁用所有语音')
  }
}
</script>

<style scoped>
.settings-container {
  position: relative;
}

.settings-toggle-btn {
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

.settings-toggle-btn:hover {
  transform: scale(1.1);
  background-color: rgba(50, 50, 50, 0.8);
}

.settings-toggle-btn i {
  font-size: 18px;
}
</style> 