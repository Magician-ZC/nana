import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useUserStore } from './user'
import _ from 'lodash'

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
  const videoUploadEtag = ref('') // 存储上传视频的etag
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
    videoUploadEtag.value = etag
  }
  
  function setUploadCallbackComplete(status) {
    uploadCallbackComplete.value = status
  }
  
  function setAssessmentComplete(status) {
    assessmentComplete.value = status
  }
  
  function setReportDownloaded(status) {
    reportDownloaded.value = status
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
        return null
      }
      
      console.log(`开始下载视频评估报告, ID: ${reportId}`)
      
      // 获取用户认证令牌
      const authToken = userStore.getAuthToken() || ''
      
      // 准备请求参数
      const timestamp = Date.now()
      const sign = generateMD5(String(timestamp))
      
      // 加密请求内容
      const queryParams = { id: reportId }
      const jsonQuery = JSON.stringify(queryParams)
      const encryptedContent = encryptRequestData(jsonQuery)
      
      // 准备POST请求数据
      const formData = new FormData()
      formData.append('sign', sign)
      formData.append('content', encryptedContent)
      formData.append('timestamp', timestamp)
      
      // 发送下载请求 - 使用正确的API端点
      const response = await fetch('http://localhost:8666/api/download-video-report', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${authToken}`
        },
        body: formData
      })
      
      // 检查响应
      if (!response.ok) {
        const errorText = await response.text()
        console.error(`报告下载失败: 状态码=${response.status}, 错误=${errorText}`)
        
        // 显示下载失败通知
        const failureNotification = document.createElement('div')
        failureNotification.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2'
        failureNotification.innerHTML = `
          <i class="fa-solid fa-exclamation-circle"></i>
          <div>
            <div class="font-medium">报告下载失败</div>
            <div class="text-sm opacity-90">状态码: ${response.status}, 将在下次刷新页面时重试</div>
          </div>
        `
        document.body.appendChild(failureNotification)
        
        // 5秒后移除通知
        setTimeout(() => {
          failureNotification.classList.add('animate-fade-out')
          setTimeout(() => {
            failureNotification.remove()
          }, 500)
        }, 5000)
        
        return null
      }
      
      // 获取报告内容
      const reportBlob = await response.blob()
      
      // 保存报告到本地存储并更新状态
      const reportFileName = `emotion_report_${reportId}.pdf`
      const reportUrl = URL.createObjectURL(reportBlob)
      videoReportUrl.value = reportUrl
      
      console.log('视频评估报告下载成功:', reportUrl)
      
      // 更新报告下载状态
      reportDownloaded.value = true
      if (videoUploadEtag.value) {
        await updateReportDownloadStatus(videoUploadEtag.value, true)
      }
      saveVideoUploadState()
      
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
  
  // 加载评估状态 - 添加防抖和缓存机制
  async function loadAssessmentStatus() {
    // 检查是否应该执行请求
    if (!canMakeRequest(lastAssessmentStatusRequestTime)) {
      console.log('跳过评估状态请求 - 间隔太短');
      return;
    }
    
    try {
      lastAssessmentStatusRequestTime = Date.now();
      const response = await fetch('http://localhost:8666/api/assessment_status');
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
  
  // 加载最新的情绪评估结果 - 添加防抖和缓存机制
  async function loadLatestEmotionalAssessment() {
    // 检查是否应该执行请求
    if (!canMakeRequest(lastEmotionalAssessmentRequestTime)) {
      console.log('跳过情绪评估请求 - 间隔太短');
      return;
    }
    
    try {
      lastEmotionalAssessmentRequestTime = Date.now();
      const response = await fetch('http://localhost:8666/api/latest_assessment');
      const data = await response.json();
      
      if (data.success && data.has_assessment) {
        emotionalAssessmentComplete.value = true;
        
        // 如果已有有效的情绪评估数据，不需要再次请求详情
        if (!emotionalAssessmentData.value) {
        // 加载详细结果
          const resultsResponse = await fetch('http://localhost:8666/api/assessment_results');
          const resultsData = await resultsResponse.json();
          
          if (resultsData.success) {
            emotionalAssessmentData.value = resultsData.results;
            
            // 检查是否需要下载报告
            if (videoUploadEtag.value && assessmentComplete.value && !reportDownloaded.value) {
              // 获取报告ID
              const reportId = resultsData?.results?.reportId || videoReportId.value;
              if (reportId) {
                console.log(`检测到评估已完成但报告未下载，尝试下载报告ID: ${reportId}`);
                // 主动触发下载
                await downloadVideoReport(reportId);
              }
            }
          }
        }
      } else {
        emotionalAssessmentComplete.value = false;
        emotionalAssessmentData.value = null;
      }
    } catch (error) {
      console.error('加载情绪评估结果失败:', error);
    }
  }
  
  // 视频状态轮询函数
  // 使用防抖函数来减少API调用次数
  const debouncedCheckVideoStatus = _.debounce(async function(etag, shouldStartPolling) {
    if (!etag) return
    
    try {
      console.log(`[防抖后]检查视频状态: etag=${etag}, 启动轮询=${shouldStartPolling}`)
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      // 调用统一API
      const response = await fetch('http://localhost:8666/api/video/status', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          etag: etag,
          auth_token: authToken,
          start_polling: shouldStartPolling
        })
      })
      
      // 更新最后API调用时间
      if (!lastApiCallTime.value) {
        lastApiCallTime.value = {}
      }
      lastApiCallTime.value[`videoStatus-${etag}`] = Date.now()
      
      const result = await response.json()
      
      if (result.success) {
        const { upload_callback_status, assessment_status, polling_started, report_downloaded } = result.data
        
        console.log(`视频状态: 上传回调=${upload_callback_status}, 评估=${assessment_status}, 轮询=${polling_started || false}, 报告下载=${report_downloaded || false}`)
        
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
          // 显示上传失败通知
          showUploadFailureNotification()
          return
        }
        
        // 更新视频评估完成状态
        if (assessment_status) {
          setVideoAssessmentComplete(true)
          setVideoProcessing(false)
          
          // 如果评估完成，停止轮询
          stopStatusPolling()
          
          // 如果评估已完成，加载评估结果并更新状态
          if (upload_callback_status && assessment_status) {
            console.log('检测到评估已完成，加载评估结果')
            await loadLatestEmotionalAssessment()
            
            // 只有当报告状态尚未下载时调用下载接口
            if (!reportDownloaded.value) {
              console.log('检测到报告尚未下载，将获取最新评估报告')
              try {
                // 获取最新报告ID并下载
                if (videoReportId.value) {
                  console.log(`尝试下载报告ID: ${videoReportId.value}`)
                  await downloadVideoReport(videoReportId.value)
                } else {
                  // 尝试获取报告列表并下载最新的
                  console.log('报告ID未找到，尝试重新获取最新报告')
                  await loadLatestEmotionalAssessment()
                  
                  if (videoReportId.value) {
                    console.log(`获取到报告ID: ${videoReportId.value}，开始下载`)
                    await downloadVideoReport(videoReportId.value)
                  } else {
                    console.warn('无法获取报告ID，下载失败')
                  }
                }
              } catch (downloadError) {
                console.error('下载报告出错:', downloadError)
                // 即使下载出错，我们仍然保存当前状态，以便下次刷新页面时重试
                saveVideoUploadState()
              }
            } else {
              console.log('报告已下载，无需重新下载')
            }
            
            saveVideoUploadState()
          }
        } else if (upload_callback_status && !assessment_status && !statusPollingActive.value) {
          // 如果上传回调已完成但评估未完成，且未开始轮询，则自动在下次轮询时启动后端轮询
          console.log('下次轮询将自动启动后端轮询')
        }
      } else {
        console.warn('获取视频状态失败:', result.message)
        // API请求失败也增加失败计数
        uploadCallbackFailCount++
        if (uploadCallbackFailCount >= MAX_UPLOAD_CALLBACK_FAILS) {
          console.error('API请求持续失败，停止轮询')
          stopStatusPolling()
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
        showUploadFailureNotification()
      }
    }
  }, 1000);  // 设置防抖时间为1秒
  
  // 包装检查函数，对外暴露
  function checkVideoStatus(etag, shouldStartPolling = false) {
    if (!etag) return;
    
    console.log(`[原始调用]检查视频状态: etag=${etag}, 启动轮询=${shouldStartPolling}`)
    
    // 立即启动轮询的情况下不去抖动
    if (shouldStartPolling) {
      debouncedCheckVideoStatus(etag, true);
      return;
    }
    
    // 常规检查状态时使用防抖
    debouncedCheckVideoStatus(etag, false);
  }
  
  // 开始轮询检查视频上传和评估状态
  function startStatusPolling(etag) {
    if (!etag) {
      console.warn('无法启动状态轮询: 缺少etag')
      return
    }
    
    // 避免重复启动轮询
    if (statusPollingActive.value) {
      console.log('状态轮询已经在运行中')
      return
    }
    
    try {
      console.log(`启动状态轮询: etag=${etag}`)
      
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
        if (canCallApi(`checkVideoStatus-${etag}`)) {
          checkVideoStatus(etag, shouldStartPolling)
          // 标记已尝试启动后端轮询
          statusPollingStarted.value = true
        }
      }, 5000) // 增加到5秒检查一次
      
      // 保存轮询间隔引用
      statusPollingInterval.value = statusInterval
      
      // 立即执行一次检查并启动后端轮询
      checkVideoStatus(etag, true)
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
        etag: videoUploadEtag.value,
        uploadCallbackComplete: uploadCallbackComplete.value,
        assessmentComplete: assessmentComplete.value,
        reportDownloaded: reportDownloaded.value,
        timestamp: Date.now()
      }
      
      // 记录日志，特别是报告下载状态
      console.log(`保存视频上传状态: etag=${uploadState.etag}, 上传回调=${uploadState.uploadCallbackComplete}, 评估=${uploadState.assessmentComplete}, 报告下载=${uploadState.reportDownloaded}`);
      
      // 如果报告下载状态是true，额外记录
      if (uploadState.reportDownloaded) {
        console.log(`警告: 正在将reportDownloaded保存为true，确保这是期望的行为`);
      }
      
      localStorage.setItem('video_upload_state', JSON.stringify(uploadState))
      return uploadState;
    } catch (error) {
      console.error('保存视频上传状态失败:', error)
      return null;
    }
  }
  
  // 从localStorage加载视频上传状态
  function loadVideoUploadState() {
    try {
      const savedState = localStorage.getItem('video_upload_state')
      if (savedState) {
        const state = JSON.parse(savedState)
        // 检查状态是否在过去24小时内保存的
        const isValid = (Date.now() - state.timestamp) < 24 * 60 * 60 * 1000
        
        if (isValid) {
          videoUploadEtag.value = state.etag || ''
          uploadCallbackComplete.value = state.uploadCallbackComplete || false
          assessmentComplete.value = state.assessmentComplete || false
          reportDownloaded.value = state.reportDownloaded || false
          
          console.log('从localStorage加载的视频上传状态:', state)
          
          // 如果上传回调已完成但评估未完成，启动后端轮询
          if (state.uploadCallbackComplete && !state.assessmentComplete && state.etag) {
            checkVideoStatus(state.etag)
          }
          
          // 如果评估已完成，检查是否有评估结果
          if (state.uploadCallbackComplete && state.assessmentComplete) {
            console.log('检测到评估已完成，将检查评估结果')
            loadLatestEmotionalAssessment()
            // 不再强制设置报告下载状态为true，而是保持原始状态
            // reportDownloaded.value = true
            
            // 如果报告未下载，尝试在后台启动下载
            if (!state.reportDownloaded) {
              console.log('检测到报告尚未下载，将在加载后尝试下载')
            }
            
            // 仍然保存状态，但不改变reportDownloaded的值
            saveVideoUploadState()
          }
          
          return true
        } else {
          // 状态过期，清除
          localStorage.removeItem('video_upload_state')
        }
      }
    } catch (error) {
      console.error('加载视频上传状态失败:', error)
    }
    
    return false
  }
  
  // 请求后端开始轮询
  async function initiateBackendPolling(etag) {
    if (!etag) return
    
    try {
      console.log(`请求后端开始轮询: etag=${etag}`)
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      const response = await fetch('http://localhost:8666/api/video/start_polling', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          etag: etag,
          auth_token: authToken
        })
      })
      
      const result = await response.json()
      
      if (result.success) {
        console.log('后端轮询已启动')
        statusPollingActive.value = true
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
    videoAssessmentComplete.value = false
    videoAssessmentData.value = null
    videoProcessing.value = false
    videoReportPolling.value = false
    videoReportGenerated.value = false
    videoReportId.value = null
    videoReportUrl.value = null
    uploadCallbackComplete.value = false
    assessmentComplete.value = false
    videoUploadEtag.value = ''
    statusPollingStarted.value = false
    reportDownloaded.value = false
    
    // 清除localStorage中的状态
    localStorage.removeItem('video_upload_state')
    
    // 确保轮询停止
    stopVideoReportPolling()
    stopStatusPolling()
  }
  
  // 初始化加载 - 添加防重复请求保护
  let isInitializing = false;
  async function initialize() {
    // 防止重复初始化
    if (isInitializing) {
      console.log('已经在初始化中，跳过重复请求');
      return;
    }
    
    try {
      isInitializing = true;
      
      // 尝试从localStorage加载视频上传状态
      const hasLocalState = loadVideoUploadState();
      
      // 并行加载其他状态
      await Promise.all([
        loadAssessmentStatus(),
        loadLatestEmotionalAssessment()
      ]);
      
      // 优化检查：如果报告评估已完成但未下载，尝试获取报告列表并下载
      if (hasLocalState && videoUploadEtag.value && 
          uploadCallbackComplete.value && assessmentComplete.value) {
        
        console.log('检测到有评估完成，检查最新报告状态');
        
        // 获取授权令牌
        const authToken = userStore.getAuthToken();
        
        // 首先通过API检查真实的报告下载状态，避免使用可能不准确的本地状态
        try {
          console.log('获取最新的报告下载状态');
          const statusResponse = await fetch('http://localhost:8666/api/video/status', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
              etag: videoUploadEtag.value,
              auth_token: authToken,
              start_polling: false
            })
          });
          
          if (statusResponse.ok) {
            const statusResult = await statusResponse.json();
            
            if (statusResult.success) {
              // 使用后端返回的最新状态更新报告下载状态
              const backendReportDownloaded = statusResult.data.report_downloaded;
              console.log(`后端返回的报告下载状态: ${backendReportDownloaded}`);
              
              if (reportDownloaded.value !== backendReportDownloaded) {
                console.log(`更新本地报告下载状态: ${reportDownloaded.value} -> ${backendReportDownloaded}`);
                reportDownloaded.value = backendReportDownloaded;
                saveVideoUploadState();
              }
              
              // 如果报告实际未下载，才尝试下载
              if (!backendReportDownloaded) {
                await attemptReportDownload(authToken);
              } else {
                console.log('后端确认报告已下载，无需重新下载');
              }
            }
          }
        } catch (statusError) {
          console.error('获取报告状态失败:', statusError);
          // 如果获取状态失败，则仍使用本地状态
          if (!reportDownloaded.value) {
            await attemptReportDownload(authToken);
          }
        }
      }
    } catch (error) {
      console.error('初始化评估状态失败:', error);
    } finally {
      isInitializing = false;
    }
  }
  
  // 帮助函数：尝试下载报告
  async function attemptReportDownload(authToken) {
    console.log('尝试下载报告');
    
    // 检查视频状态，这会触发下载逻辑
    await checkVideoStatus(videoUploadEtag.value, false);
    
    // 如果有报告ID，尝试直接下载
    if (videoReportId.value) {
      console.log(`获取到报告ID，尝试下载: ${videoReportId.value}`);
      await downloadVideoReport(videoReportId.value);
    } else {
      // 直接请求后端检查报告状态
      // 这将只检查第一条报告的状态，更高效
      try {
        console.log('尝试直接从后端获取最新报告状态');
        await fetch(`http://localhost:8666/api/check-latest-report?etag=${videoUploadEtag.value}&token=${authToken}`, {
          method: 'GET'
        });
        
        // 重新加载状态以获取最新信息
        await loadLatestEmotionalAssessment();
      } catch (error) {
        console.error('检查最新报告状态失败:', error);
      }
    }
  }
  
  // 更新报告下载状态
  async function updateReportDownloadStatus(etag, isDownloaded = true) {
    if (!etag) return
    
    try {
      console.log(`更新报告下载状态: etag=${etag}, isDownloaded=${isDownloaded}`)
      
      // 获取授权令牌
      const authToken = userStore.getAuthToken()
      
      // 调用API
      const response = await fetch('http://localhost:8666/api/video/update_report_status', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
          etag: etag,
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
    faceDetected,
    facePosition,
    emotionalAssessmentComplete,
    emotionalAssessmentData,
    emotionalProcessing,
    psychologicalAssessmentReady,
    psychologicalAssessmentData,
    psychologicalProcessing,
    dialogCount,
    videoUploadEtag,
    uploadCallbackComplete,
    assessmentComplete,
    statusPollingActive,
    statusPollingStarted,
    reportDownloaded,
    
    // 方法
    setVideoAssessmentComplete,
    setVideoAssessmentData,
    setVideoProcessing,
    setVideoUploadEtag,
    setUploadCallbackComplete,
    setAssessmentComplete,
    setReportDownloaded,
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
    downloadVideoReport,
    analyzeVideoReport,
    startStatusPolling,
    stopStatusPolling,
    checkVideoStatus,
    saveVideoUploadState,
    loadVideoUploadState,
    showUploadFailureNotification,
    updateReportDownloadStatus,
    attemptReportDownload
  }
})
