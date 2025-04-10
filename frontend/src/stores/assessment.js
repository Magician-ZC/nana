import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAssessmentStore = defineStore('assessment', () => {
  // 视频评估状态
  const videoAssessmentComplete = ref(false)
  const videoAssessmentData = ref(null)
  const videoProcessing = ref(false)
  const videoReportPolling = ref(false)
  const videoReportGenerated = ref(false)
  const videoReportId = ref(null)
  const videoReportUrl = ref(null)
  
  // 人脸检测状态
  const faceDetected = ref(false)
  const facePosition = ref('none') // 'none', 'center', 'left', 'right', 'top', 'bottom'
  
  // 情绪评估状态
  const emotionalAssessmentComplete = ref(false)
  const emotionalAssessmentData = ref(null)
  const emotionalProcessing = ref(false)
  
  // 心理评估状态
  const psychologicalAssessmentReady = ref(false)
  const psychologicalAssessmentData = ref(null)
  const psychologicalProcessing = ref(false)
  const dialogCount = ref(0)
  
  // 轮询相关
  let pollingInterval = null
  let reportCheckCount = 0
  const MAX_POLL_COUNT = 60 // 最大轮询次数(10分钟)
  
  // 设置方法
  function setVideoAssessmentComplete(status) {
    videoAssessmentComplete.value = status
  }
  
  function setVideoAssessmentData(data) {
    videoAssessmentData.value = data
  }
  
  function setVideoProcessing(status) {
    videoProcessing.value = status
  }
  
  function setFaceDetected(status) {
    faceDetected.value = status
  }
  
  function setFacePosition(position) {
    facePosition.value = position
  }
  
  function setEmotionalAssessmentComplete(status) {
    emotionalAssessmentComplete.value = status
  }
  
  function setEmotionalAssessmentData(data) {
    emotionalAssessmentData.value = data
  }
  
  function setEmotionalProcessing(status) {
    emotionalProcessing.value = status
  }
  
  function setPsychologicalAssessmentReady(status) {
    psychologicalAssessmentReady.value = status
  }
  
  function setPsychologicalAssessmentData(data) {
    psychologicalAssessmentData.value = data
  }
  
  function setPsychologicalProcessing(status) {
    psychologicalProcessing.value = status
  }
  
  function setDialogCount(count) {
    dialogCount.value = count
  }
  
  // 加密请求数据
  function encryptRequestData(data) {
    // 这里应该与实际的加密逻辑保持一致
    // 简化实现 - 实际项目中应使用与后端匹配的加密逻辑
    try {
      // 导入加密函数（实际项目中应当正确引入）
      const encrypt = (str) => {
        // 简单替代，实际项目中应使用正确的加密方法
        return btoa(encodeURIComponent(str));
      };
      
      const timestamp = Date.now();
      // 签名 - 通常使用MD5
      const sign = generateMD5(timestamp.toString());
      
      // 加密内容
      const encryptedContent = encrypt(JSON.stringify(data));
      
      return {
        sign: sign,
        content: encryptedContent,
        timestamp: timestamp
      };
    } catch (e) {
      console.error("加密请求数据失败:", e);
      return data;
    }
  }
  
  // 生成MD5哈希
  function generateMD5(str) {
    // 简化实现 - 真实应用应使用实际的MD5算法
    // 这里仅作为示例
    try {
      // 通常项目中会引入md5库
      // 这里使用简单的替代方案
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash; // Convert to 32bit integer
      }
      return hash.toString(16);
    } catch (e) {
      console.error("生成MD5失败:", e);
      return str;
    }
  }
  
  // 开始轮询检查视频评估报告
  function startVideoReportPolling() {
    // 如果已经在轮询中，不重复启动
    if (videoReportPolling.value) return
    
    console.log("开始轮询检查视频评估报告")
    
    videoReportPolling.value = true
    reportCheckCount = 0
    videoReportGenerated.value = false
    videoReportId.value = null
    
    // 清除之前的轮询
    if (pollingInterval) {
      clearInterval(pollingInterval)
    }
    
    // 立即执行一次检查
    checkVideoReport()
    
    // 设置轮询间隔 (每10秒检查一次)
    pollingInterval = setInterval(() => {
      checkVideoReport()
    }, 10000)
  }
  
  // 停止轮询
  function stopVideoReportPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
    videoReportPolling.value = false
    console.log("停止轮询检查视频评估报告")
  }
  
  // 检查视频评估报告
  async function checkVideoReport() {
    try {
      if (reportCheckCount >= MAX_POLL_COUNT) {
        console.log('已达到最大轮询次数，停止检查')
        stopVideoReportPolling()
        return
      }
      
      reportCheckCount++
      console.log(`第 ${reportCheckCount} 次检查视频评估报告`)
      
      // 准备请求数据
      const requestData = {
        pageNo: 1,
        pageSize: 10
      }
      
      // 获取用户认证令牌
      // 从localStorage或其他存储中获取
      const authToken = localStorage.getItem('auth_token') || localStorage.getItem('token') || ''
      
      if (!authToken) {
        console.warn('未找到授权令牌，使用测试令牌')
        // 使用默认测试令牌
        const testToken = '25c90b21074f42049d4c3d1772709574'
        localStorage.setItem('auth_token', testToken)
      }
      
      // 加密的请求体
      const encryptedData = encryptRequestData(requestData)
      
      console.log('发送请求到视频评估报告API:', encryptedData)
      
      // 发送请求 - 使用JSON格式
      const response = await fetch('http://192.168.3.143:30080/app-api/equipment/emotion/list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(encryptedData)
      })
      
      const result = await response.json()
      
      console.log('视频评估报告API响应:', result)
      
      // 检查响应状态
      if (result.code === 200 && result.data && result.data.list && result.data.list.length > 0) {
        // 获取最新的一条记录
        const latestReport = result.data.list[0]
        
        // 如果状态为1，表示已生成报告
        if (latestReport.status === 1) {
          console.log('视频评估报告已生成:', latestReport)
          videoReportGenerated.value = true
          videoReportId.value = latestReport.id
          
          // 停止轮询
          stopVideoReportPolling()
          
          // 自动下载报告
          await downloadVideoReport(latestReport.id)
        } else {
          console.log('视频评估报告尚未生成，状态:', latestReport.status)
        }
      } else {
        console.log('未找到视频评估报告或请求失败:', result)
      }
    } catch (error) {
      console.error('检查视频评估报告失败:', error)
    }
  }
  
  // 下载视频评估报告
  async function downloadVideoReport(reportId) {
    try {
      if (!reportId) {
        console.error('缺少报告ID，无法下载')
        return
      }
      
      // 获取用户认证令牌
      const authToken = localStorage.getItem('auth_token') || localStorage.getItem('token') || ''
      
      console.log(`开始下载视频评估报告, ID: ${reportId}`)
      
      // 发送下载请求
      const response = await fetch(`http://192.168.3.143:30080/app-api/equipment/emotion/download/back?id=${reportId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
      
      // 检查响应
      if (!response.ok) {
        throw new Error(`下载失败: ${response.status} ${response.statusText}`)
      }
      
      // 获取报告内容
      const reportBlob = await response.blob()
      
      // 保存报告到本地存储
      const reportFileName = `emotion_report_${reportId}.pdf`
      const reportUrl = URL.createObjectURL(reportBlob)
      videoReportUrl.value = reportUrl
      
      console.log('视频评估报告下载成功:', reportUrl)
      
      // 显示下载成功通知
      const notification = document.createElement('div')
      notification.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2'
      notification.innerHTML = `
        <i class="fa-solid fa-check-circle"></i>
        <div>
          <div class="font-medium">评估报告下载成功</div>
          <div class="text-sm opacity-90">正在分析报告内容...</div>
        </div>
      `
      document.body.appendChild(notification)
      
      // 3秒后移除通知
      setTimeout(() => {
        notification.classList.add('animate-fade-out')
        setTimeout(() => {
          notification.remove()
        }, 500)
      }, 3000)
      
      // 触发报告分析
      await analyzeVideoReport(reportBlob)
      
      return reportUrl
    } catch (error) {
      console.error('下载视频评估报告失败:', error)
      return null
    }
  }
  
  // 分析视频评估报告
  async function analyzeVideoReport(reportBlob) {
    try {
      // 创建FormData对象
      const formData = new FormData()
      formData.append('file', reportBlob, 'emotion_report.pdf')
      
      // 发送到后端分析接口
      const response = await fetch('http://localhost:8666/api/emotional_assessment', {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      
      if (result.success) {
        console.log('视频评估报告分析已开始:', result)
        setEmotionalProcessing(true)
        
        // 开始检查分析结果
        startCheckingAnalysisResult()
      } else {
        console.error('视频评估报告分析失败:', result.message)
      }
    } catch (error) {
      console.error('分析视频评估报告失败:', error)
    }
  }
  
  // 开始检查分析结果
  function startCheckingAnalysisResult() {
    // 每5秒检查一次分析结果
    const analysisCheckInterval = setInterval(async () => {
      try {
        const response = await fetch('http://localhost:8666/api/latest_assessment')
        const data = await response.json()
        
        if (data.success && data.has_assessment) {
          // 分析完成，加载结果
          await loadLatestEmotionalAssessment()
          
          // 清除检查间隔
          clearInterval(analysisCheckInterval)
          
          // 显示分析完成通知
          const notification = document.createElement('div')
          notification.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2'
          notification.innerHTML = `
            <i class="fa-solid fa-check-circle"></i>
            <div>
              <div class="font-medium">视频评估分析完成</div>
              <div class="text-sm opacity-90">点击情绪评估按钮查看详细分析</div>
            </div>
          `
          document.body.appendChild(notification)
          
          // 3秒后移除通知
          setTimeout(() => {
            notification.classList.add('animate-fade-out')
            setTimeout(() => {
              notification.remove()
            }, 500)
          }, 3000)
        }
      } catch (error) {
        console.error('检查分析结果失败:', error)
      }
    }, 5000)
    
    // 设置超时，最多等待2分钟
    setTimeout(() => {
      clearInterval(analysisCheckInterval)
      setEmotionalProcessing(false)
    }, 2 * 60 * 1000)
  }
  
  // 加载评估状态
  async function loadAssessmentStatus() {
    try {
      const response = await fetch('http://localhost:8666/api/assessment_status')
      const data = await response.json()
      
      if (data.success) {
        psychologicalAssessmentReady.value = data.assessment_ready
        dialogCount.value = data.dialog_count
        psychologicalProcessing.value = data.processing_assessment
      }
    } catch (error) {
      console.error('加载评估状态失败:', error)
    }
  }
  
  // 加载最新的情绪评估结果
  async function loadLatestEmotionalAssessment() {
    try {
      const response = await fetch('http://localhost:8666/api/latest_assessment')
      const data = await response.json()
      
      if (data.success && data.has_assessment) {
        emotionalAssessmentComplete.value = true
        
        // 加载详细结果
        const resultsResponse = await fetch('http://localhost:8666/api/assessment_results')
        const resultsData = await resultsResponse.json()
        
        if (resultsData.success) {
          emotionalAssessmentData.value = resultsData.results
        }
      } else {
        emotionalAssessmentComplete.value = false
        emotionalAssessmentData.value = null
      }
    } catch (error) {
      console.error('加载情绪评估结果失败:', error)
    }
  }
  
  // 重置状态
  function resetVideoAssessment() {
    videoAssessmentComplete.value = false
    videoAssessmentData.value = null
    videoProcessing.value = false
    faceDetected.value = false
    facePosition.value = 'none'
    stopVideoReportPolling()
    videoReportGenerated.value = false
    videoReportId.value = null
    videoReportUrl.value = null
  }
  
  // 初始化加载
  async function initialize() {
    await Promise.all([
      loadAssessmentStatus(),
      loadLatestEmotionalAssessment()
    ])
  }
  
  return {
    // 状态
    videoAssessmentComplete,
    videoAssessmentData,
    videoProcessing,
    videoReportPolling,
    videoReportGenerated,
    videoReportId,
    videoReportUrl,
    faceDetected,
    facePosition,
    emotionalAssessmentComplete,
    emotionalAssessmentData,
    emotionalProcessing,
    psychologicalAssessmentReady,
    psychologicalAssessmentData,
    psychologicalProcessing,
    dialogCount,
    
    // 方法
    setVideoAssessmentComplete,
    setVideoAssessmentData,
    setVideoProcessing,
    setFaceDetected,
    setFacePosition,
    setEmotionalAssessmentComplete,
    setEmotionalAssessmentData,
    setEmotionalProcessing,
    setPsychologicalAssessmentReady,
    setPsychologicalAssessmentData,
    setPsychologicalProcessing,
    setDialogCount,
    loadAssessmentStatus,
    loadLatestEmotionalAssessment,
    resetVideoAssessment,
    initialize,
    startVideoReportPolling,
    stopVideoReportPolling,
    downloadVideoReport
  }
})
