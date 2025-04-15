<template>
  <div class="video-recorder-container">
    <!-- 录制状态提示 -->
    <div v-if="isRecording" class="recording-indicator">
      <div :class="['recording-dot', { 'paused': recordingPaused }]"></div>
      <span>{{ recordingPaused ? '录制已暂停' : `正在录制 ${recordingTimeLeft}s` }}</span>
    </div>

    <!-- 摄像头选择器 -->
    <div class="camera-selector" v-if="!isRecording && !isProcessing">
      <select v-model="selectedCameraId" @change="onCameraChange" class="camera-dropdown">
        <option value="">请选择摄像头</option>
        <option v-for="camera in availableCameras" :key="camera.deviceId" :value="camera.deviceId">
          {{ camera.label || `摄像头 ${camera.deviceId.substring(0, 8)}...` }}
        </option>
      </select>
    </div>

    <!-- 视频预览区域 -->
    <div class="video-preview">
      <video ref="videoElement" autoplay muted playsinline></video>
      <canvas ref="faceCanvas" class="face-canvas"></canvas>
      
      <!-- 录制前的指导信息 -->
      <div v-if="!isRecording && !isProcessing && !recordingComplete" class="guidance-overlay">
        <div class="guidance-content">
          <div class="icon-container">
            <i class="fa-solid fa-video"></i>
          </div>
          <h3>情绪状态视频评估</h3>
          <p>{{ guidanceText }}</p>
          <p>系统将会自动录制60秒视频进行情绪评估</p>
          
          <!-- 人脸在框内时间进度条 -->
          <div class="face-timer-progress" v-if="!faceReadyForRecording">
            <div class="face-timer-bar" :style="{ width: `${(faceInFrameTime / requiredFaceTime) * 100}%` }"></div>
          </div>
          
          <button 
            @click="startRecording" 
            :disabled="!canStartRecording"
            class="start-recording-btn"
          >
            开始录制
          </button>
        </div>
      </div>
      
      <!-- 处理中状态 -->
      <div v-if="isProcessing" class="processing-overlay">
        <div class="processing-content">
          <div class="spinner"></div>
          <p>{{ processingMessage }}</p>
        </div>
      </div>
      
      <!-- 完成状态 -->
      <div v-if="recordingComplete && !isProcessing" class="complete-overlay">
        <div class="complete-content">
          <div class="icon-container success">
            <i class="fa-solid fa-check"></i>
          </div>
          <h3>视频评估完成</h3>
          <p>{{ completeMessage }}</p>
          <button @click="closeRecorder" class="complete-btn">查看评估结果</button>
        </div>
      </div>
      
      <!-- 错误状态 -->
      <div v-if="hasError" class="error-overlay">
        <div class="error-content">
          <div class="icon-container error">
            <i class="fa-solid fa-exclamation-triangle"></i>
          </div>
          <h3>出现错误</h3>
          <p>{{ errorMessage }}</p>
          <div class="error-buttons">
            <button v-if="savedVideoBlob" @click="retryUpload" class="retry-btn">重新上传</button>
            <button @click="retryCamera" class="retry-btn secondary">重试摄像头</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 关闭按钮 -->
    <button 
      v-if="!isRecording && !isProcessing" 
      @click="$emit('close')"
      class="close-button"
    >
      <i class="fa-solid fa-times"></i>
    </button>

    <!-- 添加调试信息 -->
    <div class="debug-info" v-if="showDebugInfo">
      <div>人脸检测状态: {{ assessmentStore.faceDetected ? "检测到" : "未检测" }}</div>
      <div>人脸位置: {{ assessmentStore.facePosition }}</div>
      <div>持续时间: {{ faceInFrameTime }}秒</div>
      <div>准备状态: {{ faceReadyForRecording ? "准备好" : "未准备" }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useAssessmentStore } from '../stores/assessment'
import { useUserStore } from '../stores/user'
import { getApiUrl } from '../utils/api'

const props = defineProps({
  recordingDuration: {
    type: Number,
    default: 60
  }
})

const emit = defineEmits(['close', 'recording-complete'])

// 添加调试开关
const showDebugInfo = ref(true)  // 设置为false可以在生产环境隐藏

// 获取状态管理器
const assessmentStore = useAssessmentStore()
const userStore = useUserStore()

// 状态变量
const videoElement = ref(null)
const faceCanvas = ref(null)
const stream = ref(null)
const mediaRecorder = ref(null)
const recordedChunks = ref([])
const savedVideoBlob = ref(null) // 保存视频Blob用于重试上传
const isRecording = ref(false)
const recordingStartTime = ref(0)
const recordingTimeLeft = ref(props.recordingDuration)
const cameraReady = ref(false)
const isProcessing = ref(false)
const processingMessage = ref('正在处理视频...')
const recordingComplete = ref(false)
const completeMessage = ref('评估已完成，您可以查看结果')
const hasError = ref(false)
const errorMessage = ref('')
const faceDetectionInterval = ref(null)
const timerInterval = ref(null)
const availableCameras = ref([])
const selectedCameraId = ref('')

// 人脸检测相关状态
const faceInFrameTime = ref(0) // 人脸在框内的持续时间（秒）
const faceInFrameStartTime = ref(0) // 人脸进入框内的起始时间
const faceInFrameTimer = ref(null) // 人脸在框内计时器
const requiredFaceTime = ref(10) // 需要的人脸在框内时间（秒）
const faceReadyForRecording = ref(false) // 人脸是否已准备好进行录制
const recordingPaused = ref(false) // 录制是否暂停
const recordingPausedTime = ref(0) // 录制暂停的累计时间（毫秒）
const lastPauseTime = ref(0) // 上次暂停的时间戳

// 计算属性
const isFaceInPosition = computed(() => {
  return assessmentStore.faceDetected && assessmentStore.facePosition === 'center'
})

// 更新指导文本
const guidanceText = computed(() => {
  if (!faceReadyForRecording.value) {
    return `请保持面部在框内 ${faceInFrameTime.value}/${requiredFaceTime.value}秒`
  } else {
    return '准备就绪，可以开始录制'
  }
})

// 更新录制按钮状态
const canStartRecording = computed(() => {
  return cameraReady.value && !isProcessing.value && faceReadyForRecording.value
})

// 选择特定摄像头
const onCameraChange = async () => {
  if (stream.value) {
    try {
      // 停止当前流
      stream.value.getTracks().forEach(track => {
        try {
          track.stop()
        } catch (e) {
          console.warn('停止视频轨道失败:', e)
        }
      })
      stream.value = null
      
      // 添加短暂延迟，确保资源完全释放
      await new Promise(resolve => setTimeout(resolve, 500))
    } catch (error) {
      console.error('关闭现有摄像头失败:', error)
    }
  }
  
  if (selectedCameraId.value) {
    try {
      await initCameraWithDeviceId(selectedCameraId.value)
    } catch (error) {
      console.error('切换摄像头失败:', error)
      hasError.value = true
      errorMessage.value = `切换摄像头失败: ${error.message}`
    }
  }
}

// 检测可用的摄像头设备
const enumerateDevices = async () => {
  try {
    // 使用简单的枚举，不尝试获取临时权限
    // 这样可以获取到设备ID，但可能无法获取标签名称
    const devices = await navigator.mediaDevices.enumerateDevices()
    const videoDevices = devices.filter(device => device.kind === 'videoinput')
    availableCameras.value = videoDevices
    console.log('可用的摄像头设备:', videoDevices)
    
    return videoDevices.length > 0
  } catch (error) {
    console.error('获取设备列表失败:', error)
    return false
  }
}

// 使用特定设备ID初始化摄像头
const initCameraWithDeviceId = async (deviceId) => {
  try {
    resetStates()
    
    console.log(`尝试使用设备ID访问摄像头: ${deviceId}`)
    
    // 设置更宽松的约束，并添加重试逻辑
    let attempts = 0
    const maxAttempts = 3
    let error

    while (attempts < maxAttempts) {
      try {
        attempts++
        console.log(`尝试访问摄像头: 第 ${attempts} 次尝试`)
        
        // 获取摄像头，保持原始分辨率但降低码率
        const mediaStream = await navigator.mediaDevices.getUserMedia({
          video: {
            deviceId: deviceId ? { ideal: deviceId } : undefined,
            width: { ideal: 720 },          // 恢复原始宽度720
            height: { ideal: 1280 },        // 恢复原始高度1280
            frameRate: { ideal: 25 }        // 指定帧率为25fps
          },
          audio: false  // 不请求音频以简化初始化
        })
        
        // 成功获取流
        stream.value = mediaStream
        
        // 获取当前视频轨道能力和设置
        const videoTrack = mediaStream.getVideoTracks()[0]
        if (videoTrack) {
          const settings = videoTrack.getSettings()
          console.log('成功访问摄像头，当前设置:', settings)
          console.log('实际使用的设备ID:', settings.deviceId)
          console.log('实际分辨率:', settings.width, 'x', settings.height)
          console.log('实际帧率:', settings.frameRate)
        }
        
        // 设置视频源
        if (videoElement.value) {
          videoElement.value.srcObject = mediaStream
          videoElement.value.onloadedmetadata = () => {
            cameraReady.value = true
            // 初始化人脸检测
            initFaceDetection()
          }
        }
        
        // 成功获取流，跳出循环
        return
      } catch (err) {
        error = err
        console.warn(`第 ${attempts} 次尝试失败:`, err)
        
        // 如果分辨率约束失败，尝试使用更宽松的约束
        if (attempts === maxAttempts - 1) {
          console.log('尝试使用更宽松的约束...')
          try {
            // 使用更宽松的约束，仅指定帧率
            const mediaStream = await navigator.mediaDevices.getUserMedia({
              video: {
                deviceId: deviceId ? { ideal: deviceId } : undefined,
                frameRate: { ideal: 25 }
              },
              audio: false
            })
            
            // 成功获取流
            stream.value = mediaStream
            
            // 获取视频轨道信息
            const videoTrack = mediaStream.getVideoTracks()[0]
            if (videoTrack) {
              console.log('使用宽松约束成功，当前设置:', videoTrack.getSettings())
            }
            
            // 设置视频源
            if (videoElement.value) {
              videoElement.value.srcObject = mediaStream
              videoElement.value.onloadedmetadata = () => {
                cameraReady.value = true
                // 初始化人脸检测
                initFaceDetection()
              }
            }
            
            return
          } catch (fallbackErr) {
            console.error('宽松约束也失败:', fallbackErr)
            error = fallbackErr
          }
        }
        
        // 等待一段时间再重试
        if (attempts < maxAttempts) {
          await new Promise(resolve => setTimeout(resolve, 1000))
        }
      }
    }
    
    // 所有尝试都失败了，抛出最后捕获的错误
    throw error || new Error('无法访问摄像头，多次尝试均失败')
    
  } catch (error) {
    console.error(`使用设备ID访问摄像头失败:`, error)
    hasError.value = true
    errorMessage.value = `无法访问指定摄像头: ${error.message}`
  }
}

// 方法
const initCamera = async () => {
  try {
    resetStates(true)  // 清除保存的视频数据
    
    // 枚举可用设备
    await enumerateDevices()
    
    // 如果没有检测到摄像头，提示用户
    if (availableCameras.value.length === 0) {
      hasError.value = true
      errorMessage.value = '未检测到可用的摄像头设备'
      return
    }
    
    // 默认选择第一个设备
    if (!selectedCameraId.value && availableCameras.value.length > 0) {
      selectedCameraId.value = availableCameras.value[0].deviceId
      // 由于删除了watch钩子，需要在这里直接调用初始化
      await initCameraWithDeviceId(selectedCameraId.value)
    }
  } catch (error) {
    console.error('摄像头初始化失败:', error)
    hasError.value = true
    
    // 根据错误类型提供不同的错误信息
    if (error.name === 'NotFoundError') {
      errorMessage.value = '找不到摄像头设备，请确保您的电脑已连接摄像头并且没有被其他程序占用。'
    } else if (error.name === 'NotAllowedError') {
      errorMessage.value = '摄像头访问权限被拒绝，请在浏览器设置中允许访问摄像头。'
    } else if (error.name === 'AbortError') {
      errorMessage.value = '摄像头访问被中断，可能是硬件或浏览器问题。'
    } else if (error.name === 'NotReadableError') {
      errorMessage.value = '无法读取摄像头，可能被其他应用程序占用或硬件故障。'
    } else {
      errorMessage.value = `无法访问摄像头: ${error.message || '未知错误'}。请检查设备连接。`
    }
  }
}

const initFaceDetection = () => {
  // 使用Canvas绘制人脸框
  const ctx = faceCanvas.value.getContext('2d')
  faceCanvas.value.width = videoElement.value.videoWidth
  faceCanvas.value.height = videoElement.value.videoHeight
  
  // 初始化人脸计时
  faceInFrameTime.value = 0
  faceInFrameStartTime.value = 0
  faceReadyForRecording.value = false
  
  console.log('开始加载人脸检测模型...')
  
  // 检查是否已经加载了TensorFlow和BlazeFace
  const loadScript = (src) => {
    return new Promise((resolve, reject) => {
      // 检查是否已加载
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve()
        return
      }
      
      const script = document.createElement('script')
      script.src = src
      script.onload = resolve
      script.onerror = reject
      document.head.appendChild(script)
    })
  }
  
  // 按顺序加载脚本
  loadScript('https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@3.11.0/dist/tf.min.js')
    .then(() => {
      console.log('TensorFlow.js 加载成功')
      return loadScript('https://cdn.jsdelivr.net/npm/@tensorflow-models/blazeface@0.0.7/dist/blazeface.min.js')
    })
    .then(() => {
      console.log('BlazeFace 加载成功，正在初始化模型...')
      
      // 确认全局对象存在
      if (!window.blazeface) {
        throw new Error('无法找到blazeface全局对象')
      }
      
      // 使用全局对象初始化模型
      return window.blazeface.load()
    })
    .then(model => {
      console.log('BlazeFace 模型初始化成功')
      
      // 设置定时检测
      faceDetectionInterval.value = setInterval(async () => {
        if (videoElement.value && videoElement.value.readyState === 4) {
          try {
            // 人脸检测
            const predictions = await model.estimateFaces(videoElement.value, false)
            
            // 清除画布
            ctx.clearRect(0, 0, faceCanvas.value.width, faceCanvas.value.height)
            
            if (predictions.length > 0) {
              // 更新人脸检测状态
              assessmentStore.setFaceDetected(true)
              
              const face = predictions[0]
              const x = face.topLeft[0]
              const y = face.topLeft[1]
              const width = face.bottomRight[0] - face.topLeft[0]
              const height = face.bottomRight[1] - face.topLeft[1]
              
              // 计算人脸位置
              const canvasWidth = faceCanvas.value.width
              const canvasHeight = faceCanvas.value.height
              const faceX = x + width / 2
              const faceY = y + height / 2
              
              // 画布中心区域的边界 - 放宽判断标准，让用户更容易进入中心
              const centerXMin = canvasWidth * 0.25 // 原来是0.3
              const centerXMax = canvasWidth * 0.75 // 原来是0.7
              const centerYMin = canvasHeight * 0.25 // 原来是0.3
              const centerYMax = canvasHeight * 0.75 // 原来是0.7
              
              // 判断人脸位置
              let position = 'center'
              if (faceX < centerXMin) position = 'left'
              else if (faceX > centerXMax) position = 'right'
              else if (faceY < centerYMin) position = 'top'
              else if (faceY > centerYMax) position = 'bottom'
              
              // 调试输出
              if (!isRecording.value && faceInFrameStartTime.value > 0) {
                console.log('人脸位置:', position, '时间:', faceInFrameTime.value)
              }
              
              assessmentStore.setFacePosition(position)
              
              // 处理录制中的人脸位置变化
              if (isRecording.value) {
                if (position !== 'center') {
                  // 如果人脸不在中心，并且之前未暂停，则暂停录制
                  if (!recordingPaused.value) {
                    pauseRecording()
                  }
                } else if (recordingPaused.value) {
                  // 如果人脸恢复到中心位置，并且之前处于暂停状态，则恢复录制
                  resumeRecording()
                }
              }
              
              // 处理人脸在框内时间计算
              if (position === 'center' && !isRecording.value) {
                if (faceInFrameStartTime.value === 0) {
                  // 人脸刚进入框内，开始计时
                  console.log('人脸进入中心，开始计时')
                  faceInFrameStartTime.value = Date.now()
                } else {
                  // 更新人脸在框内的时间
                  const currentTime = Date.now()
                  const timeInFrame = (currentTime - faceInFrameStartTime.value) / 1000
                  faceInFrameTime.value = Math.floor(timeInFrame)
                  
                  // 检查是否达到所需时间
                  if (faceInFrameTime.value >= requiredFaceTime.value && !faceReadyForRecording.value) {
                    console.log('人脸已经保持在中心足够时间，准备好录制')
                    faceReadyForRecording.value = true
                  }
                }
              } else if (!isRecording.value && position !== 'center') {
                if (faceInFrameStartTime.value !== 0) {
                  console.log('人脸离开中心，重置计时')
                }
                // 人脸离开框，重置计时
                faceInFrameStartTime.value = 0
                faceInFrameTime.value = 0
                faceReadyForRecording.value = false
              }
              
              // 绘制人脸框
              ctx.strokeStyle = position === 'center' ? '#4CAF50' : '#FF5252'
              ctx.lineWidth = 3
              ctx.strokeRect(x, y, width, height)
              
              // 绘制参考框
              ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)'
              ctx.lineWidth = 2
              ctx.strokeRect(
                centerXMin, 
                centerYMin, 
                centerXMax - centerXMin, 
                centerYMax - centerYMin
              )
              
              // 显示位置提示
              if (position !== 'center') {
                ctx.font = '24px Arial'
                ctx.fillStyle = '#FF5252'
                ctx.textAlign = 'center'
                
                let message = ''
                switch(position) {
                  case 'left': message = '请向右移动'; break
                  case 'right': message = '请向左移动'; break
                  case 'top': message = '请向下移动'; break
                  case 'bottom': message = '请向上移动'; break
                }
                
                ctx.fillText(message, canvasWidth / 2, 40)
              } else if (!isRecording.value && !faceReadyForRecording.value) {
                // 显示人脸在框内的时间
                ctx.font = '24px Arial'
                ctx.fillStyle = '#4CAF50'
                ctx.textAlign = 'center'
                ctx.fillText(`持续保持 ${faceInFrameTime.value}/${requiredFaceTime.value}秒`, canvasWidth / 2, 40)
              } else if (isRecording.value && recordingPaused.value) {
                // 显示录制暂停提示
                ctx.font = '24px Arial'
                ctx.fillStyle = '#FF5252'
                ctx.textAlign = 'center'
                ctx.fillText('录制暂停，请将脸部对准框内', canvasWidth / 2, 40)
              }
            } else {
              // 未检测到人脸
              assessmentStore.setFaceDetected(false)
              assessmentStore.setFacePosition('none')
              
              // 如果正在录制，暂停
              if (isRecording.value && !recordingPaused.value) {
                pauseRecording()
              }
              
              // 重置人脸准备时间
              if (!isRecording.value) {
                if (faceInFrameStartTime.value !== 0) {
                  console.log('未检测到人脸，重置计时')
                }
                faceInFrameStartTime.value = 0
                faceInFrameTime.value = 0
                faceReadyForRecording.value = false
              }
              
              // 显示未检测到人脸的提示
              ctx.font = '24px Arial'
              ctx.fillStyle = '#FF5252'
              ctx.textAlign = 'center'
              ctx.fillText('未检测到人脸', faceCanvas.value.width / 2, 40)
            }
          } catch (detectionError) {
            console.error('人脸检测过程中出错:', detectionError)
          }
        }
      }, 100)
    })
    .catch(error => {
      console.error('人脸检测初始化失败:', error)
      hasError.value = true
      errorMessage.value = `人脸检测模型加载失败: ${error.message}`
    })
}

// 暂停录制
const pauseRecording = () => {
  recordingPaused.value = true
  lastPauseTime.value = Date.now()
}

// 恢复录制
const resumeRecording = () => {
  if (recordingPaused.value) {
    recordingPaused.value = false
    const pauseDuration = Date.now() - lastPauseTime.value
    recordingPausedTime.value += pauseDuration
  }
}

const startRecording = () => {
  if (!cameraReady.value || !stream.value || !faceReadyForRecording.value) return
  
  try {
    // 重置录制状态
    recordedChunks.value = []
    isRecording.value = true
    recordingPaused.value = false
    recordingPausedTime.value = 0
    recordingStartTime.value = Date.now()
    recordingTimeLeft.value = props.recordingDuration
    
    // 获取当前流的能力信息
    const videoTrack = stream.value.getVideoTracks()[0]
    if (videoTrack) {
      const settings = videoTrack.getSettings()
      console.log('录制使用的视频轨道信息:', settings)
      
      // 检查当前流是否符合所需参数
      console.log(`录制分辨率: ${settings.width}x${settings.height}，帧率: ${settings.frameRate}fps`)
      
      // 约束记录器，确保使用所需参数
      const idealSettings = {
        width: 720,     // 恢复原始宽度720
        height: 1280,   // 恢复原始高度1280
        frameRate: 25
      }
      
      // 记录与理想设置的差异
      if (settings.width !== idealSettings.width || settings.height !== idealSettings.height) {
        console.warn(`注意: 实际分辨率(${settings.width}x${settings.height})与目标(${idealSettings.width}x${idealSettings.height})不同`)
      }
      
      if (settings.frameRate && Math.abs(settings.frameRate - idealSettings.frameRate) > 1) {
        console.warn(`注意: 实际帧率(${settings.frameRate})与目标(${idealSettings.frameRate})不同`)
      }
    }
    
    // 初始化MediaRecorder，使用浏览器支持的最佳编码
    let options = {}
    
    if (MediaRecorder.isTypeSupported('video/webm;codecs=vp9')) {
      options = { 
        mimeType: 'video/webm;codecs=vp9',
        videoBitsPerSecond: 1000000 // 降低到1Mbps
      }
      console.log('使用 VP9 编码, 1Mbps 码率')
    } else if (MediaRecorder.isTypeSupported('video/webm;codecs=vp8')) {
      options = { 
        mimeType: 'video/webm;codecs=vp8',
        videoBitsPerSecond: 1000000
      }
      console.log('使用 VP8 编码, 1Mbps 码率')
    } else if (MediaRecorder.isTypeSupported('video/webm')) {
      options = { 
        mimeType: 'video/webm',
        videoBitsPerSecond: 1000000
      }
      console.log('使用默认 WebM 编码, 1Mbps 码率')
    } else if (MediaRecorder.isTypeSupported('video/mp4')) {
      options = { 
        mimeType: 'video/mp4',
        videoBitsPerSecond: 1000000
      }
      console.log('使用 MP4 编码, 1Mbps 码率')
    }
    
    console.log('视频将在后端转换为AVI格式')
    mediaRecorder.value = new MediaRecorder(stream.value, options)
    
    // 设置录制事件处理
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunks.value.push(event.data)
      }
    }
    
    // 录制完成后上传
    mediaRecorder.value.onstop = () => {
      if (recordedChunks.value.length === 0) return
      
      isRecording.value = false
      uploadVideo()
    }
    
    // 开始录制
    mediaRecorder.value.start(1000) // 每秒触发一次ondataavailable事件
    
    // 设置录制计时器
    timerInterval.value = setInterval(() => {
      if (recordingPaused.value) return // 如果暂停，不更新时间
      
      // 计算实际已录制的时间（减去暂停的时间）
      const elapsedTime = Date.now() - recordingStartTime.value - recordingPausedTime.value
      const elapsedSeconds = Math.floor(elapsedTime / 1000)
      recordingTimeLeft.value = Math.max(0, props.recordingDuration - elapsedSeconds)
      
      if (recordingTimeLeft.value <= 0) {
        stopRecording()
      }
    }, 1000)
  
  } catch (error) {
    console.error('录制初始化失败:', error)
    hasError.value = true
    errorMessage.value = '录制初始化失败，请重试。'
    isRecording.value = false
  }
}

const stopRecording = () => {
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
  
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
}

const uploadVideo = async () => {
  isProcessing.value = true
  processingMessage.value = '正在处理视频...'
  
  try {
    // 获取录制的正确MIME类型
    let mimeType = 'video/webm'; // 默认类型
    
    // 尝试从MediaRecorder获取实际MIME类型
    if (mediaRecorder.value && mediaRecorder.value.mimeType) {
      mimeType = mediaRecorder.value.mimeType;
    } else if (recordedChunks.value.length > 0 && recordedChunks.value[0].type) {
      // 从第一个数据块获取类型
      mimeType = recordedChunks.value[0].type;
    }
    
    console.log(`使用实际MIME类型创建Blob: ${mimeType}`);
    
    // 创建视频Blob - 使用实际录制格式，不强制标记为AVI
    const videoBlob = new Blob(recordedChunks.value, { type: mimeType })
    
    // 保存视频Blob用于重试上传
    savedVideoBlob.value = videoBlob;
    
    // 创建FormData对象上传文件 - 使用实际扩展名
    const formData = new FormData()
    const fileExtension = mimeType.includes('webm') ? 'webm' : 
                         mimeType.includes('mp4') ? 'mp4' : 'avi';
    formData.append('file', videoBlob, `emotion_assessment.${fileExtension}`)
    
    // 从用户状态获取授权令牌
    let authToken = userStore.getAuthToken();
    
    // 如果没有token，使用默认开发测试token
    if (!authToken) {
      console.warn('未找到用户授权令牌，使用开发测试token');
      authToken = userStore.setDevelopmentToken();
    } else {
      // 确保token正确存储在userStore中
      userStore.setAuthToken(authToken);
    }
    
    console.log('授权令牌已存储:', authToken);
    
    // 使用七牛云上传接口
    const response = await fetch(getApiUrl('upload-video'), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      body: formData,
    })
    
    const result = await response.json()
    
    if (result.success) {
      console.log('[DEBUG] 视频上传成功，返回数据:', result);
      
      // 获取上传数据
      const uploadData = result.data;
      
      // 记录后端传来的状态
      console.log(`[DEBUG] 后端返回的状态信息: 上传回调=${uploadData.upload_callback_status}, 评估=${uploadData.assessment_status}, 报告ID=${uploadData.report_id || 'none'}`);
      
      // 保存报告ID（如果有）
      if (uploadData.report_id) {
        console.log(`[DEBUG] 获取到report_id: ${uploadData.report_id}`);
        assessmentStore.setReportId(uploadData.report_id);
      } else {
        console.log('[DEBUG] 返回数据中没有report_id，稍后将从report列表获取');
      }
      
      // 明确设置上传回调状态 - 检查多种可能的属性名
      const hasCallback = uploadData.upload_callback_status || 
                         uploadData.uploadCallbackStatus || 
                         uploadData.initial_status?.upload_callback || 
                         false;
      console.log(`[DEBUG] 设置上传回调状态: ${hasCallback}`);
      assessmentStore.setUploadCallbackComplete(hasCallback);
      
      // 明确设置评估状态 - 检查多种可能的属性名
      const isAssessmentComplete = uploadData.assessment_status || 
                                  uploadData.assessmentStatus || 
                                  uploadData.initial_status?.assessment || 
                                  false;
      console.log(`[DEBUG] 设置评估状态: ${isAssessmentComplete}`);
      assessmentStore.setAssessmentComplete(isAssessmentComplete);
      
      // 明确设置报告下载状态 - 检查多种可能的属性名
      const isReportDownloaded = uploadData.reportDownloaded || 
                               uploadData.report_downloaded || 
                               uploadData.initial_status?.downloaded || 
                               false;
      console.log(`[DEBUG] 设置报告下载状态: ${isReportDownloaded}`);
      assessmentStore.setReportDownloaded(isReportDownloaded);
      
      // 手动保存状态到localStorage
      console.log('[DEBUG] 主动调用saveVideoUploadState保存状态');
      const saveResult = assessmentStore.saveVideoUploadState();
      console.log('[DEBUG] 保存结果:', saveResult);
      
      // 延迟验证localStorage状态
      setTimeout(() => {
        try {
          const savedState = localStorage.getItem('video_upload_state');
          if (savedState) {
            const parsedState = JSON.parse(savedState);
            console.log('[DEBUG] 验证localStorage中保存的状态:', parsedState);
            console.log(`[DEBUG] localStorage状态验证: reportId=${parsedState.reportId}, 上传回调=${parsedState.uploadCallbackComplete}`);
            
            // 如果localStorage中的状态与期望的不符，尝试再次保存
            if ((uploadData.report_id && parsedState.reportId !== uploadData.report_id) || 
                parsedState.uploadCallbackComplete !== hasCallback) {
              console.warn('[DEBUG] 警告: localStorage中的状态与预期不符，再次尝试保存');
              assessmentStore.saveVideoUploadState();
            }
          } else {
            console.error('[DEBUG] 错误: localStorage中未找到video_upload_state');
            console.log('[DEBUG] 尝试再次保存状态');
            assessmentStore.saveVideoUploadState();
          }
        } catch (err) {
          console.error('[DEBUG] 读取localStorage状态失败:', err);
        }
      }, 500);  // 增加延迟确保有足够时间写入
      
      // 根据上传回调状态决定是否启动轮询
      if (uploadData.upload_callback_status === true) {
        console.log('[DEBUG] 上传回调已完成，启动视频评估状态轮询');
        // 启动主轮询
        assessmentStore.startMasterPolling();
      } else {
        console.log('[DEBUG] 上传回调未完成，启动状态轮询');
        // 启动状态轮询检查
        assessmentStore.startStatusPolling();
      }
      
      // 重置 UI 状态
      isProcessing.value = false;
      recordingComplete.value = true;
      completeMessage.value = result.message || '视频上传成功，您可以查看结果';
      
      // 设置视频评估数据
      assessmentStore.setVideoAssessmentData({
        url: uploadData.url,
        reportId: uploadData.report_id,
        uploadTime: new Date().toISOString(),
        status: 'processing'
      });
      
      // 显示上传成功通知
      const successNotification = document.createElement('div')
      successNotification.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2'
      successNotification.innerHTML = `
        <i class="fa-solid fa-check-circle"></i>
        <div>
          <div class="font-medium">视频上传成功</div>
          <div class="text-sm opacity-90">视频已成功上传到云端，正在分析中...</div>
        </div>
      `
      document.body.appendChild(successNotification)
      
      // 3秒后移除通知
      setTimeout(() => {
        successNotification.classList.add('animate-fade-out')
        setTimeout(() => {
          successNotification.remove()
        }, 500)
      }, 3000)
      
      // 发送上传完成事件，以便关闭视频评估界面
      emit('recording-complete')
    } else {
      console.error('[DEBUG] 视频上传失败:', result.message);
      throw new Error(result.message || '视频上传失败');
    }
  } catch (error) {
    console.error('视频上传失败:', error)
    hasError.value = true
    
    // 根据错误类型判断失败原因
    let errorType = 'general';
    if (error.message && error.message.includes('503')) {
      errorType = 'server_unavailable';
      errorMessage.value = '服务器暂时不可用，请稍后再次尝试重新上传';
    } else if (error.message && (error.message.includes('timeout') || error.message.includes('timed out'))) {
      errorType = 'timeout';
      errorMessage.value = '上传超时，请稍后再次尝试重新上传';
    } else if (error.message && (error.message.includes('network') || error.message.includes('disconnected'))) {
      errorType = 'network';
      errorMessage.value = '网络连接错误，请检查网络连接后再次尝试重新上传';
    } else {
      errorMessage.value = `视频上传失败: ${error.message}`;
    }
    
    isProcessing.value = false;
    // 使用适当的错误类型显示通知
    assessmentStore.showUploadFailureNotification(errorType);
  }
}

const retryCamera = () => {
  hasError.value = false
  errorMessage.value = ''
  initCamera()
}

const resetStates = (clearSavedVideo = false) => {
  hasError.value = false
  errorMessage.value = ''
  isRecording.value = false
  recordingComplete.value = false
  isProcessing.value = false
  
  // 只有在明确指定时才清除保存的视频
  if (clearSavedVideo) {
    savedVideoBlob.value = null
  }
}

const closeRecorder = () => {
  emit('recording-complete')
  emit('close')
}

const cleanup = () => {
  // 停止录制
  if (mediaRecorder.value && mediaRecorder.value.state !== 'inactive') {
    mediaRecorder.value.stop()
  }
  
  // 清除定时器
  if (timerInterval.value) {
    clearInterval(timerInterval.value)
    timerInterval.value = null
  }
  
  // 清除人脸检测定时器
  if (faceDetectionInterval.value) {
    clearInterval(faceDetectionInterval.value)
    faceDetectionInterval.value = null
  }
  
  // 停止视频流
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop())
    stream.value = null
  }
}

// 重试上传视频
const retryUpload = async () => {
  if (!savedVideoBlob.value) {
    console.error('没有保存的视频可以重新上传');
    return;
  }
  
  // 重置错误状态
  hasError.value = false;
  errorMessage.value = '';
  isProcessing.value = true;
  processingMessage.value = '正在重新上传视频...';
  
  try {
    // 从用户状态获取授权令牌
    let authToken = userStore.getAuthToken();
    
    // 如果没有token，使用默认开发测试token
    if (!authToken) {
      console.warn('未找到用户授权令牌，使用开发测试token');
      authToken = userStore.setDevelopmentToken();
    } else {
      // 确保token正确存储在userStore中
      userStore.setAuthToken(authToken);
    }
    
    console.log('授权令牌已存储:', authToken);
    
    // 获取保存的视频MIME类型
    const mimeType = savedVideoBlob.value.type || 'video/webm';
    const fileExtension = mimeType.includes('webm') ? 'webm' : 
                         mimeType.includes('mp4') ? 'mp4' : 'avi';
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', savedVideoBlob.value, `emotion_assessment.${fileExtension}`);
    
    // 使用七牛云上传接口
    const response = await fetch(getApiUrl('upload-video'), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      body: formData,
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('[DEBUG] 视频上传成功，返回数据:', result);
      
      // 获取上传数据
      const uploadData = result.data;
      
      // 记录后端传来的状态
      console.log(`[DEBUG] 后端返回的状态信息: 上传回调=${uploadData.upload_callback_status}, 评估=${uploadData.assessment_status}, 报告ID=${uploadData.report_id || 'none'}`);
      
      // 保存报告ID（如果有）
      if (uploadData.report_id) {
        console.log(`[DEBUG] 获取到report_id: ${uploadData.report_id}`);
        assessmentStore.setReportId(uploadData.report_id);
      } else {
        console.log('[DEBUG] 返回数据中没有report_id，稍后将从report列表获取');
      }
      
      // 明确设置上传回调状态 - 检查多种可能的属性名
      const hasCallback = uploadData.upload_callback_status || 
                         uploadData.uploadCallbackStatus || 
                         uploadData.initial_status?.upload_callback || 
                         false;
      console.log(`[DEBUG] 设置上传回调状态: ${hasCallback}`);
      assessmentStore.setUploadCallbackComplete(hasCallback);
      
      // 明确设置评估状态 - 检查多种可能的属性名
      const isAssessmentComplete = uploadData.assessment_status || 
                                  uploadData.assessmentStatus || 
                                  uploadData.initial_status?.assessment || 
                                  false;
      console.log(`[DEBUG] 设置评估状态: ${isAssessmentComplete}`);
      assessmentStore.setAssessmentComplete(isAssessmentComplete);
      
      // 明确设置报告下载状态 - 检查多种可能的属性名
      const isReportDownloaded = uploadData.reportDownloaded || 
                               uploadData.report_downloaded || 
                               uploadData.initial_status?.downloaded || 
                               false;
      console.log(`[DEBUG] 设置报告下载状态: ${isReportDownloaded}`);
      assessmentStore.setReportDownloaded(isReportDownloaded);
      
      // 手动保存状态到localStorage
      console.log('[DEBUG] 主动调用saveVideoUploadState保存状态');
      const saveResult = assessmentStore.saveVideoUploadState();
      console.log('[DEBUG] 保存结果:', saveResult);
      
      // 延迟验证localStorage状态
      setTimeout(() => {
        try {
          const savedState = localStorage.getItem('video_upload_state');
          if (savedState) {
            const parsedState = JSON.parse(savedState);
            console.log('[DEBUG] 验证localStorage中保存的状态:', parsedState);
            console.log(`[DEBUG] localStorage状态验证: reportId=${parsedState.reportId}, 上传回调=${parsedState.uploadCallbackComplete}`);
            
            // 如果localStorage中的状态与期望的不符，尝试再次保存
            if ((uploadData.report_id && parsedState.reportId !== uploadData.report_id) || 
                parsedState.uploadCallbackComplete !== hasCallback) {
              console.warn('[DEBUG] 警告: localStorage中的状态与预期不符，再次尝试保存');
              assessmentStore.saveVideoUploadState();
            }
          } else {
            console.error('[DEBUG] 错误: localStorage中未找到video_upload_state');
            console.log('[DEBUG] 尝试再次保存状态');
            assessmentStore.saveVideoUploadState();
          }
        } catch (err) {
          console.error('[DEBUG] 读取localStorage状态失败:', err);
        }
      }, 500);  // 增加延迟确保有足够时间写入
      
      // 根据上传回调状态决定是否启动轮询
      if (uploadData.upload_callback_status === true) {
        console.log('[DEBUG] 上传回调已完成，启动视频评估状态轮询');
        // 启动主轮询
        assessmentStore.startMasterPolling();
      } else {
        console.log('[DEBUG] 上传回调未完成，启动状态轮询');
        // 启动状态轮询检查
        assessmentStore.startStatusPolling();
      }
      
      // 重置 UI 状态
      isProcessing.value = false;
      recordingComplete.value = true;
      completeMessage.value = result.message || '视频上传成功，您可以查看结果';
      
      // 设置视频评估数据
      assessmentStore.setVideoAssessmentData({
        url: uploadData.url,
        reportId: uploadData.report_id,
        uploadTime: new Date().toISOString(),
        status: 'processing'
      });
      
      // 显示上传成功通知
      const successNotification = document.createElement('div');
      successNotification.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2';
      successNotification.innerHTML = `
        <i class="fa-solid fa-check-circle"></i>
        <div>
          <div class="font-medium">视频上传成功</div>
          <div class="text-sm opacity-90">视频已成功上传到云端，正在分析中...</div>
        </div>
      `;
      document.body.appendChild(successNotification);
      
      // 3秒后移除通知
      setTimeout(() => {
        successNotification.classList.add('animate-fade-out');
        setTimeout(() => {
          successNotification.remove();
        }, 500);
      }, 3000);
      
      // 发送上传完成事件，以便关闭视频评估界面
      emit('recording-complete');
    } else {
      throw new Error(result.message || '视频重新上传失败');
    }
  } catch (error) {
    console.error('视频重新上传失败:', error);
    hasError.value = true;
    errorMessage.value = `视频重新上传失败: ${error.message}`;
    isProcessing.value = false;
  }
}

// 生命周期钩子
onMounted(() => {
  // 初始化摄像头
  initCamera()
  
  // 加载localStorage中保存的视频上传状态
  assessmentStore.loadVideoUploadState()
  
  // 检查是否有未完成的评估
  if (assessmentStore.videoUploadEtag && assessmentStore.uploadCallbackComplete) {
    console.log('检测到未完成的视频评估任务')
    // 如果上传回调已完成但评估尚未完成，自动启动状态轮询
    if (assessmentStore.uploadCallbackComplete && !assessmentStore.assessmentComplete) {
      console.log('启动未完成视频的状态轮询')
      assessmentStore.startStatusPolling(assessmentStore.videoUploadEtag)
    }
  }
})

onUnmounted(() => {
  cleanup()
})
</script>

<style scoped>
.video-recorder-container {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background-color: #000;
  border-radius: 12px;
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
}

.video-preview {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.face-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.recording-indicator {
  position: absolute;
  top: 20px;
  left: 20px;
  display: flex;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.6);
  padding: 8px 16px;
  border-radius: 20px;
  z-index: 10;
}

.recording-dot {
  width: 12px;
  height: 12px;
  background-color: #FF5252;
  border-radius: 50%;
  margin-right: 8px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0% { opacity: 0.4; }
  50% { opacity: 1; }
  100% { opacity: 0.4; }
}

.recording-indicator span {
  color: white;
  font-size: 14px;
  font-weight: 500;
}

.close-button {
  position: absolute;
  top: 15px;
  right: 15px;
  width: 36px;
  height: 36px;
  background-color: rgba(0, 0, 0, 0.6);
  border: none;
  border-radius: 50%;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s;
  z-index: 10;
}

.close-button:hover {
  background-color: rgba(0, 0, 0, 0.8);
}

/* 指导信息样式 */
.guidance-overlay, .processing-overlay, .complete-overlay, .error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
}

.guidance-content, .processing-content, .complete-content, .error-content {
  max-width: 90%;
  width: 400px;
  background-color: #fff;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.dark .guidance-content, 
.dark .processing-content, 
.dark .complete-content, 
.dark .error-content {
  background-color: #2a2a2a;
  color: #e0e0e0;
}

.icon-container {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background-color: #e0f2f1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dark .icon-container {
  background-color: #263238;
}

.icon-container i {
  font-size: 28px;
  color: #009688;
}

.dark .icon-container i {
  color: #4db6ac;
}

.icon-container.success {
  background-color: #e8f5e9;
}

.dark .icon-container.success {
  background-color: #1b5e20;
}

.icon-container.success i {
  color: #4caf50;
}

.dark .icon-container.success i {
  color: #81c784;
}

.icon-container.error {
  background-color: #ffebee;
}

.dark .icon-container.error {
  background-color: #b71c1c;
}

.icon-container.error i {
  color: #f44336;
}

.dark .icon-container.error i {
  color: #e57373;
}

.guidance-content h3, .complete-content h3, .error-content h3 {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.dark .guidance-content h3, 
.dark .complete-content h3, 
.dark .error-content h3 {
  color: #f0f0f0;
}

.guidance-content p, .complete-content p, .error-content p {
  margin: 8px 0;
  color: #666;
  font-size: 14px;
  line-height: 1.5;
}

.dark .guidance-content p, 
.dark .complete-content p, 
.dark .error-content p {
  color: #bdbdbd;
}

.start-recording-btn, .complete-btn, .retry-btn {
  margin-top: 24px;
  padding: 12px 24px;
  border: none;
  border-radius: 24px;
  background-color: #009688;
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.start-recording-btn:hover, .complete-btn:hover, .retry-btn:hover {
  background-color: #00796b;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.start-recording-btn:disabled {
  background-color: #e0e0e0;
  color: #9e9e9e;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.dark .start-recording-btn:disabled {
  background-color: #424242;
  color: #757575;
}

.complete-btn {
  background-color: #4caf50;
}

.complete-btn:hover {
  background-color: #388e3c;
}

.retry-btn {
  background-color: #f44336;
}

.retry-btn:hover {
  background-color: #d32f2f;
}

.error-buttons {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 24px;
}

.retry-btn.secondary {
  background-color: #607D8B;
}

.retry-btn.secondary:hover {
  background-color: #455A64;
}

/* 处理中动画 */
.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  border: 4px solid rgba(0, 150, 136, 0.2);
  border-top-color: #009688;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.processing-content p {
  color: #666;
  font-size: 16px;
}

.dark .processing-content p {
  color: #bdbdbd;
}

.camera-selector {
  position: absolute;
  top: 15px;
  left: 15px;
  z-index: 10;
  display: flex;
  gap: 10px;
  align-items: center;
}

.camera-dropdown {
  padding: 8px 12px;
  border-radius: 20px;
  border: none;
  background-color: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 14px;
  min-width: 180px;
  cursor: pointer;
}

.recording-dot.paused {
  animation: none;
  opacity: 1;
  background-color: #FFC107;
}

.face-timer-progress {
  width: 100%;
  height: 8px;
  background-color: rgba(0, 0, 0, 0.1);
  border-radius: 4px;
  margin: 16px 0;
  overflow: hidden;
}

.face-timer-bar {
  height: 100%;
  background-color: #4CAF50;
  border-radius: 4px;
  transition: width 0.3s;
}

/* 添加调试信息的样式 */
.debug-info {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 10px;
  border-radius: 5px;
  font-size: 12px;
  z-index: 100;
  text-align: left;
}
</style>
