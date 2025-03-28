<template>
  <!-- 桌面版快速提问 -->
  <div class="quick-questions-container hidden md:block">
    <div class="title-area">
      <div class="circle-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <!-- 灯泡图标 -->
          <path d="M9 18h6"></path>
          <path d="M10 22h4"></path>
          <path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z"></path>
        </svg>
      </div>
      <span>快速提问</span>
    </div>
    
    <div class="questions-list">
      <button 
        v-for="(question, index) in questions" 
        :key="index" 
        class="question-button"
        @click="handleQuestionClick(question.text)"
      >
        <div class="question-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
          </svg>
        </div>
        <span>{{ question.text }}</span>
      </button>
    </div>
  </div>
  
  <!-- 移动端浮动按钮 -->
  <div 
    v-show="!isDesktop" 
    ref="floatingButton"
    class="mobile-floating-button md:hidden" 
    :class="{ 'active': isExpanded }"
    :style="{ left: buttonPosition.x + 'px', top: buttonPosition.y + 'px' }"
    @click.stop="toggleExpand"
    @touchstart="startDrag"
    @touchmove="onDrag"
    @touchend="endDrag"
  >
    <!-- 按钮图标 -->
    <div class="button-icon" :class="{ 'rotate-45': isExpanded }">
      <svg v-if="!isExpanded" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <!-- 灯泡图标 -->
        <path d="M9 18h6"></path>
        <path d="M10 22h4"></path>
        <path d="M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z"></path>
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </div>
    
    <!-- 展开的气泡菜单 -->
    <div 
      v-if="isExpanded" 
      class="bubble-menu"
      @click.stop
    >
      <div 
        v-for="(question, index) in questions" 
        :key="index" 
        class="bubble-item"
        :style="{ 
          transitionDelay: `${index * 0.05}s`, 
          transform: `scale(${isExpanded ? 1 : 0}) translate(${getItemPosition(index, questions.length).x}px, ${getItemPosition(index, questions.length).y}px)` 
        }"
        @click="selectQuestion(question.text)"
      >
        {{ question.text }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { useChatStore } from '../stores/chat'
import { ref, onMounted, onUnmounted, computed } from 'vue'

const chatStore = useChatStore()
const isExpanded = ref(false)
const isDesktop = ref(window.innerWidth >= 768)
const isDragging = ref(false)
const floatingButton = ref(null)
const buttonPosition = ref({ x: 20, y: window.innerHeight / 2 })
const dragStart = ref({ x: 0, y: 0 })

// 定义提问选项
const questions = [
  { text: "情感咨询师" },
  { text: "人际关系" },
  { text: "学业问题" },
  { text: "就业与职业规划压力" },
  { text: "精神健康障碍" },
  { text: "自我认同与价值观冲突" },
  { text: "突发事件与危机情景" }
]

// 处理快捷提问点击事件
const handleQuestionClick = (questionText) => {
  chatStore.sendMessage(questionText)
}

// 切换展开/收起状态
const toggleExpand = () => {
  if (isDragging.value) return
  isExpanded.value = !isExpanded.value
}

// 选择问题后收起菜单
const selectQuestion = (questionText) => {
  chatStore.sendMessage(questionText)
  isExpanded.value = false
}

// 开始拖动
const startDrag = (event) => {
  isDragging.value = false
  const touch = event.touches[0]
  dragStart.value = { 
    x: touch.clientX - buttonPosition.value.x, 
    y: touch.clientY - buttonPosition.value.y 
  }
  
  // 防止长按触发上下文菜单
  event.preventDefault()
}

// 拖动中
const onDrag = (event) => {
  if (event.touches && event.touches[0]) {
    isDragging.value = true
    const touch = event.touches[0]
    
    // 计算新位置
    let newX = touch.clientX - dragStart.value.x
    let newY = touch.clientY - dragStart.value.y
    
    // 限制范围，避免按钮拖出屏幕
    const buttonSize = 56
    const maxX = window.innerWidth - buttonSize
    const maxY = window.innerHeight - buttonSize
    
    newX = Math.max(0, Math.min(newX, maxX))
    newY = Math.max(0, Math.min(newY, maxY))
    
    buttonPosition.value = { x: newX, y: newY }
    
    // 防止页面滚动
    event.preventDefault()
  }
}

// 结束拖动
const endDrag = () => {
  // 短暂延迟以防止触发点击事件
  setTimeout(() => {
    isDragging.value = false
  }, 50)
}

// 计算气泡项的位置（环形排列）
const getItemPosition = (index, total) => {
  const radius = 100 // 气泡环形半径
  const angle = (index / total) * Math.PI * 2 - Math.PI / 2
  
  return {
    x: radius * Math.cos(angle),
    y: radius * Math.sin(angle)
  }
}

// 监听窗口大小变化
const handleResize = () => {
  isDesktop.value = window.innerWidth >= 768
  
  // 确保按钮不会超出屏幕
  const buttonSize = 56
  const maxX = window.innerWidth - buttonSize
  const maxY = window.innerHeight - buttonSize
  
  buttonPosition.value = {
    x: Math.min(buttonPosition.value.x, maxX),
    y: Math.min(buttonPosition.value.y, maxY)
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  
  // 从本地存储中恢复上次的按钮位置（如果有）
  const savedPosition = localStorage.getItem('quickAskButtonPosition')
  if (savedPosition) {
    try {
      const position = JSON.parse(savedPosition)
      
      // 验证位置是否在屏幕范围内
      const buttonSize = 56
      const maxX = window.innerWidth - buttonSize
      const maxY = window.innerHeight - buttonSize
      
      buttonPosition.value = {
        x: Math.min(Math.max(0, position.x), maxX),
        y: Math.min(Math.max(0, position.y), maxY)
      }
    } catch (e) {
      console.error('Error restoring button position:', e)
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  // 保存按钮位置到本地存储
  localStorage.setItem('quickAskButtonPosition', JSON.stringify(buttonPosition.value))
})
</script>

<style scoped>
/* 桌面版快速提问样式 */
.quick-questions-container {
  position: fixed;
  left: 30px;
  top: 50%;
  transform: translateY(-50%);
  width: 260px;
  background-color: rgba(30, 30, 30, 0.7);
  backdrop-filter: blur(10px);
  border-radius: 15px;
  padding: 15px;
  box-shadow: 0 5px 20px rgba(0, 0, 0, 0.2);
  z-index: 10;
  color: white;
  transition: all 0.3s ease;
}

.title-area {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
  font-weight: 500;
  font-size: 1.1rem;
  gap: 8px;
}

.circle-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(70, 130, 180, 0.3);
}

.questions-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.question-button {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: rgba(255, 255, 255, 0.1);
  border: none;
  border-radius: 12px;
  padding: 10px 12px;
  color: white;
  font-size: 0.9rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s ease;
  width: 100%;
}

.question-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
  transform: scale(1.03);
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.1);
}

.question-icon {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(70, 130, 180, 0.3);
  flex-shrink: 0;
}

/* 移动端浮动按钮样式 */
.mobile-floating-button {
  position: fixed;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background-color: rgba(255, 193, 7, 0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  color: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  z-index: 9999;
  cursor: pointer;
  user-select: none;
  touch-action: none;
  transition: transform 0.2s, background-color 0.3s;
}

.mobile-floating-button.active {
  background-color: rgba(220, 53, 69, 0.9);
  transform: rotate(45deg);
}

.button-icon {
  transition: transform 0.3s ease;
}

.button-icon.rotate-45 {
  transform: rotate(45deg);
}

/* 气泡菜单样式 */
.bubble-menu {
  position: absolute;
  top: 0;
  left: 0;
  width: 56px;
  height: 56px;
  z-index: -1;
  pointer-events: none;
}

.bubble-item {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: center;
  padding: 10px 15px;
  border-radius: 18px;
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
  font-size: 14px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
  white-space: nowrap;
  cursor: pointer;
  pointer-events: auto;
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  opacity: 0;
  animation: fadeIn 0.3s forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.5); }
  to { opacity: 1; transform: scale(1); }
}

/* 暗模式支持 */
@media (prefers-color-scheme: dark) {
  .bubble-item {
    background-color: rgba(48, 48, 48, 0.9);
    color: white;
  }
}
</style> 