<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup>
// 基本组件设置
</script>

<style>
:root {
  --primary-color: #2c7c7e;
  --secondary-color: #4a6fa5;
  --background-color: #1a1a1a;
  --text-color: #ffffff;
  --accent-color: #f06292;
}

/* 页面过渡效果 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  background-color: var(--background-color);
  color: var(--text-color);
  overflow: hidden;
}

.app {
  position: relative;
  width: 100vw;
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(90deg, #d4c1ec 0%, #a6c1f4 100%);
}

.live2d-main {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  background-color: transparent;
}

/* 控制按钮容器 */
.controls-container {
  position: fixed;
  top: 20px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 100;
}

/* 设置按钮样式 */
.settings-button {
  margin-left: 10px;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb {
  background: rgba(80, 80, 80, 0.5);
  border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 100, 100, 0.7);
}

/* 移动端适配 */
@media (max-width: 768px) {
  .chat-panel {
    width: 100% !important;
    height: 100vh !important;
    max-height: none !important;
    right: 0 !important;
    bottom: 0 !important;
    border-radius: 0 !important;
  }
  
  .controls-container {
    position: fixed;
    top: 15px;
    right: 15px;
  }
}

/* 权限测试组件容器 */
.permission-test-container {
  position: fixed;
  top: 70px;
  left: 20px;
  z-index: 100;
  max-width: 80vw;
}

/* 深色模式切换按钮 */
.theme-toggle-btn {
  position: fixed;
  top: 20px;
  left: 20px;
  z-index: 100;
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

.theme-toggle-btn:hover {
  transform: scale(1.1);
  background-color: rgba(50, 50, 50, 0.8);
}

.dark .theme-toggle-btn {
  background-color: rgba(255, 255, 255, 0.2);
}

.dark .theme-toggle-btn:hover {
  background-color: rgba(255, 255, 255, 0.3);
}

/* Tailwind Dark Mode Support */
.dark {
  color-scheme: dark;
}

.dark body {
  background-color: #111827;
  color: #f9fafb;
}
</style> 