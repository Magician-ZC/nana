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
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">创建账户</h1>
            <p class="text-gray-600 dark:text-gray-400">注册一个新账户开始使用</p>
          </div>
          
          <!-- 添加通用错误消息显示 -->
          <div v-if="errors.general" class="mb-4 p-3 bg-red-100 border-l-4 border-red-500 text-red-700 dark:bg-red-900 dark:text-red-200 rounded-md">
            {{ errors.general }}
          </div>
          
          <form @submit.prevent="handleRegister" class="space-y-5">
            <div>
              <label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">用户名</label>
              <input 
                id="username"
                v-model="username"
                type="text" 
                required
                class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-white text-gray-800 transition-colors"
                :class="{ 'border-red-500 dark:border-red-500': errors.username }"
              />
              <p v-if="errors.username" class="mt-1 text-sm text-red-500">{{ errors.username }}</p>
            </div>
            
            <div>
              <label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">电子邮箱</label>
              <input 
                id="email"
                v-model="email"
                type="email" 
                required
                class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-white text-gray-800 transition-colors"
                :class="{ 'border-red-500 dark:border-red-500': errors.email }"
              />
              <p v-if="errors.email" class="mt-1 text-sm text-red-500">{{ errors.email }}</p>
            </div>
            
            <div>
              <label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">密码</label>
              <input 
                id="password"
                v-model="password"
                type="password" 
                required
                class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-white text-gray-800 transition-colors"
                :class="{ 'border-red-500 dark:border-red-500': errors.password }"
              />
              <p v-if="errors.password" class="mt-1 text-sm text-red-500">{{ errors.password }}</p>
            </div>
            
            <div>
              <label for="confirmPassword" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">确认密码</label>
              <input 
                id="confirmPassword"
                v-model="confirmPassword"
                type="password" 
                required
                class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 dark:bg-gray-700 dark:text-white text-gray-800 transition-colors"
                :class="{ 'border-red-500 dark:border-red-500': errors.confirmPassword }"
              />
              <p v-if="errors.confirmPassword" class="mt-1 text-sm text-red-500">{{ errors.confirmPassword }}</p>
            </div>
            
            <div class="flex items-center">
              <input 
                id="agreement"
                v-model="agreement"
                type="checkbox" 
                required
                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700"
                :class="{ 'border-red-500': errors.agreement }"
              />
              <label for="agreement" class="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                我同意 <a href="#" class="text-blue-600 hover:text-blue-500 dark:text-blue-400">服务条款</a> 和 <a href="#" class="text-blue-600 hover:text-blue-500 dark:text-blue-400">隐私政策</a>
              </label>
            </div>
            <p v-if="errors.agreement" class="mt-1 text-sm text-red-500">{{ errors.agreement }}</p>
            
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
                    注册中...
                  </div>
                </template>
                <template v-else>注册</template>
              </button>
            </div>
          </form>
          
          <div class="mt-6 text-center">
            <p class="text-sm text-gray-600 dark:text-gray-400">
              已有账户? 
              <router-link to="/login" class="font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300">立即登录</router-link>
            </p>
          </div>
        </div>
      </div>
    </div>
    
    <div class="py-4 text-center text-gray-600 dark:text-gray-400 text-sm">
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
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const agreement = ref(false)
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

// 处理注册
const handleRegister = async () => {
  // 清空错误信息
  Object.keys(errors).forEach(key => delete errors[key])
  
  // 表单验证
  let hasError = false
  
  if (username.value.trim() === '') {
    errors.username = '请输入用户名'
    hasError = true
  } else if (username.value.length < 3) {
    errors.username = '用户名长度至少为3个字符'
    hasError = true
  }
  
  if (email.value.trim() === '') {
    errors.email = '请输入电子邮箱'
    hasError = true
  } else if (!/^[\w-]+(\.[\w-]+)*@[\w-]+(\.[\w-]+)+$/.test(email.value)) {
    errors.email = '请输入有效的电子邮箱'
    hasError = true
  }
  
  if (password.value.trim() === '') {
    errors.password = '请输入密码'
    hasError = true
  } else if (password.value.length < 6) {
    errors.password = '密码长度至少为6个字符'
    hasError = true
  }
  
  if (confirmPassword.value.trim() === '') {
    errors.confirmPassword = '请确认密码'
    hasError = true
  } else if (password.value !== confirmPassword.value) {
    errors.confirmPassword = '两次输入的密码不一致'
    hasError = true
  }
  
  if (!agreement.value) {
    errors.agreement = '请同意服务条款和隐私政策'
    hasError = true
  }
  
  if (hasError) return
  
  try {
    isLoading.value = true
    
    // 调用store中的register方法
    const userData = {
      username: username.value,
      email: email.value,
      password: password.value
    }
    
    const response = await userStore.register(userData)
    
    // 注册成功后初始化聊天历史
    try {
      const { useChatStore } = await import('../stores/chat')
      const chatStore = useChatStore()
      
      // 清空消息并向后端保存空聊天历史
      await chatStore.clearMessages()
      
      // 显示欢迎消息
      chatStore.showWelcomeMessage()
    } catch (error) {
      console.error('初始化聊天历史失败:', error)
    }
    
    // 注册成功，跳转到首页
    router.push('/')
    
  } catch (error) {
    console.error('注册失败:', error)
    // 设置通用错误消息
    errors.general = error.message || '注册失败，请检查输入信息或稍后重试'
  } finally {
    isLoading.value = false
  }
}

onMounted(() => {
  // 检查并应用保存的主题设置
  checkSystemPreference()
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