import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getApiUrl } from '../utils/api'

export const useUserStore = defineStore('user', () => {
  // 状态
  const authToken = ref(localStorage.getItem('auth_token') || '1f5046804d2c4e44b430adbf923c22a8')
  const sessionId = ref(localStorage.getItem('session_id') || '')
  const isAuthenticated = ref(!!sessionId.value)
  const userProfile = ref(JSON.parse(localStorage.getItem('user_profile')) || null)
  
  // 登录状态计算属性
  const isLoggedIn = computed(() => !!sessionId.value)
  const username = computed(() => userProfile.value?.username || '')
  const email = computed(() => userProfile.value?.email || '')
  
  // 初始化token - 应用启动时调用
  function initializeSession() {
    // 从localStorage获取session ID
    const storedSessionId = localStorage.getItem('session_id')
    
    if (storedSessionId) {
      // 如果localStorage中有session ID，使用它
      sessionId.value = storedSessionId
      isAuthenticated.value = true
      console.log('从localStorage初始化会话成功')
      
      // 尝试获取用户档案
      const storedProfile = localStorage.getItem('user_profile')
      if (storedProfile) {
        try {
          userProfile.value = JSON.parse(storedProfile)
        } catch (e) {
          console.error('解析用户档案失败', e)
        }
      }
      
      // 验证会话有效性
      verifySession(storedSessionId)
    } else {
      // 如果没有会话ID，清除状态
      clearAuthState()
    }
    
    return sessionId.value
  }
  
  // 设置认证会话
  function setSession(session) {
    if (!session || !session.session_id) return
    
    // 更新内存中的session ID
    sessionId.value = session.session_id
    // 统一保存到localStorage
    localStorage.setItem('session_id', session.session_id)
    // 更新认证状态
    isAuthenticated.value = true
    
    // 如果有用户信息，也保存
    if (session.user) {
      setUserProfile(session.user)
    }
    
    console.log('会话已设置并保存到localStorage')
    return session.session_id
  }
  
  // 设置用户资料
  function setUserProfile(user) {
    if (!user) return
    
    userProfile.value = user
    localStorage.setItem('user_profile', JSON.stringify(user))
    console.log('用户资料已保存到localStorage')
    return user
  }
  
  // 清除认证状态
  function clearAuthState() {
    sessionId.value = ''
    authToken.value = ''
    userProfile.value = null
    isAuthenticated.value = false
    
    localStorage.removeItem('session_id')
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_profile')
    
    console.log('认证状态已清除')
  }
  
  // 检查认证状态
  function checkAuth() {
    return isAuthenticated.value
  }
  
  // 验证会话有效性
  async function verifySession(sid = null) {
    const sessionToVerify = sid || sessionId.value
    
    if (!sessionToVerify) {
      console.log('没有会话ID，无法验证')
      return false
    }
    
    try {
      const response = await fetch(getApiUrl('verify_session'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionToVerify }),
      })
      
      const data = await response.json()
      
      if (data.success && data.user) {
        // 会话有效，更新用户资料
        setUserProfile(data.user)
        return true
      } else {
        // 会话无效，清除状态
        console.warn('会话验证失败:', data.message)
        clearAuthState()
        return false
      }
    } catch (error) {
      console.error('验证会话时出错:', error)
      return false
    }
  }
  
  // 用户登录函数
  async function login(username, password) {
    try {
      const response = await fetch(getApiUrl('login'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        // 保存会话ID和用户资料
        setSession(data)
        return data
      } else {
        throw new Error(data.message || '登录失败')
      }
    } catch (error) {
      console.error('登录失败:', error)
      throw error
    }
  }
  
  // 用户注册函数
  async function register(userData) {
    try {
      const response = await fetch(getApiUrl('register'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: userData.username,
          email: userData.email,
          password: userData.password,
          profile: {
            name: userData.username,
            avatar: null
          }
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        // 注册成功后自动登录
        return await login(userData.username, userData.password)
      } else {
        throw new Error(data.message || '注册失败')
      }
    } catch (error) {
      console.error('注册失败:', error)
      throw error
    }
  }
  
  // 用户登出函数
  async function logout() {
    try {
      if (sessionId.value) {
        // 调用后端登出接口
        await fetch(getApiUrl('logout'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ session_id: sessionId.value }),
        })
      }
    } catch (error) {
      console.error('登出API调用失败:', error)
    } finally {
      // 无论API调用是否成功，都清除本地状态
      clearAuthState()
    }
  }
  
  // 更新用户资料
  async function updateProfile(profileData) {
    if (!sessionId.value || !userProfile.value?.username) {
      throw new Error('用户未登录')
    }
    
    try {
      const response = await fetch(getApiUrl('update_profile'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId.value,
          username: userProfile.value.username,
          profile_data: profileData
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        // 更新本地资料
        const updatedProfile = {
          ...userProfile.value,
          ...data.profile
        }
        setUserProfile(updatedProfile)
        return data
      } else {
        throw new Error(data.message || '更新资料失败')
      }
    } catch (error) {
      console.error('更新资料失败:', error)
      throw error
    }
  }
  
  // 修改密码
  async function changePassword(currentPassword, newPassword) {
    if (!sessionId.value || !userProfile.value?.username) {
      throw new Error('用户未登录')
    }
    
    try {
      const response = await fetch(getApiUrl('change_password'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId.value,
          username: userProfile.value.username,
          current_password: currentPassword,
          new_password: newPassword
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        // 密码修改成功需要重新登录
        clearAuthState()
        return data
      } else {
        throw new Error(data.message || '修改密码失败')
      }
    } catch (error) {
      console.error('修改密码失败:', error)
      throw error
    }
  }
  
  // 忘记密码
  async function forgotPassword(email) {
    try {
      const response = await fetch(getApiUrl('forgot_password'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        return data
      } else {
        throw new Error(data.message || '重置密码请求失败')
      }
    } catch (error) {
      console.error('重置密码请求失败:', error)
      throw error
    }
  }
  
  // 重置密码
  async function resetPassword(resetToken, newPassword) {
    try {
      const response = await fetch(getApiUrl('reset_password'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          reset_token: resetToken,
          new_password: newPassword
        }),
      })
      
      const data = await response.json()
      
      if (data.success) {
        return data
      } else {
        throw new Error(data.message || '重置密码失败')
      }
    } catch (error) {
      console.error('重置密码失败:', error)
      throw error
    }
  }
  
  // 组件加载时自动初始化
  initializeSession()
  
  return {
    // 状态
    sessionId,
    authToken,
    userProfile,
    isAuthenticated,
    isLoggedIn,
    username,
    email,
    
    // 方法
    login,
    register,
    logout,
    checkAuth,
    verifySession,
    updateProfile,
    changePassword,
    forgotPassword,
    resetPassword,
    clearAuthState,
    initializeSession
  }
}) 