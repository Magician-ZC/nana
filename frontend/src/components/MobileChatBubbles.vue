<template>
  <div class="mobile-chat-bubbles" v-if="isMobile">
    <div class="bubbles-container">
      <div
        v-for="(message, index) in assistantMessages"
        :key="message.id"
        class="message-bubble ios-bubble"
        :class="[
          getMessageClass(message),
          { 'fade-in': true },
          { 'welcome-message': message.isWelcomeMessage }
        ]"
        :style="getBubbleStyle(message, index)"
      >
        <!-- 消息内容 -->
        <div class="message-content" :style="getContentStyle(message.id)">
          {{ renderMessageContent(message) }}
        </div>
      </div>
      
      <!-- 正在输入的提示 -->
      <div v-if="hasStreamingMessage" class="typing-indicator" :style="{ backgroundColor: colors[0] }">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useChatStore } from '../stores/chat';

export default {
  props: {
    // 接收父组件传递的移动设备状态
    isMobileDevice: {
      type: Boolean,
      default: true
    }
  },
  setup(props) {
    const chatStore = useChatStore();
    // 使用父组件传来的isMobile状态
    const isMobile = computed(() => props.isMobileDevice);
    
    // iOS风格的颜色数组
    const colors = [
      'rgba(0, 132, 255, 0.9)',  // iOS蓝色
      'rgba(76, 217, 100, 0.9)',  // iOS绿色
      'rgba(255, 45, 85, 0.9)',   // iOS粉色
      'rgba(88, 86, 214, 0.9)',   // iOS紫色
      'rgba(255, 149, 0, 0.9)',   // iOS橙色
      'rgba(90, 200, 250, 0.9)',  // iOS浅蓝色
      'rgba(52, 170, 220, 0.9)',  // iOS天蓝色
      'rgba(120, 120, 128, 0.9)'  // iOS灰色
    ];
    
    // 消息颜色映射
    const messageColors = ref({});
    
    // 获取消息颜色，确保每个消息ID都有固定的颜色
    const getMessageColor = (id) => {
      if (!messageColors.value[id]) {
        const colorIndex = Object.keys(messageColors.value).length % colors.length;
        messageColors.value[id] = colors[colorIndex];
      }
      return messageColors.value[id];
    };
    
    // 获取助手(agent)消息，确保欢迎消息保留在列表中
    const assistantMessages = computed(() => {
      // 获取所有助手消息
      const allMessages = chatStore.messages
        .filter(message => message.type === 'assistant')
        .map((message, index) => {
          // 确保每个消息都有唯一ID
          const id = message.id || `msg-${index}`;
          console.log(`消息[${index}]内容: "${message.content}"`); // 添加调试日志
          return {
            ...message,
            id
          };
        });
      
      console.log(`共有 ${allMessages.length} 条助手消息`);
      
      // 确保欢迎消息保留在顶部，不被顶掉
      let hasWelcomeMessage = false;
      let welcomeMessage = null;
      
      // 检查是否有欢迎消息
      for (const msg of allMessages) {
        if (msg.isWelcomeMessage) {
          hasWelcomeMessage = true;
          welcomeMessage = msg;
          break;
        }
      }
      
      return allMessages;
    });
    
    // 修改渲染消息内容的函数，提高对"正在思考中"的处理优先级
    const renderMessageContent = (message) => {
      // 获取消息内容
      const content = message.content;
      
      // 调试日志
      console.log(`移动端渲染消息(${message.id || 'unknown'})内容: "${content?.substring(0, 30) || '空'}"`);
      
      // 如果消息没有内容或内容为空（不应该发生，但以防万一）
      if (content === null || content === undefined || content.trim() === '') {
        console.log(`消息 ${message.id || 'unknown'} 内容为空，显示"正在思考中"`);
        return '正在思考中';
      }
      
      // 如果内容是"正在思考中"或"正在思考中..."，原样显示
      if (content === '正在思考中' || content === '正在思考中...') {
        return content;
      }
      
      // 检查内容是否以"正在思考中"开头但不仅是"正在思考中"
      // 这种情况不应该出现，但为了防止显示问题，我们需要处理
      if (content.startsWith('正在思考中') && content !== '正在思考中' && content !== '正在思考中...') {
        // 可能是后端发送的内容没有完全替换"正在思考中"，截取掉这部分
        console.log(`发现内容以"正在思考中"开头但不仅是"正在思考中"，可能需要处理:`, content);
        
        // 使用更强大的正则表达式，匹配"正在思考中"和任何后续的省略号
        const cleanedContent = content.replace(/^正在思考中\.{0,3}/, '').replace(/^\.{1,3}/, '');
        console.log(`清理后的内容: "${cleanedContent}"`);
        return cleanedContent || content; // 如果替换后为空，则返回原内容
      }
      
      // 检查内容是否仅以省略号开头，这可能是省略号单独残留的情况
      if (content.match(/^\.{1,3}[^\.]/)) {
        console.log(`发现内容以省略号开头，可能是残留，进行清理:`, content);
        const cleanedContent = content.replace(/^\.{1,3}/, '');
        console.log(`清理后的内容: "${cleanedContent}"`);
        return cleanedContent || content;
      }
      
      // 如果消息被标记为需要清除，但内容不为空，仍显示内容
      if (message.shouldClear && content && content.trim() !== '') {
        console.log(`消息 ${message.id || 'unknown'} 被标记为shouldClear但有内容，显示内容`);
        return content;
      }
      
      // 如果消息被标记为需要清除且内容为空，显示"正在思考中"
      if (message.shouldClear) {
        console.log(`消息 ${message.id || 'unknown'} 被标记为shouldClear且内容为空，显示"正在思考中"`);
        return '正在思考中';
      }
      
      // 返回消息内容
      return content;
    };
    
    // 为每个消息创建一个样式对象
    const getBubbleStyle = (message, index) => {
      const opacity = calculateOpacity(index);
      const backgroundColor = getMessageColor(message.id);
      
      // 欢迎消息使用特殊样式
      if (message.isWelcomeMessage) {
        return {
          opacity,
          backgroundColor,
          borderWidth: '2px',
          borderColor: 'rgba(255, 255, 255, 0.4)'
        };
      }
      
      // 添加最小高度和内边距确保气泡始终可见
      return {
        opacity,
        backgroundColor,
        padding: '10px 16px', // 确保气泡有足够的padding
        minHeight: '36px',    // 确保气泡有最小高度
        minWidth: '50px'      // 确保气泡有最小宽度
      };
    };
    
    // 修改getContentStyle函数，确保文本样式适合阅读
    const getContentStyle = (id) => {
      const backgroundColor = getMessageColor(id);
      // 为系统消息设置黑色文本，其他为白色
      const textColor = backgroundColor === 'rgba(230, 230, 235, 0.9)' ? '#000' : '#fff';
      
      return {
        color: textColor,
        minWidth: '20px', // 确保消息内容区域有最小宽度
        minHeight: '20px',  // 确保消息内容区域有最小高度
        fontSize: '16px', // 确保字体大小足够大
        lineHeight: '1.4',
        padding: '5px 0', // 添加一些内边距使文本更易读
        wordBreak: 'break-word',
        overflow: 'hidden'
      };
    };
    
    // 获取消息类名
    const getMessageClass = (message) => {
      return message.type === 'user' ? 'user-message' : 'system-message';
    };
    
    // 计算透明度 - 实现iOS风格的渐变效果
    const calculateOpacity = (index) => {
      const totalMessages = assistantMessages.value.length;
      if (totalMessages === 0) return 1;
      
      // 计算相对位置 (0到1之间，0表示最顶部，1表示最底部)
      const relativePosition = index / (totalMessages - 1);
      
      // 如果是欢迎消息，保持完全可见
      if (assistantMessages.value[index]?.isWelcomeMessage) {
        return 1;
      }
      
      // 如果消息不在上半部分区域，保持完全可见
      if (relativePosition >= 0.5) {
        return 1;
      }
      
      // 否则，渐变消失 (将0-0.5映射到0-1)
      // 使用更平滑的透明度变化
      const t = relativePosition / 0.5;
      // 使用自定义渐变函数，让顶部区域接近完全透明
      return Math.min(t * 1.5, 1); // 顶部更趋近于0透明度
    };
    
    // 获取正在流式传输的消息状态
    const hasStreamingMessage = computed(() => {
      return chatStore.messages.some(msg => msg.isStreaming === true);
    });
    
    // 注册音频事件
    const registerAudioEvents = () => {
      // 创建一个事件，通知组件音频已准备就绪
      const audioReadyEvent = new CustomEvent('audio-ready', {
        detail: { ready: true }
      });
      document.dispatchEvent(audioReadyEvent);
    };
    
    onMounted(() => {
      // 注册音频事件
      registerAudioEvents();
      
      // 打印初始消息状态
      console.log('初始化消息状态:', JSON.stringify(chatStore.messages.map(m => ({
        type: m.type,
        content: m.content,
        id: m.id
      }))));
      
      // 监听新消息，自动滚动到底部
      watch(() => assistantMessages.value.length, () => {
        scrollToBottom();
      });
    });
    
    // 添加自动滚动到底部的函数
    const scrollToBottom = () => {
      // 使用nextTick确保DOM已更新
      nextTick(() => {
        const container = document.querySelector('.bubbles-container');
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      });
    };
    
    return {
      isMobile,
      assistantMessages,
      hasStreamingMessage,
      getMessageClass,
      getMessageColor,
      getBubbleStyle,
      getContentStyle,
      calculateOpacity,
      colors,
      scrollToBottom,
      renderMessageContent
    };
  }
};
</script>

<style scoped>
.mobile-chat-bubbles {
  position: fixed;
  bottom: 90px;
  right: 0;
  width: 85%;
  max-width: 380px;
  height: 40vh;
  z-index: 100;
  overflow: hidden; /* 保留overflow:hidden，内部容器将可滚动 */
}

.bubbles-container {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  align-items: flex-end;
  overflow-y: auto; /* 改为可垂直滚动 */
  overflow-x: hidden;
  background: transparent;
  padding-right: 0;
  padding-bottom: 10px;
  /* 保留遮罩以实现渐变效果 */
  mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 50%, rgba(0, 0, 0, 0) 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0, 0, 0, 1) 50%, rgba(0, 0, 0, 0) 100%);
  /* 添加触摸滚动优化 */
  -webkit-overflow-scrolling: touch;
  touch-action: pan-y;
  pointer-events: auto; /* 允许触摸事件通过 */
}

/* 确保iOS风格滚动条 */
.bubbles-container::-webkit-scrollbar {
  width: 3px;
}

.bubbles-container::-webkit-scrollbar-track {
  background: transparent;
}

.bubbles-container::-webkit-scrollbar-thumb {
  background-color: rgba(255, 255, 255, 0.3);
  border-radius: 10px;
}

.message-bubble {
  position: relative;
  max-width: 90%;
  margin: 4px 5px;
  padding: 10px 16px !important; /* 增加padding并确保优先级 */
  border-radius: 18px;
  background-color: rgba(0, 132, 255, 0.9);
  word-wrap: break-word;
  transform-origin: right bottom;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  overflow: visible;
  animation: fadeIn 0.3s ease-out;
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: auto; /* 允许气泡响应触摸事件 */
  min-width: 50px !important; /* 确保气泡有最小宽度 */
  min-height: 36px !important; /* 确保气泡有最小高度 */
  display: flex;
  align-items: center;
}

.ios-bubble {
  border-radius: 18px;
  position: relative;
  min-width: 40px;
  max-width: 90%;
  align-self: flex-end;
  margin-bottom: 8px;
  margin-right: 10;
}

.ios-bubble.user-message {
  border-bottom-right-radius: 4px;
  margin-right: 0;
  border-top-right-radius: 4px;
}

.ios-bubble.system-message {
  border-top-left-radius: 18px;
  border-top-right-radius: 18px;
  border-bottom-left-radius: 18px;
  border-bottom-right-radius: 4px;
  margin-left: 0;
  align-self: flex-end;
  margin-right: 0;
}

.message-content {
  color: white;
  text-align: left;
  font-size: 16px;
  line-height: 1.4;
  word-break: break-word;
  white-space: pre-wrap; /* 保留空格和换行 */
  overflow-wrap: break-word; /* 确保长单词能换行 */
  min-height: 16px !important; /* 确保内容区域有最小高度 */
  width: 100%; /* 确保内容区占满气泡宽度 */
  display: block; /* 确保总是显示为块 */
}

.message-bubble.user-message {
  align-self: flex-end;
}

.message-bubble.system-message {
  align-self: flex-end;
  margin-right: 10px;
  background-color: rgba(230, 230, 235, 0.9);
}

.system-message .message-content {
  color: #000;
}

/* 欢迎消息样式 */
.message-bubble.welcome-message {
  border: 2px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
  z-index: 10; /* 确保欢迎消息显示在最上层 */
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  background-color: rgba(0, 132, 255, 0.9);
  border-radius: 18px;
  margin: 4px 0;
  position: relative;
  align-self: flex-end;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
  margin-right: 0;
  border-bottom-right-radius: 4px;
}

.typing-indicator span {
  height: 8px;
  width: 8px;
  margin: 0 2px;
  background-color: rgba(255, 255, 255, 0.8);
  border-radius: 50%;
  display: inline-block;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) {
  animation-delay: 0s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  50% {
    transform: translateY(-5px);
    opacity: 1;
  }
}

@keyframes fadeIn {
  0% {
    opacity: 0;
    transform: translateY(20px) scale(0.9);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes fadeOut {
  0% {
    opacity: 1;
    transform: translateY(0);
  }
  100% {
    opacity: 0;
    transform: translateY(-20px);
  }
}

.fade-in {
  animation: fadeIn 0.3s ease-out;
}

.fade-out {
  animation: fadeOut 0.3s ease-out forwards;
}
</style> 