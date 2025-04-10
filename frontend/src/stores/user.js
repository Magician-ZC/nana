import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  // 状态
  const authToken = ref(localStorage.getItem('auth_token') || '')
  const isAuthenticated = ref(!!authToken.value)
  const userProfile = ref(null)
  
  // 设置认证令牌
  function setAuthToken(token) {
    authToken.value = token
    localStorage.setItem('auth_token', token)
    isAuthenticated.value = !!token
  }
  
  // 获取认证令牌
  function getAuthToken() {
    return authToken.value
  }
  
  // 清除认证令牌
  function clearAuthToken() {
    authToken.value = ''
    localStorage.removeItem('auth_token')
    isAuthenticated.value = false
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
    return isAuthenticated.value
  }
  
  // 设置默认开发测试令牌
  function setDevelopmentToken() {
    // 使用与后端测试一致的token
    const devToken = '25c90b21074f42049d4c3d1772709574'
    setAuthToken(devToken)
    console.log('已设置开发测试令牌:', devToken)
    return devToken
  }
  
  return {
    // 状态
    authToken,
    isAuthenticated,
    userProfile,
    
    // 方法
    setAuthToken,
    getAuthToken,
    clearAuthToken,
    setUserProfile,
    getUserProfile,
    checkAuth,
    setDevelopmentToken
  }
}) 