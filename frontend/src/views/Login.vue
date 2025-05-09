<template>
  <div class="min-h-screen flex flex-col bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 transition-colors duration-300">
    <div class="flex justify-between items-center p-4">
      <div class="text-2xl font-bold text-gray-800 dark:text-white">Nana</div>
      <button 
        @click="toggleDarkMode" 
        class="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-300"
      >
        <svg v-if="isDarkMode" xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-700" viewBox="0 0 20 20" fill="currentColor">
          <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
        </svg>
      </button>
    </div>
    
    <div class="flex-grow flex items-center justify-center p-6">
      <div class="w-full max-w-md">
        <div class="bg-white dark:bg-gray-800 shadow-xl rounded-xl p-8 transition-all duration-300 transform hover:scale-[1.01]">
          <div class="mb-8 text-center">
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">欢迎回来</h1>
            <p class="text-gray-600 dark:text-gray-400">登录您的账户继续使用</p>
          </div>
          
          <form @submit.prevent="handleLogin" class="space-y-6">
            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名</label>
              <input 
                id="username"
                v-model="username"
                type="text" 
                required
                class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-white transition-colors"
                :class="{ 'border-red-500 dark:border-red-500': errors.username }"
              />
              <p v-if="errors.username" class="mt-1 text-sm text-red-500">{{ errors.username }}</p>
            </div>
            
            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">密码</label>
              <input 
                id="password"
                v-model="password"
                type="password" 
                required
                class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-white transition-colors"
                :class="{ 'border-red-500 dark:border-red-500': errors.password }"
              />
              <p v-if="errors.password" class="mt-1 text-sm text-red-500">{{ errors.password }}</p>
            </div>
            
            <div class="flex items-center justify-between">
              <div class="flex items-center">
                <input 
                  id="remember"
                  v-model="rememberMe"
                  type="checkbox" 
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                />
                <label for="remember" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">记住我</label>
              </div>
              
              <div>
                <a href="#" class="text-sm font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300">忘记密码?</a>
              </div>
            </div>
            
            <div>
              <button 
                type="submit"
                class="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-300"
                :disabled="isLoading"
              >
                <template v-if="isLoading">
                  <div class="flex items-center">
                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    登录中...
                  </div>
                </template>
                <template v-else>登录</template>
              </button>
            </div>
          </form>
          
          <div class="mt-6 text-center">
            <p class="text-sm text-gray-600 dark:text-gray-400">
              还没有账户? 
              <router-link to="/register" class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300">立即注册</router-link>
            </p>
          </div>
        </div>
      </div>
    </div>
    
    <div class="py-4 text-center text-gray-500 dark:text-gray-400 text-sm">
      © 2023 Nana. All rights reserved.
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()

// 表单数据
const username = ref('')
const password = ref('')
const rememberMe = ref(false)
const errors = reactive({})
const isLoading = ref(false)
const isDarkMode = ref(false)

// 切换深色/浅色模式
const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value
  // 保存用户偏好到本地存储
  localStorage.setItem('darkMode', isDarkMode.value)
  updateTheme()
}

// 更新主题
const updateTheme = () => {
  if (isDarkMode.value) {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
}

// 检查系统偏好
const checkSystemPreference = () => {
  // 先检查用户之前的设置
  const savedPreference = localStorage.getItem('darkMode')
  
  if (savedPreference !== null) {
    // 如果有保存的设置，使用它
    isDarkMode.value = savedPreference === 'true'
  } else {
    // 否则使用系统偏好
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDarkMode.value = prefersDark
  }
  
  updateTheme()
}

// 处理登录
const handleLogin = async () => {
  // 清空错误信息
  Object.keys(errors).forEach(key => delete errors[key])
  
  // 简单表单验证
  if (username.value.trim() === '') {
    errors.username = '请输入用户名'
    return
  }
  
  if (password.value.trim() === '') {
    errors.password = '请输入密码'
    return
  }
  
  try {
    isLoading.value = true
    
    // 调用store中的login方法
    const response = await userStore.login(username.value, password.value)
    
    // 如果选择了记住我，可以在这里处理额外的持久化
    if (rememberMe.value) {
      localStorage.setItem('remember_user', username.value)
    } else {
      localStorage.removeItem('remember_user')
    }
    
    // 登录成功后加载聊天历史
    try {
      const { useChatStore } = await import('../stores/chat')
      const chatStore = useChatStore()
      
      // 确保聊天记录加载成功
      await chatStore.loadMessages()
        .then(loaded => {
          console.log('登录成功，聊天历史加载状态:', loaded ? '成功' : '无历史记录')
          
          // 如果没有历史记录或消息为空，显示欢迎消息
          if (!loaded || chatStore.messages.length === 0) {
            chatStore.showWelcomeMessage()
          }
        })
        .catch(error => {
          console.error('加载聊天历史失败:', error)
          // 出错时也显示欢迎消息
          chatStore.showWelcomeMessage()
        })
    } catch (error) {
      console.error('加载聊天历史失败:', error)
      // 发生异常时仍然重定向到首页
    }
    
    // 登录成功，跳转到首页
    router.push('/')
    
  } catch (error) {
    console.error('登录失败:', error)
    errors.general = '登录失败，请检查用户名和密码'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  // 检查并应用保存的主题设置
  checkSystemPreference()
  
  // 检查是否有保存的用户名
  const rememberedUser = localStorage.getItem('remember_user')
  if (rememberedUser) {
    username.value = rememberedUser
    rememberMe.value = true
  }
})
</script>

<style scoped>
/* 为表单元素添加平滑过渡效果 */
input, button {
  transition: all 0.3s ease;
}

/* 为卡片添加精致的阴影效果 */
.shadow-xl {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* 深色模式下的卡片阴影调整 */
.dark .shadow-xl {
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
}

/* 为整个页面添加平滑背景过渡 */
.min-h-screen {
  animation: fadeIn 0.5s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style> 