import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useUserStore } from './user'
import _ from 'lodash'
import { getApiUrl } from '../utils/api'

export const useAssessmentStore = defineStore('assessment', () => {
  // Get userStore instance
  const userStore = useUserStore()
  
  // 视频评估状态
  const videoAssessmentComplete = ref(false)
  const videoAssessmentData = ref(null)
  const videoProcessing = ref(false)
  const videoReportPolling = ref(false)
  const videoReportGenerated = ref(false)
  const videoReportId = ref(null)
  const videoReportUrl = ref(null)
  
  // 视频上传相关状态
  const videoUploadEtag = ref('') // 保留但不使用，仅为兼容性
  const reportId = ref(null) // 添加reportId状态变量
  const uploadCallbackComplete = ref(false) // 上传回调完成状态
  const assessmentComplete = ref(false) // 评估完成状态
  const statusPollingActive = ref(false)
  const statusPollingStarted = ref(false)
  const statusPollingInterval = ref(null)
  const reportDownloaded = ref(false) // 报告是否已下载
  
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
  
  // 添加防抖函数和缓存控制
  let lastAssessmentStatusRequestTime = 0;
  let lastEmotionalAssessmentRequestTime = 0;
  const MIN_REQUEST_INTERVAL = 2000; // 最少2秒之间的请求间隔
  
  // 添加失败计数器变量
  let uploadCallbackFailCount = 0;
  const MAX_UPLOAD_CALLBACK_FAILS = 10; // 最大失败次数，超过则停止轮询
  
  // 新增：记录上次API调用时间
  const lastApiCallTime = ref(0)
  const API_CALL_THROTTLE = 3000  // 新增：API调用最小间隔时间(毫秒)
  
  // 新增全局轮询控制变量
  let masterPollingActive = false;
  let masterPollingInterval = null;
  const MASTER_POLLING_INTERVAL = 10000; // 10秒轮询一次
  
  // 新增API调用间隔控制
  const lastApiCallTimes = {
    videoStatus: 0,
    videoReport: 0,
    emotionalAssessment: 0
  };
  const API_CALL_INTERVALS = {
    videoStatus: 15000,
    videoReport: 20000, 
    emotionalAssessment: 30000
  };
  
  // 检查是否可以发起新的请求
  function canMakeRequest(lastRequestTime) {
    const now = Date.now();
    return (now - lastRequestTime) > MIN_REQUEST_INTERVAL;
  }
  
  // 节流函数：确保同一API在指定时间内只调用一次
  function canCallApi(key) {
    const now = Date.now()
    const lastCall = lastApiCallTime.value[key] || 0
    
    if (now - lastCall > API_CALL_THROTTLE) {
      lastApiCallTime.value[key] = now
      return true
    }
    
    console.log(`API调用被节流: ${key}, 间隔: ${now - lastCall}ms, 需要: ${API_CALL_THROTTLE}ms`)
    return false
  }
  
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
  
  function setVideoUploadEtag(etag) {
    // 保留方法但不再使用
    console.log('[DEBUG] setVideoUploadEtag方法已弃用，不再使用etag')
  }
  
  function setReportId(id) {
    reportId.value = id
    // 立即保存到localStorage
    saveVideoUploadState()
  }
  
  function setUploadCallbackComplete(status) {
    uploadCallbackComplete.value = status
    // 立即保存到localStorage
    saveVideoUploadState()
  }
  
  function setAssessmentComplete(status) {
    assessmentComplete.value = status
    // 立即保存到localStorage
    saveVideoUploadState()
  }
  
  function setReportDownloaded(status) {
    reportDownloaded.value = status
    // 立即保存到localStorage
    saveVideoUploadState()
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
  
  // 启动主轮询机制 - 改进
  function startMasterPolling() {
    if (masterPollingActive) {
      console.log('[Assessment Store] 主轮询已经在运行中')
      return
    }
    
    console.log('[Assessment Store] 启动主轮询机制')
    masterPollingActive = true
    
    // 首次立即执行检查
    runMasterPollingChecks()
    
    // 设置定期轮询
    masterPollingInterval = setInterval(() => {
      runMasterPollingChecks()
    }, MASTER_POLLING_INTERVAL)
  }
  
  // 主轮询检查函数 - 新增
  async function runMasterPollingChecks() {
    console.log('[Assessment Store] 执行主轮询检查')
    
    const now = Date.now()
    
    // 如果全部状态都已完成且报告已下载且已解析情绪评估，则停止轮询
    if (uploadCallbackComplete.value && assessmentComplete.value && 
        reportDownloaded.value && emotionalAssessmentComplete.value) {
      console.log('[Assessment Store] 所有状态已完成且报告已下载和解析，停止主轮询')
      stopMasterPolling()
      return
    }
    
    try {
      // 检查视频上传状态 - 限制API调用频率，移除etag依赖
      if ((!uploadCallbackComplete.value || !assessmentComplete.value) && 
          (now - lastApiCallTimes.videoStatus >= API_CALL_INTERVALS.videoStatus)) {
        lastApiCallTimes.videoStatus = now
        await checkVideoStatus(false)
      }
      
      // 检查视频报告 - 限制API调用频率，移除etag依赖
      if (assessmentComplete.value && 
          !reportDownloaded.value && 
          (now - lastApiCallTimes.videoReport >= API_CALL_INTERVALS.videoReport)) {
        lastApiCallTimes.videoReport = now
        await checkVideoReport()
      }
      
      // 检查情绪评估状态 - 限制API调用频率，并且只在需要时调用
      if (!emotionalAssessmentComplete.value && reportDownloaded.value && 
          (now - lastApiCallTimes.emotionalAssessment >= API_CALL_INTERVALS.emotionalAssessment)) {
        lastApiCallTimes.emotionalAssessment = now
        await loadLatestEmotionalAssessment()
      }
    } catch (error) {
      console.error('[Assessment Store] 主轮询检查失败:', error)
    }
  }
  
  // 停止主轮询 - 改进
  function stopMasterPolling() {
    if (masterPollingInterval) {
      console.log('[Assessment Store] 停止主轮询')
      clearInterval(masterPollingInterval)
      masterPollingInterval = null
      masterPollingActive = false
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
      // 从userStore获取
      const authToken = userStore.getAuthToken() || ''
      
      if (!authToken) {
        console.warn('未找到授权令牌，使用测试令牌')
        // 使用默认测试令牌
        const testToken = userStore.setDevelopmentToken()
      }
      
      // 加密的请求体
      const encryptedData = encryptRequestData(requestData)
      
      console.log('发送请求到视频评估报告API:', encryptedData)
      
      // 发送请求 - 使用JSON格式
      const response = await fetch(getApiUrl('equipment/emotion/list'), {
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
  
  // 分析视频评估报告
  async function analyzeVideoReport(reportBlob) {
    try {
      console.log('[DEBUG] 开始分析视频评估报告');
      
      // 读取报告内容
      const text = await reportBlob.text();
      console.log('[DEBUG] 报告内容长度:', text.length);
      
      // 提取JSON部分
      const jsonMatch = text.match(/```json\n([\s\S]*?)\n```/);
      if (jsonMatch && jsonMatch[1]) {
        const jsonContent = jsonMatch[1].trim();
        console.log('[DEBUG] 找到JSON内容:', jsonContent);
        
        try {
          const assessmentData = JSON.parse(jsonContent);
          
          // 更新视频评估数据
          videoAssessmentData.value = assessmentData;
          videoAssessmentComplete.value = true;
          
          console.log('[DEBUG] 视频评估报告解析成功:', assessmentData);
          
          return assessmentData;
        } catch (jsonError) {
          console.error('[DEBUG] 解析JSON失败:', jsonError);
          return null;
        }
      } else {
        console.error('[DEBUG] 未在报告中找到JSON数据');
        return null;
      }
    } catch (error) {
      console.error('[DEBUG] 分析视频评估报告失败:', error);
      return null;
    }
  }
  
  // 下载视频评估报告 - 确保状态一致性
  async function downloadVideoReport(reportId) {
    try {
      console.log(`[Assessment Store] 开始下载视频评估报告: ID=${reportId}`)
      
      // 检查参数
      if (!reportId) {
        console.error('[Assessment Store] 缺少报告ID，无法下载')
        return null
      }
      
      // 如果报告已下载，则直接返回URL
      if (reportDownloaded.value && videoReportUrl.value) {
        console.log('[Assessment Store] 报告已下载，直接返回URL:', videoReportUrl.value)
        return videoReportUrl.value
      }
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      // 发起下载请求
      const response = await fetch(getApiUrl(`report/${reportId}`), {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
      
      if (!response.ok) {
        console.error(`[Assessment Store] 报告下载失败: ${response.status} ${response.statusText}`)
        return null
      }
      
      // 获取报告文件
      const reportBlob = await response.blob()
      
      // 创建临时URL
      const reportUrl = URL.createObjectURL(reportBlob)
      
      // 更新报告URL和状态
      videoReportUrl.value = reportUrl
      uploadCallbackComplete.value = true
      assessmentComplete.value = true
      reportDownloaded.value = true
      
      console.log('[Assessment Store] 视频评估报告下载成功:', reportUrl)
      
      // 更新报告下载状态
      await updateReportDownloadStatus(true)
      
      // 保存状态到localStorage - 确保状态持久化
      saveVideoUploadState()
      
      // 调用情绪评估接口 - 发送报告进行评估
      console.log('[Assessment Store] 调用情绪评估API进行报告分析')
      
      // 创建 FormData 对象
      const formData = new FormData()
      formData.append('file', reportBlob, `report_${reportId}.pdf`)
      
      // 调用情绪评估接口
      try {
        console.log('[Assessment Store] 发送POST请求到 /api/emotional_assessment')
        const emotionalResponse = await fetch(getApiUrl('emotional_assessment'), {
          method: 'POST',
          body: formData
        })
        
        if (!emotionalResponse.ok) {
          console.error(`[Assessment Store] 情绪评估API调用失败: ${emotionalResponse.status} ${emotionalResponse.statusText}`)
          const errorText = await emotionalResponse.text()
          console.error('[Assessment Store] 错误详情:', errorText)
        } else {
          const emotionalResult = await emotionalResponse.json()
          console.log('[Assessment Store] 情绪评估API调用成功:', emotionalResult)
          
          if (emotionalResult.success) {
            console.log('[Assessment Store] 情绪评估已在后台处理中')
            emotionalProcessing.value = true
            saveVideoUploadState()
          }
        }
      } catch (emotionalError) {
        console.error('[Assessment Store] 调用情绪评估API出错:', emotionalError)
      }
      
      // 停止所有轮询
      stopStatusPolling()
      stopMasterPolling()
      
      return reportUrl
    } catch (error) {
      console.error('[Assessment Store] 下载或分析报告失败:', error)
      return null
    }
  }
  
  // 加载最新的情绪评估结果 - 防抖和缓存优化版
  async function loadLatestEmotionalAssessment() {
    try {
      // 检查是否应该发起请求（防抖）
      const now = Date.now();
      if (now - lastEmotionalAssessmentRequestTime < MIN_REQUEST_INTERVAL) {
        console.log('[DEBUG] 跳过情绪评估数据请求 - 间隔太短');
        return false;
      }
      
      lastEmotionalAssessmentRequestTime = now;
      console.log('[DEBUG] 加载最新情绪评估数据');
      
      // 先检查localStorage中是否有最近的评估数据
      const savedState = localStorage.getItem('video_upload_state');
      if (savedState) {
        try {
          const state = JSON.parse(savedState);
          const timestamp = state.timestamp || 0;
          
          // 如果状态是最近10分钟内保存的，且已经完成了情绪评估，则不重新获取
          if ((now - timestamp < 10 * 60 * 1000) && 
              emotionalAssessmentComplete.value && 
              emotionalAssessmentData.value) {
            console.log('[DEBUG] 使用缓存的情绪评估数据，不重新获取');
            return true;
          }
        } catch (e) {
          console.error('[DEBUG] 解析缓存状态失败:', e);
        }
      }
      
      // 发起网络请求获取最新数据
      const response = await fetch(getApiUrl('assessment_results'));
      const data = await response.json();
      
      if (!data.success) {
        console.log('[DEBUG] 加载评估数据失败');
        return false;
      }
      
      if (!data.has_assessment) {
        console.log('[DEBUG] 没有找到有效的评估数据');
        return false;
      }
      
      // 更新状态
      emotionalAssessmentComplete.value = true;
      emotionalAssessmentData.value = data.assessment;
      emotionalProcessing.value = false;
      
      console.log('[DEBUG] 成功加载评估数据，缓存到localStorage');
      
      // 同步更新视频评估数据，确保两者一致
      if (!videoAssessmentComplete.value && data.assessment) {
        videoAssessmentData.value = data.assessment;
        videoAssessmentComplete.value = true;
        console.log('[DEBUG] 同步更新视频评估数据');
      }
      
      // 将数据保存到localStorage
      saveVideoUploadState();
      
      return true;
    } catch (error) {
      console.error('[DEBUG] 加载评估数据时发生错误:', error);
      return false;
    }
  }
  
  // 开始检查分析结果
  function startCheckingAnalysisResult() {
    // 每5秒检查一次分析结果
    const analysisCheckInterval = setInterval(async () => {
      try {
        const response = await fetch(getApiUrl('assessment_results'))
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
  
  // 加载评估状态 - 添加防抖和缓存机制
  async function loadAssessmentStatus() {
    // 检查是否应该执行请求
    if (!canMakeRequest(lastAssessmentStatusRequestTime)) {
      console.log('跳过评估状态请求 - 间隔太短');
      return;
    }
    
    try {
      lastAssessmentStatusRequestTime = Date.now();
      const response = await fetch(getApiUrl('assessment_status'));
      const data = await response.json();
      
      if (data.success) {
        psychologicalAssessmentReady.value = data.assessment_ready;
        dialogCount.value = data.dialog_count;
        psychologicalProcessing.value = data.processing_assessment;
      }
    } catch (error) {
      console.error('加载评估状态失败:', error);
    }
  }
  
  // 视频状态轮询函数
  // 使用防抖函数来减少API调用次数
  const debouncedCheckVideoStatus = _.debounce(async function(shouldStartPolling) {
    try {
      console.log(`[防抖后]检查视频状态: 启动轮询=${shouldStartPolling}`)
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      // 调用统一API
      const response = await fetch(getApiUrl('video/status'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          auth_token: authToken,
          start_polling: shouldStartPolling
        })
      })
      
      // 更新最后API调用时间
      if (!lastApiCallTime.value) {
        lastApiCallTime.value = {}
      }
      lastApiCallTime.value[`videoStatus`] = Date.now()
      
      const result = await response.json()
      
      if (result.success) {
        const { report_id, upload_callback_status, assessment_status, polling_started, report_downloaded, status } = result.data
        
        console.log(`视频状态: 报告ID=${report_id}, 状态=${status}, 上传回调=${upload_callback_status}, 评估=${assessment_status}, 轮询=${polling_started || false}, 报告下载=${report_downloaded || false}`)
        
        // 更新报告ID
        if (report_id) {
          reportId.value = report_id
        }
        
        // 更新状态
        uploadCallbackComplete.value = upload_callback_status
        assessmentComplete.value = assessment_status
        
        // 更新报告下载状态
        if (report_downloaded !== undefined) {
          reportDownloaded.value = report_downloaded
        }
        
        if (polling_started) {
          statusPollingActive.value = true
          console.log('后端轮询已启动')
        }
        
        // 保存到localStorage
        saveVideoUploadState()
        
        // 上传回调状态为false的处理
        if (!upload_callback_status) {
          console.warn('上传回调未成功，停止轮询')
          stopStatusPolling()
          stopMasterPolling()
          // 显示上传失败通知
          showUploadFailureNotification()
          return
        }
        
        // 更新视频评估完成状态
        if (assessment_status) {
          setVideoAssessmentComplete(true)
          setVideoProcessing(false)
          
          // 如果评估完成且报告未下载，尝试下载报告
          if (upload_callback_status && assessment_status && !reportDownloaded.value) {
            console.log('检测到评估已完成但报告未下载，将尝试下载报告')
            await attemptReportDownload()
          }
          // 如果全部完成，停止轮询
          else if (upload_callback_status && assessment_status && reportDownloaded.value) {
            console.log('检测到评估已完成且报告已下载，停止轮询')
            stopStatusPolling()
            stopMasterPolling()
          }
        }
      } else {
        console.warn('获取视频状态失败:', result.message)
        // API请求失败也增加失败计数
        uploadCallbackFailCount++
        if (uploadCallbackFailCount >= MAX_UPLOAD_CALLBACK_FAILS) {
          console.error('API请求持续失败，停止轮询')
          stopStatusPolling()
          stopMasterPolling()
          showUploadFailureNotification()
        }
      }
    } catch (error) {
      console.error('检查视频状态出错:', error)
      // 异常也计入失败次数
      uploadCallbackFailCount++
      if (uploadCallbackFailCount >= MAX_UPLOAD_CALLBACK_FAILS) {
        console.error('API请求异常，停止轮询')
        stopStatusPolling()
        stopMasterPolling()
        showUploadFailureNotification()
      }
    }
  }, 1000);  // 设置防抖时间为1秒
  
  // 包装检查函数，对外暴露
  function checkVideoStatus(shouldStartPolling = false) {
    console.log(`[原始调用]检查视频状态: 启动轮询=${shouldStartPolling}`)
    
    // 立即启动轮询的情况下不去抖动
    if (shouldStartPolling) {
      debouncedCheckVideoStatus(true);
      return;
    }
    
    // 常规检查状态时使用防抖
    debouncedCheckVideoStatus(false);
  }
  
  // 开始轮询检查视频上传和评估状态
  function startStatusPolling() {
    // 避免重复启动轮询
    if (statusPollingActive.value) {
      console.log('状态轮询已经在运行中')
      return
    }
    
    try {
      console.log(`启动状态轮询`)
      
      // 初始化API调用时间记录
      if (!lastApiCallTime.value) {
        lastApiCallTime.value = {}
      }
      
      // 设置轮询活跃状态
      statusPollingActive.value = true
      
      // 创建轮询间隔
      const statusInterval = setInterval(() => {
        // 第一次轮询需要启动后端轮询
        const shouldStartPolling = !statusPollingStarted.value
        
        // 使用节流函数控制API调用频率
        if (canCallApi(`checkVideoStatus`)) {
          checkVideoStatus(shouldStartPolling)
          // 标记已尝试启动后端轮询
          statusPollingStarted.value = true
        }
      }, 5000) // 每5秒检查一次
      
      // 保存轮询间隔引用
      statusPollingInterval.value = statusInterval
      
      // 立即执行一次检查并启动后端轮询
      checkVideoStatus(true)
      
      // 同时启动主轮询
      startMasterPolling()
    } catch (error) {
      console.error('启动状态轮询失败:', error)
      statusPollingActive.value = false
    }
  }
  
  // 停止状态轮询
  function stopStatusPolling() {
    if (statusPollingInterval.value) {
      clearInterval(statusPollingInterval.value)
      statusPollingInterval.value = null
      statusPollingActive.value = false
      statusPollingStarted.value = false
      console.log('状态轮询已停止')
    }
  }
  
  // 保存视频上传状态到localStorage
  function saveVideoUploadState() {
    try {
      const uploadState = {
        // 不再使用etag，仅保留兼容性字段但设为空字符串
        etag: '',
        reportId: reportId.value,
        uploadCallbackComplete: uploadCallbackComplete.value,
        assessmentComplete: assessmentComplete.value,
        reportDownloaded: reportDownloaded.value,
        timestamp: Date.now()
      }
      
      // 记录日志，特别是报告下载状态
      console.log(`[DEBUG] 保存视频上传状态: reportId=${uploadState.reportId}, 上传回调=${uploadState.uploadCallbackComplete}, 评估=${uploadState.assessmentComplete}, 报告下载=${uploadState.reportDownloaded}`);
      
      // 保存前检查localStorage访问权限
      try {
        console.log('[DEBUG] 保存前localStorage测试...');
        const testKey = "__test_localStorage";
        localStorage.setItem(testKey, "test");
        localStorage.removeItem(testKey);
        console.log("[DEBUG] localStorage访问测试成功");
      } catch (storageError) {
        console.error("[DEBUG] localStorage访问测试失败:", storageError);
        return false;
      }
      
      // 保存前检查当前localStorage内容
      console.log('[DEBUG] 保存前的localStorage内容:', localStorage.getItem('video_upload_state'));
      
      // 保存状态 - 使用同步调用确保立即写入
      localStorage.setItem('video_upload_state', JSON.stringify(uploadState));
      
      // 提高可靠性：尝试读取保存的状态，验证是否成功保存
      const verifyState = localStorage.getItem('video_upload_state');
      if (!verifyState) {
        console.error('[DEBUG] 存储验证失败，无法读取保存的值');
        // 再次尝试保存
        localStorage.setItem('video_upload_state', JSON.stringify(uploadState));
      }
      
      // 验证保存结果 - 添加延迟保证写入完成
      setTimeout(() => {
        const savedItem = localStorage.getItem('video_upload_state');
        if (savedItem) {
          const parsedItem = JSON.parse(savedItem);
          console.log("[DEBUG] 成功保存状态到localStorage:", parsedItem);
          console.log(`[DEBUG] 验证存储值: reportId=${parsedItem.reportId}, 回调=${parsedItem.uploadCallbackComplete}, 评估=${parsedItem.assessmentComplete}`);
        } else {
          console.error("[DEBUG] localStorage保存失败: 无法读取保存的状态");
          // 最后再尝试一次
          localStorage.setItem('video_upload_state', JSON.stringify(uploadState));
        }
      }, 50);
      
      return true;
    } catch (error) {
      console.error('[DEBUG] 保存视频上传状态失败:', error);
      return false;
    }
  }
  
  // 从localStorage加载视频上传状态
  function loadVideoUploadState() {
    try {
      console.log('[DEBUG] 尝试从localStorage加载视频上传状态...');
      
      // 记录所有localStorage键
      const allKeys = [];
      for (let i = 0; i < localStorage.length; i++) {
        allKeys.push(localStorage.key(i));
      }
      console.log('[DEBUG] 当前localStorage中的所有键:', allKeys);
      
      const savedState = localStorage.getItem('video_upload_state');
      console.log('[DEBUG] 读取的localStorage值:', savedState);
      
      if (savedState) {
        try {
          const state = JSON.parse(savedState);
          console.log('[DEBUG] 解析后的状态:', state);
          
          // 检查状态是否在过去24小时内保存的
          const isValid = (Date.now() - (state.timestamp || 0)) < 24 * 60 * 60 * 1000;
          
          if (isValid) {
            // 不再使用etag，保留兼容性
            videoUploadEtag.value = '';
            reportId.value = state.reportId || null;
            uploadCallbackComplete.value = Boolean(state.uploadCallbackComplete);
            assessmentComplete.value = Boolean(state.assessmentComplete);
            reportDownloaded.value = Boolean(state.reportDownloaded);
            
            console.log('[DEBUG] 从localStorage加载的视频上传状态:',
              `reportId=${reportId.value}, ` +
              `uploadCallbackComplete=${uploadCallbackComplete.value}, ` +
              `assessmentComplete=${assessmentComplete.value}, ` +
              `reportDownloaded=${reportDownloaded.value}`);
            
            // 如果有上传记录，总是启动主轮询以确保状态同步
            if (state.reportId || state.uploadCallbackComplete) {
              console.log('[DEBUG] 检测到视频上传记录，启动主轮询');
              startMasterPolling();
            }
            
            return true;
          } else {
            // 状态过期，清除
            console.log('[DEBUG] 状态已过期，清除localStorage');
            localStorage.removeItem('video_upload_state');
          }
        } catch (parseError) {
          console.error('[DEBUG] 解析localStorage数据失败:', parseError);
        }
      } else {
        console.log('[DEBUG] localStorage中没有找到video_upload_state');
      }
    } catch (error) {
      console.error('[DEBUG] 加载视频上传状态失败:', error);
    }
    
    return false;
  }
  
  // 请求后端开始轮询
  async function initiateBackendPolling() {
    try {
      console.log(`请求后端开始轮询`)
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      const response = await fetch(getApiUrl('video/status'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          auth_token: authToken,
          start_polling: true
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        console.log('后端轮询已启动')
        statusPollingActive.value = true
        
        // 如果返回了report_id，更新状态
        if (result.data && result.data.report_id) {
          reportId.value = result.data.report_id
          console.log(`更新report_id: ${result.data.report_id}`)
        }
        
        // 启动主轮询
        startMasterPolling()
      } else {
        console.error('启动后端轮询失败:', result.message)
      }
    } catch (error) {
      console.error('请求后端轮询失败:', error)
    }
  }
  
  // 显示上传失败通知
  function showUploadFailureNotification(errorType = 'general') {
    try {
      const failureNotification = document.createElement('div');
      failureNotification.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2';
      
      let title = '视频上传处理失败';
      let message = '请检查网络连接并重试';
      
      // 根据错误类型调整提示信息
      if (errorType === 'server_unavailable') {
        title = '服务器暂时不可用';
        message = '可点击重新上传按钮再次尝试，无需重新录制';
      } else if (errorType === 'network') {
        title = '网络连接错误';
        message = '请检查网络连接后点击重新上传';
      } else if (errorType === 'timeout') {
        title = '上传超时';
        message = '服务器响应超时，可点击重新上传按钮再次尝试';
      }
      
      failureNotification.innerHTML = `
        <i class="fa-solid fa-exclamation-circle"></i>
        <div>
          <div class="font-medium">${title}</div>
          <div class="text-sm opacity-90">${message}</div>
        </div>
      `;
      document.body.appendChild(failureNotification);
      
      // 8秒后移除通知
      setTimeout(() => {
        failureNotification.classList.add('animate-fade-out');
        setTimeout(() => {
          failureNotification.remove();
        }, 500);
      }, 8000);
    } catch (e) {
      console.error('显示失败通知出错:', e);
    }
  }
  
  // 重置视频评估状态
  function resetVideoAssessment() {
    console.log('[DEBUG] 重置视频评估状态')
    videoAssessmentComplete.value = false
    videoAssessmentData.value = null
    videoProcessing.value = false
    videoReportPolling.value = false
    videoReportGenerated.value = false
    videoReportId.value = null
    videoReportUrl.value = null
    uploadCallbackComplete.value = false
    assessmentComplete.value = false
    videoUploadEtag.value = null
    statusPollingStarted.value = false
    reportDownloaded.value = false
    
    // 重置情绪评估状态
    emotionalAssessmentComplete.value = false
    emotionalAssessmentData.value = null
    emotionalProcessing.value = false
    
    // 清除localStorage中的状态
    localStorage.removeItem('video_upload_state')
    localStorage.removeItem('lastAssessmentTimestamp')
    
    // 确保轮询停止
    stopVideoReportPolling()
    stopStatusPolling()
    stopMasterPolling()
  }
  
  // 初始化方法 - 将在应用启动时调用
  async function initialize() {
    console.log('[DEBUG] 初始化评估存储...');
    
    try {
      // 首先尝试从localStorage加载状态
      const savedState = localStorage.getItem('video_upload_state');
      
      if (savedState) {
        try {
          const state = JSON.parse(savedState);
          // 检查状态是否在过去24小时内保存的
          const now = Date.now();
          const isValid = (now - (state.timestamp || 0)) < 24 * 60 * 60 * 1000;
          
          if (!isValid) {
            console.log('[DEBUG] 清除过期的评估状态');
            localStorage.removeItem('video_upload_state');
            resetVideoAssessment();
          } else {
            console.log('[DEBUG] 找到有效的存储状态，准备恢复');
            
            // 恢复状态
            loadVideoUploadState();
            
            // 如果有上传记录，启动主轮询
            if (reportId.value || uploadCallbackComplete.value) {
              console.log('[DEBUG] 恢复状态成功，启动状态轮询');
              startMasterPolling();
            }
          }
        } catch (parseError) {
          console.error('[DEBUG] 解析localStorage状态失败:', parseError);
          resetVideoAssessment();
        }
      } else {
        console.log('[DEBUG] localStorage中无视频上传状态');
        resetVideoAssessment();
      }
      
      return true;
    } catch (error) {
      console.error('[DEBUG] 初始化评估存储失败:', error);
      resetVideoAssessment();
      return false;
    }
  }
  
  // 尝试下载报告
  async function attemptReportDownload() {
    // 仅在评估完成但报告未下载时尝试下载
    if (!uploadCallbackComplete.value || !assessmentComplete.value || reportDownloaded.value) {
      return
    }
    
    try {
      console.log("尝试下载最新报告");
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      // 获取最新报告列表
      const response = await fetch(getApiUrl('check-latest-report'), {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`报告列表请求失败: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success && result.data) {
        const resultsData = result.data;
        
        // 获取report_id
        const reportId = resultsData.report_id || videoReportId.value;
        if (reportId) {
          console.log(`检测到评估已完成但报告未下载，尝试下载报告ID: ${reportId}`);
          
          // 下载报告
          await downloadVideoReport(reportId);
        } else {
          console.log("未找到有效的报告ID，无法下载报告");
        }
      }
    } catch (error) {
      console.error('检查最新报告状态失败:', error);
    }
  }
  
  // 更新报告下载状态
  async function updateReportDownloadStatus(isDownloaded = true) {
    if (!reportId.value) {
      console.warn('更新报告下载状态失败：缺少report_id')
      return false
    }
    
    try {
      console.log(`更新报告下载状态: report_id=${reportId.value}, isDownloaded=${isDownloaded}`)
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      // 调用API
      const response = await fetch(getApiUrl('video/update_report_status'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          report_id: reportId.value,
          auth_token: authToken,
          downloaded: isDownloaded
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        console.log('报告下载状态更新成功')
        // 更新本地状态
        reportDownloaded.value = isDownloaded
        // 保存到localStorage
        saveVideoUploadState()
        return true
      } else {
        console.error('更新报告下载状态失败:', result.message)
        return false
      }
    } catch (error) {
      console.error('更新报告下载状态出错:', error)
      return false
    }
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
    videoUploadEtag,
    reportId,
    uploadCallbackComplete,
    assessmentComplete,
    statusPollingActive,
    statusPollingInterval,
    faceDetected,
    facePosition,
    emotionalAssessmentComplete,
    emotionalAssessmentData,
    emotionalProcessing,
    psychologicalAssessmentReady,
    psychologicalAssessmentData,
    psychologicalProcessing,
    dialogCount,
    reportDownloaded,
    
    // 方法
    setVideoAssessmentComplete,
    setVideoAssessmentData,
    setVideoProcessing,
    setVideoUploadEtag,
    setReportId,
    setUploadCallbackComplete,
    setAssessmentComplete,
    setFaceDetected,
    setFacePosition,
    setEmotionalAssessmentComplete,
    setEmotionalAssessmentData,
    setEmotionalProcessing,
    setPsychologicalAssessmentReady,
    setPsychologicalAssessmentData,
    setPsychologicalProcessing,
    setDialogCount,
    setReportDownloaded,
    
    startVideoReportPolling,
    stopVideoReportPolling,
    downloadVideoReport,
    startCheckingAnalysisResult,
    loadAssessmentStatus,
    loadLatestEmotionalAssessment,
    checkVideoStatus,
    startStatusPolling,
    stopStatusPolling,
    
    // 新增：显式导出保存和加载函数
    saveVideoUploadState,
    loadVideoUploadState,
    
    // 其他导出方法
    resetVideoAssessment,
    initiateBackendPolling,
    startMasterPolling,
    stopMasterPolling,
    initialize,
    attemptReportDownload,
    updateReportDownloadStatus
  }
})
