<template>
  <div class="mobile-chat-bubbles" v-if="isMobile">
    <div class="bubbles-container">
      <div
        v-for="(message, index) in messagesWithId"
        :key="message.id"
        class="message-bubble"
        :class="[
          getMessageClass(message),
          { 'fade-in': true }
        ]"
        :style="{
          opacity: calculateOpacity(index)
        }"
      >
        <!-- 消息内容 -->
        <div class="message-content">
          {{ message.content || '无消息内容' }}
        </div>
        
        <!-- 元数据（角色名和时间） -->
        <div class="message-meta" v-if="message.timestamp || message.agentId">
          <span v-if="message.agentId" class="agent-name">{{ getAgentName(message.agentId) }}</span>
          <span v-if="message.timestamp" class="timestamp">{{ formatTime(message.timestamp) }}</span>
        </div>
      </div>
      
      <!-- 正在输入的提示 -->
      <div v-if="hasStreamingMessage" class="typing-indicator">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
    
    <!-- 渐变遮罩 -->
    <div class="gradient-overlay"></div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, onUnmounted, onBeforeUnmount } from 'vue';
import { useChatStore } from '../stores/chat';

const chatStore = useChatStore();

// 从聊天记录中筛选出最新的8条助手消息
const recentAssistantMessages = computed(() => {
  const assistantMessages = chatStore.messages
    .filter(message => message.type === 'assistant')
    .reverse()
    .slice(0, 8);
  
  console.log("助手消息筛选后数量:", assistantMessages.length);
  if (assistantMessages.length === 0) {
    console.log("没有找到助手消息!");
  } else {
    console.log("找到助手消息内容示例:", assistantMessages[0].content?.substring(0, 20));
  }
  
  return assistantMessages;
});

// 为消息添加唯一ID并存储
const messagesWithId = ref([]);

// 生成唯一ID的函数
const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

// 监听消息变化并更新messagesWithId
watch(() => chatStore.messages, (newMessages) => {
  try {
    console.log("消息变化监听触发，总消息数:", newMessages?.length || 0);
    
    // 获取助手消息
    const assistantMessages = recentAssistantMessages.value;
    console.log("当前助手消息数:", assistantMessages?.length || 0);
    
    // 更新消息ID列表
    const newMessagesWithId = [];
    
    // 处理每条消息
    assistantMessages.forEach(message => {
      if (!message) return; // 跳过无效消息
      
      try {
        // 检查消息是否已存在
        const existingMessage = messagesWithId.value.find(m => 
          m.content === message.content && 
          m.agentId === message.agentId
        );
        
        if (existingMessage) {
          // 如果消息已存在，保留它
          newMessagesWithId.push(existingMessage);
        } else {
          // 如果是新消息，添加一个新ID
          newMessagesWithId.push({
            ...message,
            id: generateId()
          });
        }
      } catch (messageError) {
        console.error("处理单条消息时出错:", messageError);
      }
    });
    
    // 更新ref
    messagesWithId.value = newMessagesWithId;
    console.log("更新后的messagesWithId长度:", messagesWithId.value.length);
  } catch (error) {
    console.error("监听消息变化时出错:", error);
  }
}, { immediate: true, deep: true });

// 监听当前正在流式传输的消息
watch(() => hasStreamingMessage.value, () => {
  // 强制更新以确保动画正常
  if (messagesWithId.value.length > 0) {
    const lastMessage = messagesWithId.value[messagesWithId.value.length - 1];
    if (lastMessage) {
      lastMessage.updatedAt = Date.now();
    }
  }
});

// 计算消息的透明度，越往上越透明
function calculateOpacity(index) {
  // 使用非线性渐变，使底部的几条消息都较为清晰，上面的迅速变透明
  const ratio = index / (recentAssistantMessages.value.length - 1);
  const opacity = Math.max(0.1, 1 - (ratio * ratio * 1.2));
  
  // 如果是最新消息并且正在流式传输，确保完全不透明
  if (index === 0 && hasStreamingMessage.value) {
    return 1;
  }
  
  return opacity;
}

// 根据消息的长度和内容调整样式
function getMessageStyle(message, index) {
  // 基础样式
  const style = {
    opacity: calculateOpacity(index),
    transform: `translateY(${-index * 10}px) scale(${0.98 + (index * 0.004)})`,
  };
  
  // 根据消息长度设置最大宽度
  if (message.content && message.content.length < 15) {
    style.maxWidth = '60%';
  } else if (message.content && message.content.length > 50) {
    style.maxWidth = '90%';
  }
  
  return style;
}

// 根据消息内容确定气泡类型
function getBubbleClass(message) {
  const content = message.content || '';
  
  // 基础类
  const classes = { 
    'typing': message.isStreaming,
  };
  
  // 根据内容添加情感类型
  if (content.includes('？') || content.includes('?')) {
    classes['question'] = true;
  } else if (content.includes('！') || content.includes('!')) {
    classes['excited'] = true;
  } else if (/[哈嘻😊😄😂🤣]/u.test(content)) {
    classes['happy'] = true;
  } else if (/[😔😟🙁☹️😢😭]/u.test(content)) {
    classes['sad'] = true;
  }
  
  return classes;
}

// 获取角色简称
function getShortAgentName(agentId) {
  if (!agentId) return '助手';
  
  // 根据角色ID返回简短名称
  const agentNames = {
    'nanaA': '猫娘',
    'nanaB': '姐姐',
    'nanaC': '少女'
  };
  
  // 对于自定义角色，获取名称前两个字符
  if (agentId.startsWith('custom_')) {
    const customAgent = chatStore.agents?.find(agent => agent.id === agentId);
    if (customAgent && customAgent.name) {
      return customAgent.name.substring(0, 2);
    }
    return '自定';
  }
  
  return agentNames[agentId] || '助手';
}

// 时间格式化为简短格式
function formatTime(timestamp) {
  if (!timestamp || !timestamp.time) return '';
  
  try {
    const date = new Date(timestamp.time);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  } catch (e) {
    return '';
  }
}

// 判断是否需要显示时间戳
function shouldShowTimestamp(message, index) {
  if (index === 0) return true;
  
  // 获取前一条消息
  const prevMessage = recentAssistantMessages.value[index + 1];
  if (!prevMessage) return true;
  
  // 如果角色ID不同，显示时间
  if (message.agentId !== prevMessage.agentId) return true;
  
  // 如果时间相差超过3分钟，显示时间
  if (message.timestamp && prevMessage.timestamp) {
    const curr = new Date(message.timestamp.time);
    const prev = new Date(prevMessage.timestamp.time);
    return (curr - prev) > 1000 * 60 * 3; // 3分钟
  }
  
  return false;
}

// 检测是否有正在流式传输的消息
const hasStreamingMessage = computed(() => {
  return chatStore.messages.some(message => message.isStreaming === true);
});

// 移动设备检测
const isMobile = ref(false);

const checkMobileDevice = () => {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) 
    || window.innerWidth <= 768;
  console.log("移动设备检测结果:", isMobile.value);
};

// 获取角色名称
function getAgentName(agentId) {
  if (!agentId) return '助手';
  
  const agents = {
    'zhinang': '智囊',
    'assistant': '助手',
    'default': '助手',
    // 可以添加更多角色
  };
  
  return agents[agentId] || agentId;
}

// 获取消息样式类
function getMessageClass(message) {
  if (!message || !message.content) return '';
  
  const content = message.content.toLowerCase();
  
  // 根据内容长度和情感特征返回不同的样式
  if (content.includes('?') || content.includes('？')) {
    return 'question-message';
  } else if (content.length < 15) {
    return 'short-message';
  } else if (content.length > 80) {
    return 'long-message';
  }
  
  return '';
}

// 在组件挂载时初始化
onMounted(() => {
  // 事件处理函数绑定到实例，以便于在卸载时正确移除
  checkMobileDevice.handler = checkMobileDevice;
  handleMessageSent.handler = handleMessageSent;
  
  // 检测移动设备
  checkMobileDevice();
  
  // 监听窗口大小变化
  window.addEventListener('resize', checkMobileDevice.handler);
  
  // 初始化可能需要的任何资源
  console.log("移动端气泡组件已挂载");
  
  try {
    // 将消息展示的初始化操作放在nextTick中执行，确保DOM已经更新
    nextTick(() => {
      try {
        // 强制更新一次消息列表
        const currentMessages = [...chatStore.messages];
        if (currentMessages.length > 0) {
          console.log("移动端气泡组件挂载后强制更新", currentMessages.length, "条消息");
          
          // 检查当前助手消息
          const assistantMessages = currentMessages.filter(msg => msg.type === 'assistant');
          console.log("移动端气泡组件：助手消息", assistantMessages.length, "条");
          
          // 检查消息内容，使用安全访问
          assistantMessages.forEach((msg, index) => {
            if (msg) {
              console.log(`助手消息${index+1}:`, msg.content?.substring(0, 30) || '无内容', 
                          "id:", msg.id || '无ID', 
                          "agentId:", msg.agentId || '无agentId');
            }
          });
          
          // 检查recentAssistantMessages计算属性
          console.log("recentAssistantMessages长度:", recentAssistantMessages.value.length);
          
          // 如果消息数组为空，强制添加一条消息用于测试
          if (messagesWithId.value.length === 0 && assistantMessages.length > 0) {
            messagesWithId.value = assistantMessages.map(msg => ({
              ...msg,
              id: generateId()
            }));
            console.log("强制添加消息到messagesWithId, 现在长度:", messagesWithId.value.length);
          }
        }
      } catch (tickError) {
        console.error("nextTick更新消息时出错:", tickError);
      }
    });
    
    // 监听消息发送事件
    document.addEventListener('message-sent', handleMessageSent.handler);
  } catch (mountError) {
    console.error("组件挂载过程中出错:", mountError);
  }
});

// 处理新消息事件
function handleMessageSent() {
  // 在消息发送后，确保更新视图
  nextTick(() => {
    console.log("收到消息发送事件，recentAssistantMessages长度：", recentAssistantMessages.value.length);
  });
}

// 组件卸载时清理事件监听
onUnmounted(() => {
  try {
    console.log("移动端气泡组件卸载");
    // 移除事件监听器，使用保存的引用以确保正确移除
    document.removeEventListener('message-sent', handleMessageSent.handler);
  } catch (error) {
    console.error("移除事件监听器时出错:", error);
  }
});

onBeforeUnmount(() => {
  try {
    // 清理事件监听器，使用保存的引用以确保正确移除
    window.removeEventListener('resize', checkMobileDevice.handler);
    console.log("移动端气泡组件卸载前清理完成");
  } catch (error) {
    console.error("清理窗口大小事件监听器时出错:", error);
  }
});
</script>

<style scoped>
.mobile-chat-bubbles {
  position: fixed;
  bottom: 80px; /* 位于输入框上方 */
  right: 10px;
  width: 85%;
  max-width: 320px;
  height: 70vh;
  z-index: 500; /* 进一步提高z-index确保在所有元素上方 */
  pointer-events: none; /* 防止干扰其他交互 */
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  overflow: hidden;
  background-color: rgba(0, 0, 0, 0.02); /* 添加微小背景色，用于调试 */
  border: 1px solid rgba(255, 0, 0, 0.1); /* 添加微小边框，用于调试 */
}

/* 在移动端上调整底部空间，为输入区域留出空间 */
@media (max-width: 768px) {
  .mobile-chat-bubbles {
    bottom: 80px; /* 确保在输入区域上方 */
    left: 10px; /* 添加左侧边距 */
    right: 10px;
    width: auto; /* 自动宽度 */
    max-width: none;
    height: calc(70vh - 60px); /* 减去输入区域高度 */
  }
}

.bubbles-container {
  position: fixed;
  bottom: 60px; /* 保留输入区域的空间 */
  left: 0;
  width: 100%;
  height: calc(70vh - 60px); /* 调整高度以便在移动设备上能更好地显示 */
  background-color: rgba(0, 0, 0, 0.02); /* 几乎不可见的背景 */
  display: flex;
  flex-direction: column-reverse;
  overflow: hidden;
  padding: 10px 15px;
  z-index: 500; /* 增加z-index确保能显示在其他元素之上 */
}

.message-bubble {
  max-width: 85%;
  margin-bottom: 12px;
  padding: 12px 16px;
  background-color: rgba(255, 255, 255, 0.95); /* 增加不透明度 */
  border-radius: 18px;
  font-size: 15px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  opacity: 1; /* 默认完全不透明 */
  transform-origin: left bottom;
  transition: all 0.3s ease;
  position: relative;
  z-index: 210;
  word-break: break-word;
  line-height: 1.5;
  color: #333;
  border-bottom-right-radius: 4px; /* 右下角为小圆角，模拟对话气泡 */
  animation: fadeIn 0.3s ease-out;
}

.message-bubble.typing {
  animation: pulse 1.5s infinite ease-in-out;
}

/* 打字指示器 */
.typing-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(255, 255, 255, 0.8);
  border-radius: 18px;
  padding: 8px 12px;
  width: fit-content;
  margin-bottom: 10px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
  animation: fadeIn 0.3s ease-out;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  margin: 0 2px;
  background-color: #3b82f6;
  border-radius: 50%;
  display: inline-block;
  opacity: 0.6;
}

.typing-indicator span:nth-child(1) {
  animation: bouncing 1s infinite 0.2s;
}
.typing-indicator span:nth-child(2) {
  animation: bouncing 1s infinite 0.4s;
}
.typing-indicator span:nth-child(3) {
  animation: bouncing 1s infinite 0.6s;
}

@keyframes bouncing {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

/* 气泡动画 */
.bubble-animation-enter-active {
  animation: bubbleIn 0.5s ease;
}

.bubble-animation-leave-active {
  animation: bubbleOut 0.5s ease forwards;
}

.bubble-animation-move {
  transition: transform 0.5s ease;
}

@keyframes bubbleIn {
  0% {
    transform: translateY(20px) scale(0.8);
    opacity: 0;
  }
  100% {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
}

@keyframes bubbleOut {
  0% {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
  100% {
    transform: translateY(-30px) scale(0.8);
    opacity: 0;
  }
}

/* 调整渐变遮罩，减小透明度 */
.mobile-chat-bubbles::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0.8) 0%,
    rgba(0, 0, 0, 0.6) 20%,
    rgba(0, 0, 0, 0) 40%
  );
  pointer-events: none;
  z-index: 3; /* 调整遮罩的z-index */
}

.message-bubble.question {
  background-color: rgba(220, 245, 255, 0.92);
  border-left: 3px solid #4a90e2;
}

.message-bubble.excited {
  background-color: rgba(255, 235, 220, 0.92);
  border-left: 3px solid #ff7043;
}

.message-bubble.happy {
  background-color: rgba(235, 255, 235, 0.92);
  border-left: 3px solid #4caf50;
}

.message-bubble.sad {
  background-color: rgba(240, 240, 250, 0.92);
  border-left: 3px solid #9c27b0;
}

/* 情绪动画 */
.message-bubble.excited {
  animation: excited 0.5s 1;
}

.message-bubble.happy {
  animation: happy 0.7s 1;
}

.message-bubble.sad {
  animation: sad 1s 1;
}

@keyframes excited {
  0%, 100% { transform: translateY(0); }
  25% { transform: translateY(-5px); }
  50% { transform: translateY(0); }
  75% { transform: translateY(-3px); }
}

@keyframes happy {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02) rotate(1deg); }
}

@keyframes sad {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(3px); }
}

.message-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #777;
  margin-top: 6px;
  padding-top: 4px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.agent-name {
  font-weight: 500;
}

.timestamp {
  opacity: 0.8;
}

.message-text {
  word-break: break-word;
}

/* 渐变遮罩覆盖底部，创造消失效果 */
.gradient-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 30%;
  background: linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.5) 70%,
    rgba(255, 255, 255, 0.9) 100%
  );
  pointer-events: none;
  z-index: 400; /* 确保在消息之上，但在其他UI元素之下 */
}

/* 消息类型样式 */
.short-message {
  font-size: 16px;
  font-weight: 500;
  background-color: rgba(255, 245, 230, 0.95);
  border-left: 3px solid #ffb74d;
}

.question-message {
  background-color: rgba(232, 245, 233, 0.95);
  border-left: 3px solid #81c784;
}

.long-message {
  font-size: 14px;
  line-height: 1.6;
  background-color: rgba(255, 255, 255, 0.97);
}

/* 消息进入动画 */
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style> 