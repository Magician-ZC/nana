import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 状态
  const authToken = ref(localStorage.getItem('auth_token') || '')
  const isAuthenticated = ref(!!authToken.value)
  const userProfile = ref(JSON.parse(localStorage.getItem('user_profile')) || null)
  
  // 开发环境的默认测试令牌
  const DEFAULT_DEV_TOKEN = 'bdcfce39a84c47ac8e41b16d054f5999'
  
  // 登录状态计算属性
  const isLoggedIn = computed(() => !!authToken.value)
  
  // 初始化token - 应用启动时调用
  function initializeToken() {
    // 从localStorage获取token
    const storedToken = localStorage.getItem('auth_token')
    
    if (storedToken) {
      // 如果localStorage中有token，使用它
      authToken.value = storedToken
      isAuthenticated.value = true
      console.log('从localStorage初始化token成功')
      
      // 尝试获取用户档案
      const storedProfile = localStorage.getItem('user_profile')
      if (storedProfile) {
        try {
          userProfile.value = JSON.parse(storedProfile)
        } catch (e) {
          console.error('解析用户档案失败', e)
        }
      }
    } else {
      // 生产环境中清除token状态
      clearAuthToken()
    }
    
    return authToken.value
  }
  
  // 设置认证令牌
  function setAuthToken(token) {
    if (!token) return
    
    // 更新内存中的token
    authToken.value = token
    // 统一保存到localStorage
    localStorage.setItem('auth_token', token)
    // 更新认证状态
    isAuthenticated.value = true
    
    console.log('Token已设置并保存到localStorage')
    return token
  }
  
  // 获取认证令牌
  function getAuthToken() {
    // 如果内存中没有token但localStorage中有，更新内存
    if (!authToken.value) {
      const storedToken = localStorage.getItem('auth_token')
      if (storedToken) {
        authToken.value = storedToken
        isAuthenticated.value = true
      }
    }
    return authToken.value
  }
  
  // 清除认证令牌
  function clearAuthToken() {
    // 清除内存和localStorage中的token
    authToken.value = ''
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_profile')
    userProfile.value = null
    isAuthenticated.value = false
    console.log('Token和用户资料已清除')
  }
  
  // 设置用户资料
  function setUserProfile(profile) {
    userProfile.value = profile
    
    // 持久化存储
    if (profile) {
      localStorage.setItem('user_profile', JSON.stringify(profile))
    } else {
      localStorage.removeItem('user_profile')
    }
  }
  
  // 获取用户资料
  function getUserProfile() {
    return userProfile.value
  }
  
  // 检查是否认证
  function checkAuth() {
    // 确保认证状态与token一致
    isAuthenticated.value = !!getAuthToken()
    return isAuthenticated.value
  }
  
  // 设置默认开发测试令牌
  function setDevelopmentToken() {
    // 使用统一的开发测试token
    setAuthToken(DEFAULT_DEV_TOKEN)
    console.log('已设置开发测试令牌:', DEFAULT_DEV_TOKEN)
    return DEFAULT_DEV_TOKEN
  }
  
  // 用户登录函数
  async function login(username, password) {
    // 在实际应用中，这里应该调用后端API
    // 这里模拟一个登录过程
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        // 模拟API响应
        const mockResponse = {
          success: true,
          token: `user_${Math.random().toString(36).substring(2, 15)}`,
          user: {
            id: 1,
            username: username,
            name: username,
            email: `${username}@example.com`,
            avatar: null
          }
        }
        
        // 保存token和用户资料
        setAuthToken(mockResponse.token)
        setUserProfile(mockResponse.user)
        
        resolve(mockResponse)
      }, 800) // 模拟网络延迟
    })
  }
  
  // 用户注册函数
  async function register(userData) {
    // 在实际应用中，这里应该调用后端API
    // 这里模拟一个注册过程
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        // 模拟API响应
        const mockResponse = {
          success: true,
          token: `user_${Math.random().toString(36).substring(2, 15)}`,
          user: {
            id: Date.now(),
            username: userData.username,
            name: userData.username,
            email: userData.email,
            avatar: null
          }
        }
        
        // 保存token和用户资料
        setAuthToken(mockResponse.token)
        setUserProfile(mockResponse.user)
        
        resolve(mockResponse)
      }, 800) // 模拟网络延迟
    })
  }
  
  // 注销函数
  async function logout() {
    // 先获取当前用户信息，用于日志和清除特定用户的聊天记录
    const currentUser = userProfile.value?.username || userProfile.value?.name || 'guest'
    
    // 如果用户已登录，清除其前端本地聊天记录
    if (currentUser !== 'guest') {
      try {
        // 清除当前用户的localStorage聊天记录
        const key = `chat_history_${currentUser}`
        localStorage.removeItem(key)
        console.log(`已清除用户 ${currentUser} 的localStorage聊天记录`)
        
        // 导入API工具
        const apiModule = await import('../utils/api')
        
        // 结束引导模式
        try {
          const endGuidanceResponse = await fetch(apiModule.getApiUrl('end_guidance'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              session_id: "default",
              agent_type: null
            }),
          })
          
          const endGuidanceResult = await endGuidanceResponse.json()
          console.log('引导模式重置结果:', endGuidanceResult)
        } catch (error) {
          console.error('重置引导模式失败:', error)
        }
        
        // 注意：不再清除后端服务器中的聊天记录，以便在再次登录时恢复
        console.log('保留后端聊天记录，以便在再次登录时恢复')
        
        // 导入chat store，清空内存中的消息
        try {
          const { useChatStore } = await import('./chat')
          const chatStore = useChatStore()
          chatStore.clearMessages()
          console.log('已清空内存中的消息')
        } catch (e) {
          console.error('清空内存中消息失败', e)
        }
      } catch (e) {
        console.error('清除聊天记录失败', e)
      }
    }
    
    // 清除用户信息和令牌
    userProfile.value = null
    authToken.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_profile')
    isAuthenticated.value = false
    
    // 不再尝试控制路由，而是返回成功，让调用者（如Home.vue）处理路由跳转
    console.log('注销完成: 已清除用户信息和令牌')
    return true
  }
  
  return {
    // 状态
    authToken,
    isAuthenticated,
    userProfile,
    isLoggedIn,
    
    // 方法
    initializeToken,
    setAuthToken,
    getAuthToken,
    clearAuthToken,
    setUserProfile,
    getUserProfile,
    checkAuth,
    setDevelopmentToken,
    login,
    register,
    logout
  }
}) 