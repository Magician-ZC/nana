<template>
  <div class="quick-questions-container">
    <div class="title-area">
      <div class="circle-icon">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
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
</template>

<script setup>
import { useChatStore } from '../stores/chat'

const chatStore = useChatStore()

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
</script>

<style scoped>
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

/* 媒体查询 - 移动端适配 */
@media (max-width: 768px) {
  .quick-questions-container {
    position: static;
    transform: none;
    width: 100%;
    margin-bottom: 15px;
    left: 0;
  }
}
</style> 