import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 状态
  const authToken = ref(localStorage.getItem('auth_token') || '')
  const isAuthenticated = ref(!!authToken.value)
  const userProfile = ref(null)
  
  // 开发环境的默认测试令牌
  const DEFAULT_DEV_TOKEN = '5a4afbb8a10344978bae28f1ab2a0b73'
  
  // 初始化token - 应用启动时调用
  function initializeToken() {
    // 从localStorage获取token
    const storedToken = localStorage.getItem('auth_token')
    
    if (storedToken) {
      // 如果localStorage中有token，使用它
      authToken.value = storedToken
      isAuthenticated.value = true
      console.log('从localStorage初始化token成功')
    } else {
      // 在开发环境中，如果没有token，可以使用默认测试token
      if (process.env.NODE_ENV === 'development') {
        setDevelopmentToken()
      } else {
        // 生产环境中清除token状态
        clearAuthToken()
      }
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
    isAuthenticated.value = false
    console.log('Token已清除')
  }
  
  // 设置用户资料
  function setUserProfile(profile) {
    userProfile.value = profile
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
  
  return {
    // 状态
    authToken,
    isAuthenticated,
    userProfile,
    
    // 方法
    initializeToken,
    setAuthToken,
    getAuthToken,
    clearAuthToken,
    setUserProfile,
    getUserProfile,
    checkAuth,
    setDevelopmentToken
  }
}) 