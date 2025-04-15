<!-- 权限测试组件 -->
<template>
  <div class="permission-test">
    <h2>摄像头和麦克风权限测试</h2>
    
    <div class="controls">
      <button 
        @click="requestCameraAccess" 
        :disabled="cameraActive"
        class="test-btn camera-btn"
      >
        测试摄像头
      </button>
      
      <button 
        @click="requestMicrophoneAccess" 
        :disabled="microphoneActive"
        class="test-btn mic-btn"
      >
        测试麦克风
      </button>
      
      <button 
        @click="requestBothAccess" 
        :disabled="cameraActive && microphoneActive"
        class="test-btn both-btn"
      >
        同时测试
      </button>
      
      <button 
        v-if="cameraActive || microphoneActive"
        @click="stopAll" 
        class="test-btn stop-btn"
      >
        停止所有
      </button>
    </div>
    
    <div class="status-container">
      <div class="status">
        <div class="status-label">摄像头:</div>
        <div class="status-value" :class="cameraStatus.class">
          {{ cameraStatus.text }}
        </div>
      </div>
      
      <div class="status">
        <div class="status-label">麦克风:</div>
        <div class="status-value" :class="microphoneStatus.class">
          {{ microphoneStatus.text }}
        </div>
      </div>
    </div>
    
    <!-- 摄像头预览 -->
    <div v-if="cameraActive" class="video-container">
      <video ref="videoRef" autoplay playsinline></video>
    </div>
    
    <!-- 音频可视化 -->
    <div v-if="microphoneActive" class="audio-container">
      <canvas ref="audioCanvasRef" width="300" height="100"></canvas>
    </div>
    
    <div v-if="errorMessage" class="error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';

// 状态变量
const cameraActive = ref(false);
const microphoneActive = ref(false);
const errorMessage = ref('');
const videoRef = ref(null);
const audioCanvasRef = ref(null);

// 媒体流和处理器
let videoStream = null;
let audioStream = null;
let audioContext = null;
let analyser = null;
let animationFrameId = null;

// 访问状态
const cameraStatus = computed(() => {
  if (cameraActive.value) {
    return { text: '已授权并活跃', class: 'status-active' };
  } else if (errorMessage.value.includes('摄像头')) {
    return { text: '访问失败', class: 'status-error' };
  } else {
    return { text: '未请求', class: 'status-inactive' };
  }
});

const microphoneStatus = computed(() => {
  if (microphoneActive.value) {
    return { text: '已授权并活跃', class: 'status-active' };
  } else if (errorMessage.value.includes('麦克风')) {
    return { text: '访问失败', class: 'status-error' };
  } else {
    return { text: '未请求', class: 'status-inactive' };
  }
});

// 请求摄像头权限
async function requestCameraAccess() {
  try {
    errorMessage.value = '';
    videoStream = await navigator.mediaDevices.getUserMedia({ 
      video: true 
    });
    
    if (videoRef.value) {
      videoRef.value.srcObject = videoStream;
    }
    
    cameraActive.value = true;
  } catch (err) {
    console.error('摄像头访问失败:', err);
    errorMessage.value = `摄像头访问失败: ${err.message}`;
  }
}

// 请求麦克风权限
async function requestMicrophoneAccess() {
  try {
    errorMessage.value = '';
    audioStream = await navigator.mediaDevices.getUserMedia({ 
      audio: true 
    });
    
    setupAudioVisualization(audioStream);
    microphoneActive.value = true;
  } catch (err) {
    console.error('麦克风访问失败:', err);
    errorMessage.value = `麦克风访问失败: ${err.message}`;
  }
}

// 同时请求摄像头和麦克风权限
async function requestBothAccess() {
  try {
    errorMessage.value = '';
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: true,
      audio: true 
    });
    
    // 分离音视频轨道
    const videoTracks = stream.getVideoTracks();
    const audioTracks = stream.getAudioTracks();
    
    if (videoTracks.length > 0) {
      videoStream = new MediaStream([videoTracks[0]]);
      if (videoRef.value) {
        videoRef.value.srcObject = videoStream;
      }
      cameraActive.value = true;
    }
    
    if (audioTracks.length > 0) {
      audioStream = new MediaStream([audioTracks[0]]);
      setupAudioVisualization(audioStream);
      microphoneActive.value = true;
    }
  } catch (err) {
    console.error('摄像头和麦克风访问失败:', err);
    errorMessage.value = `摄像头和麦克风访问失败: ${err.message}`;
  }
}

// 停止所有媒体流
function stopAll() {
  if (videoStream) {
    videoStream.getTracks().forEach(track => track.stop());
    videoStream = null;
    if (videoRef.value) {
      videoRef.value.srcObject = null;
    }
    cameraActive.value = false;
  }
  
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop());
    audioStream = null;
    microphoneActive.value = false;
  }
  
  if (audioContext) {
    cancelAnimationFrame(animationFrameId);
    audioContext = null;
    analyser = null;
  }
  
  errorMessage.value = '';
}

// 设置音频可视化
function setupAudioVisualization(stream) {
  if (!audioCanvasRef.value) return;
  
  // 创建音频上下文
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioContext.createMediaStreamSource(stream);
  analyser = audioContext.createAnalyser();
  
  // 设置分析器参数
  analyser.fftSize = 256;
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  
  // 连接节点
  source.connect(analyser);
  
  // 获取画布上下文
  const canvasCtx = audioCanvasRef.value.getContext('2d');
  
  // 创建动画循环
  function draw() {
    animationFrameId = requestAnimationFrame(draw);
    
    // 获取频率数据
    analyser.getByteFrequencyData(dataArray);
    
    // 清空画布
    canvasCtx.fillStyle = 'rgb(20, 20, 30)';
    canvasCtx.fillRect(0, 0, audioCanvasRef.value.width, audioCanvasRef.value.height);
    
    // 计算条形宽度
    const barWidth = (audioCanvasRef.value.width / bufferLength) * 2.5;
    let barHeight;
    let x = 0;
    
    // 绘制频谱
    for (let i = 0; i < bufferLength; i++) {
      barHeight = dataArray[i] / 2;
      
      // 根据频率高度确定颜色
      const h = 200 + (barHeight / 2);
      const s = 90;
      const l = 50;
      canvasCtx.fillStyle = `hsl(${h}, ${s}%, ${l}%)`;
      
      canvasCtx.fillRect(x, audioCanvasRef.value.height - barHeight, barWidth, barHeight);
      x += barWidth + 1;
    }
  }
  
  draw();
}

// 清理资源
onUnmounted(() => {
  stopAll();
});
</script>

<style scoped>
.permission-test {
  margin: 20px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  max-width: 600px;
  margin: 20px auto;
}

.permission-test h2 {
  margin-top: 0;
  margin-bottom: 20px;
  color: #333;
  text-align: center;
}

.controls {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  flex-wrap: wrap;
  justify-content: center;
}

.test-btn {
  padding: 10px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-weight: bold;
  transition: all 0.3s ease;
}

.test-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.camera-btn {
  background-color: #4caf50;
  color: white;
}

.mic-btn {
  background-color: #2196f3;
  color: white;
}

.both-btn {
  background-color: #9c27b0;
  color: white;
}

.stop-btn {
  background-color: #f44336;
  color: white;
}

.status-container {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-around;
}

.status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-label {
  font-weight: bold;
}

.status-value {
  padding: 5px 10px;
  border-radius: 20px;
  font-size: 14px;
}

.status-active {
  background-color: #4caf50;
  color: white;
}

.status-inactive {
  background-color: #9e9e9e;
  color: white;
}

.status-error {
  background-color: #f44336;
  color: white;
}

.video-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.video-container video {
  max-width: 100%;
  border-radius: 8px;
  border: 2px solid #2196f3;
}

.audio-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.audio-container canvas {
  width: 100%;
  border-radius: 8px;
  border: 2px solid #9c27b0;
}

.error-message {
  margin-top: 20px;
  padding: 10px;
  background-color: #ffebee;
  color: #c62828;
  border-radius: 5px;
  border-left: 4px solid #f44336;
}

/* 暗色模式支持 */
:deep(.dark) .permission-test {
  background-color: #1e1e2d;
  color: #e0e0e0;
}

:deep(.dark) .permission-test h2 {
  color: #e0e0e0;
}
</style> 