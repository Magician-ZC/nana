import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAssessmentStore = defineStore('assessment', () => {
  // 视频评估状态
  const videoAssessmentComplete = ref(false)
  const videoAssessmentData = ref(null)
  const videoProcessing = ref(false)
  
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
    initialize
  }
})
