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
      <!-- 添加切换话题按钮 - 仅在引导模式下显示 -->
      <div class="topic-button-container" v-if="isGuiding">
        <button 
          @click="endCurrentTopic" 
          class="end-topic-button"
          @mouseenter="showTooltip = true"
          @mouseleave="showTooltip = false"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6 6 18"></path>
            <path d="m6 6 12 12"></path>
          </svg>
        </button>
        <div class="tooltip" v-show="showTooltip">点击按钮可以切换话题</div>
      </div>
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

// 提示框显示状态
const showTooltip = ref(false)

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

// 结束当前话题
const endCurrentTopic = () => {
  console.log("用户点击切换话题图标，强制结束引导")
  isGuiding.value = false
  currentCategory.value = null
  
  // 调用聊天存储的强制结束函数
  chatStore.forceEndGuidance()
  
  // 向用户发送提示消息
  chatStore.sendMessage("结束话题")
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
    "建议如下", "还有其他想讨论", "还有什么想讨论",
    "有其他想讨论", "已结束本次", "希望我的回答", 
    "希望我的建议", "希望对您有所帮助", "结束了引导",
    "结束话题", "退出话题", "返回主菜单"
  ];
  
  // 特殊处理：用户直接说"结束话题"等明确指令
  const exactEndCommands = ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"];
  if (exactEndCommands.includes(lowerContent.trim())) {
    console.log("用户明确指令结束话题:", lowerContent);
    return true;
  }
  
  return endKeywords.some(keyword => lowerContent.includes(keyword));
}

// 监听聊天消息
chatStore.$subscribe((mutation, state) => {
  if (mutation.storeId === 'chat' && mutation.events.key === 'messages') {
    const lastMessage = state.messages[state.messages.length - 1]
    
    // 检查用户消息是否是直接结束指令
    if (lastMessage && lastMessage.type === 'user') {
      const userMsg = lastMessage.content.toLowerCase().trim();
      const directEndCommands = ["结束话题", "退出话题", "返回主菜单", "结束引导", "退出引导"];
      
      if (directEndCommands.includes(userMsg)) {
        console.log("用户直接输入结束指令:", userMsg);
        isGuiding.value = false;
        currentCategory.value = null;
        console.log("已直接解锁快速提问面板");
        
        // 调用聊天存储的强制结束函数
        chatStore.forceEndGuidance();
        
        return; // 提前结束处理
      }
    }
    
    // 处理助手回复
    if (lastMessage && lastMessage.type === 'assistant') {
      console.log("收到助手消息，检查是否结束引导:", lastMessage.content.substring(0, 50) + "...");
      
      // 检查是否需要结束引导
      let shouldEndGuidance = false;
      
      try {
        // 尝试解析JSON (兼容后台直接返回JSON格式的情况)
        const replyData = JSON.parse(lastMessage.content);
        if (replyData.is_summary) {
          console.log("检测到summary标记，结束引导");
          shouldEndGuidance = true;
        }
      } catch (e) {
        // 不是JSON格式，继续检查其他情况
      }
      
      // 如果不是JSON或未检测到summary，检查纯文本内容是否包含结束关键词
      if (!shouldEndGuidance && lastMessage.content && typeof lastMessage.content === 'string') {
        if (containsEndGuidanceKeywords(lastMessage.content)) {
          console.log("检测到会话结束关键词，解锁快速提问面板");
          shouldEndGuidance = true;
        }
      }
      
      // 如果需要结束引导，解锁面板
      if (shouldEndGuidance) {
        isGuiding.value = false;
        currentCategory.value = null;
        console.log("引导式会话已结束，已解锁快速提问面板");
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
  
  // 监听引导结束事件
  const handleGuidanceEnd = (event) => {
    console.log("接收到引导结束事件:", event.detail);
    isGuiding.value = false;
    currentCategory.value = null;
  };
  
  window.addEventListener('guidance-end', handleGuidanceEnd);
  
  // 组件卸载时清除定时器和事件监听
  onUnmounted(() => {
    clearInterval(intervalId);
    window.removeEventListener('guidance-end', handleGuidanceEnd);
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
  position: relative;
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

/* 结束话题按钮样式 */
.topic-button-container {
  position: absolute;
  right: 0;
}

.end-topic-button {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255, 100, 100, 0.2);
  border: none;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.end-topic-button:hover {
  background: rgba(255, 100, 100, 0.4);
  transform: scale(1.1);
}

.tooltip {
  position: absolute;
  top: -35px;
  right: 0;
  background-color: rgba(0, 0, 0, 0.8);
  color: white;
  padding: 5px 10px;
  border-radius: 6px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 20;
}

.tooltip:after {
  content: "";
  position: absolute;
  top: 100%;
  right: 10px;
  border-width: 5px;
  border-style: solid;
  border-color: rgba(0, 0, 0, 0.8) transparent transparent transparent;
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