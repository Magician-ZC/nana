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
        :disabled="isGuiding && currentCategory !== question.text"
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
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'

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

// 引导状态
const isGuiding = ref(false)
const currentCategory = ref(null)

// 监听聊天消息以更新引导状态
const updateGuidanceState = (message) => {
  if (questions.some(q => q.text === message)) {
    console.log("开始引导式提问:", message);
    isGuiding.value = true
    currentCategory.value = message
  }
}

// 处理快捷提问点击事件
const handleQuestionClick = (questionText) => {
  chatStore.sendMessage(questionText)
  updateGuidanceState(questionText)
}

// 检查消息是否包含结束引导的关键词
const containsEndGuidanceKeywords = (content) => {
  if (!content || typeof content !== 'string') return false;
  
  const lowerContent = content.toLowerCase();
  const endKeywords = [
    "已结束当前话题", "已经结束话题", "话题已结束", 
    "结束了本次", "结束了这个话题", "已经为您结束",
    "确定要结束", "确认结束", "要结束这个话题", 
    "确定不继续", "结束引导", "退出引导",
    "总结一下", "总结如下", "总结这次", 
    "建议如下"
  ];
  
  return endKeywords.some(keyword => lowerContent.includes(keyword));
}

// 监听聊天消息
chatStore.$subscribe((mutation, state) => {
  if (mutation.storeId === 'chat' && mutation.events.key === 'messages') {
    const lastMessage = state.messages[state.messages.length - 1]
    if (lastMessage && lastMessage.type === 'assistant') {
      try {
        // 尝试解析JSON
        const replyData = JSON.parse(lastMessage.content)
        if (replyData.is_summary) {
          console.log("检测到summary标记，结束引导");
          isGuiding.value = false
          currentCategory.value = null
        }
      } catch (e) {
        // 如果不是JSON格式，检查纯文本内容
        if (lastMessage.content && typeof lastMessage.content === 'string') {
          // 检查是否包含结束引导的关键词
          if (containsEndGuidanceKeywords(lastMessage.content)) {
            console.log("检测到会话结束关键词，解锁快速提问面板");
            isGuiding.value = false
            currentCategory.value = null
          }
        }
      }
    }
  }
})

// 双重保险：定期检查对话状态，如果检测到总结性回复但状态未更新，强制解锁
const checkGuidanceState = () => {
  if (!isGuiding.value) return;
  
  // 获取最近的几条消息
  const recentMessages = chatStore.messages.slice(-3);
  
  // 检查是否有结束的迹象（消息内容包含总结性语句）
  for (const msg of recentMessages) {
    if (msg.type === 'assistant' && containsEndGuidanceKeywords(msg.content)) {
      console.log("定期检查发现结束标志，解锁面板");
      isGuiding.value = false;
      currentCategory.value = null;
      break;
    }
  }
};

// 设置定期检查
onMounted(() => {
  // 每10秒检查一次状态
  const intervalId = setInterval(checkGuidanceState, 10000);
  
  // 组件卸载时清除定时器
  onUnmounted(() => {
    clearInterval(intervalId);
  });
});

// 监听路由变化，当用户切换页面或刷新时重置状态
watch(() => window.location.href, () => {
  if (isGuiding.value) {
    console.log("页面变化，重置引导状态");
    isGuiding.value = false;
    currentCategory.value = null;
  }
});
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

.question-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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