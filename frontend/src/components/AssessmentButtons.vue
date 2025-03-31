<template>
  <div class="assessment-container">
    <!-- 情绪评估按钮，只在桌面端显示 -->
    <button 
      v-if="!isMobile" 
      @click="openEmotionalAssessment" 
      class="assessment-btn px-3 py-2 rounded-lg bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-all duration-200 font-medium border border-neutral-200 dark:border-neutral-700 shadow-sm flex items-center"
      title="情绪评估"
    >
      <i class="fa-solid fa-face-smile mr-2 text-blue-500"></i>
      情绪评估
    </button>
    
    <!-- 心理评估按钮，所有端都显示 -->
    <button 
      @click="openPsychologicalAssessment" 
      class="assessment-btn px-3 py-2 rounded-lg bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-all duration-200 font-medium border border-neutral-200 dark:border-neutral-700 shadow-sm flex items-center"
      :class="{ 'opacity-60 cursor-not-allowed': !psychAssessmentReady }"
      :title="psychAssessmentReady ? '心理评估' : '需要20轮有效对话'"
    >
      <i class="fa-solid fa-brain mr-2 text-purple-500"></i>
      {{ psychAssessmentReady ? '心理评估' : '评估中' }}
      <span v-if="psychAssessmentReady" class="ml-1 text-xs px-1.5 py-0.5 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-300 rounded-full">就绪</span>
    </button>
    
    <!-- 情绪评估上传弹窗 -->
    <div v-if="showEmotionalModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-50 flex items-center justify-center transition-all duration-300 ease-in-out" @click="showEmotionalModal = false">
      <div class="w-full max-w-xl max-h-[90vh] overflow-y-auto bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in" @click.stop>
        <!-- 顶部标题栏 -->
        <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
          <h3 class="text-xl font-semibold text-neutral-800 dark:text-white">情绪评估</h3>
          <button 
            @click="showEmotionalModal = false" 
            class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
          >
            <span class="text-lg">&times;</span>
          </button>
        </div>
        
        <!-- 内容区域 -->
        <div class="p-6 space-y-4">
          <p class="text-neutral-700 dark:text-neutral-300">请上传检测报告文件进行情绪评估分析</p>
          <p class="text-sm text-neutral-500 dark:text-neutral-400">支持格式：PDF、图片(PNG/JPG)、TXT文本</p>
          
          <!-- 文件上传区 -->
          <div class="mt-4 p-4 border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg text-center">
            <input type="file" ref="fileInput" accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx" @change="handleFileUpload" class="hidden" id="file-upload"/>
            <label for="file-upload" class="block w-full cursor-pointer">
              <div class="flex flex-col items-center justify-center py-4">
                <svg class="mx-auto h-12 w-12 text-neutral-400" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                  <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
                <p class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                  {{ selectedFile ? selectedFile.name : '点击选择文件或拖拽文件到此区域' }}
                </p>
              </div>
            </label>
          </div>
          
          <!-- 状态提示 -->
          <div v-if="uploadStatus" class="mt-3 text-center text-sm p-2 rounded-md" :class="isUploading ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'">
            {{ uploadStatus }}
          </div>
        </div>
        
        <!-- 底部按钮 -->
        <div class="flex items-center justify-end p-5 border-t border-neutral-200 dark:border-neutral-700 gap-3">
          <button 
            @click="showEmotionalModal = false" 
            class="px-4 py-2 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all duration-200 font-medium"
          >
            取消
          </button>
          <button 
            @click="parseFile" 
            :disabled="!selectedFile || isUploading"
            class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-all duration-200 font-medium flex items-center disabled:opacity-50 disabled:pointer-events-none"
          >
            <i class="fa-solid fa-file-lines mr-2"></i>
            查看解析文本
          </button>
          <button 
            @click="uploadFile" 
            :disabled="!selectedFile || isUploading"
            class="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white transition-all duration-200 font-medium flex items-center disabled:opacity-50 disabled:pointer-events-none"
          >
            <i class="fa-solid fa-upload mr-2"></i>
            {{ isUploading ? '上传中...' : '上传分析' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- 解析结果弹窗 -->
    <div v-if="showParseModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-50 flex items-center justify-center transition-all duration-300 ease-in-out" @click="showParseModal = false">
      <div class="w-full max-w-4xl max-h-[90vh] overflow-hidden bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in" @click.stop>
        <!-- 顶部标题栏 -->
        <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
          <h3 class="text-xl font-semibold text-neutral-800 dark:text-white">文档解析结果</h3>
          <button 
            @click="showParseModal = false" 
            class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
          >
            <span class="text-lg">&times;</span>
          </button>
        </div>
        
        <!-- 解析内容区域 -->
        <div class="p-4 max-h-[calc(90vh-120px)] overflow-y-auto">
          <div class="bg-neutral-50 dark:bg-neutral-900 rounded-lg p-4 font-mono text-sm whitespace-pre-wrap border border-neutral-200 dark:border-neutral-700">
            {{ parseResult }}
          </div>
        </div>
        
        <!-- 底部按钮 -->
        <div class="flex items-center justify-end p-5 border-t border-neutral-200 dark:border-neutral-700 gap-3">
          <button 
            @click="showParseModal = false" 
            class="px-4 py-2 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all duration-200 font-medium"
          >
            关闭
          </button>
          <button 
            @click="uploadFile" 
            :disabled="isUploading"
            class="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white transition-all duration-200 font-medium flex items-center disabled:opacity-50 disabled:pointer-events-none"
          >
            <i class="fa-solid fa-upload mr-2"></i>
            {{ isUploading ? '上传中...' : '直接上传分析' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { getApiBaseUrl } from '../stores/chat';

const psychAssessmentReady = ref(false);
const showEmotionalModal = ref(false);
const showParseModal = ref(false);
const fileInput = ref(null);
const selectedFile = ref(null);
const isUploading = ref(false);
const uploadStatus = ref('');
const parseResult = ref('');
// 初始值设为true，确保首次加载时情绪评估按钮不显示在移动端
const isMobile = ref(window.innerWidth <= 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent));

// 打开情绪评估弹窗
const openEmotionalAssessment = () => {
  showEmotionalModal.value = true;
};

// 检测是否为移动设备
const checkMobileDevice = () => {
  try {
    isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
    console.log("情绪评估按钮 - 移动设备检测:", isMobile.value ? "是移动设备" : "非移动设备");
  } catch (error) {
    console.error("移动设备检测出错:", error);
    // 出错时默认为移动设备，确保按钮不显示
    isMobile.value = true;
  }
};

// 将函数引用保存到函数本身，方便移除监听器
checkMobileDevice.handler = checkMobileDevice;

// 打开心理评估
const openPsychologicalAssessment = async () => {
  if (!psychAssessmentReady.value) {
    return; // 如果评估未完成，按钮不可点击
  }
  
  try {
    // 显示加载状态
    uploadStatus.value = '正在生成心理评估报告...';
    
    // 发送请求以生成和下载报告
    const response = await fetch(`${getApiBaseUrl()}/psychological_assessment`, {
      method: 'GET',
    });
    
    if (!response.ok) {
      throw new Error('生成报告失败');
    }
    
    // 获取二进制数据
    const pdfBlob = await response.blob();
    
    // 创建下载链接
    const url = window.URL.createObjectURL(pdfBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '心理测评报告.pdf';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    uploadStatus.value = '';
  } catch (error) {
    console.error('下载心理评估报告失败:', error);
    uploadStatus.value = '下载报告失败，请重试';
  }
};

// 监听文件选择
const handleFileUpload = (event) => {
  selectedFile.value = event.target.files[0];
  uploadStatus.value = '';
  // 清空之前的解析结果
  parseResult.value = '';
};

// 上传文件进行情绪评估
const uploadFile = async () => {
  if (!selectedFile.value) {
    uploadStatus.value = '请先选择文件';
    return;
  }
  
  const formData = new FormData();
  formData.append('file', selectedFile.value);
  
  try {
    isUploading.value = true;
    uploadStatus.value = '上传中...';
    
    const response = await fetch(`${getApiBaseUrl()}/emotional_assessment`, {
      method: 'POST',
      body: formData,
    });
    
    const result = await response.json();
    
    if (result.success) {
      uploadStatus.value = '上传成功，文件已处理';
      // 清空选择的文件
      fileInput.value.value = '';
      selectedFile.value = null;
      // 2秒后关闭弹窗
      setTimeout(() => {
        showEmotionalModal.value = false;
        uploadStatus.value = '';
      }, 2000);
    } else {
      uploadStatus.value = result.message || '上传失败，请重试';
    }
  } catch (error) {
    console.error('上传文件失败:', error);
    uploadStatus.value = '上传失败，请重试';
  } finally {
    isUploading.value = false;
  }
};

// 解析文件并查看原始文本
const parseFile = async () => {
  if (!selectedFile.value) {
    uploadStatus.value = '请先选择文件';
    return;
  }
  
  const formData = new FormData();
  formData.append('file', selectedFile.value);
  
  try {
    isUploading.value = true;
    uploadStatus.value = '解析中...';
    
    const response = await fetch(`${getApiBaseUrl()}/parse_document`, {
      method: 'POST',
      body: formData,
    });
    
    const result = await response.json();
    
    if (result.success) {
      parseResult.value = result.text;
      showParseModal.value = true;
      uploadStatus.value = '';
    } else {
      uploadStatus.value = result.message || '解析失败，请重试';
    }
  } catch (error) {
    console.error('文件解析失败:', error);
    uploadStatus.value = '解析失败，请重试';
  } finally {
    isUploading.value = false;
  }
};

// 获取对话轮数和评估状态
const checkAssessmentStatus = async () => {
  try {
    const response = await fetch(`${getApiBaseUrl()}/assessment_status`);
    const data = await response.json();
    
    if (data.success) {
      psychAssessmentReady.value = data.assessment_ready;
    }
  } catch (error) {
    console.error('获取评估状态失败:', error);
  }
};

// 设置定时检查
let checkInterval = null;

onMounted(() => {
  try {
    // 立即检测移动设备
    checkMobileDevice();
    
    // 监听窗口大小变化
    window.addEventListener('resize', checkMobileDevice.handler);
    
    // 每5分钟检查一次
    checkInterval = setInterval(checkAssessmentStatus, 5 * 60 * 1000);
    
    console.log("情绪评估按钮组件已挂载");
  } catch (error) {
    console.error("情绪评估按钮挂载时出错:", error);
  }
});

onBeforeUnmount(() => {
  try {
    // 确保清理所有事件监听器
    if (checkInterval) {
      clearInterval(checkInterval);
    }
    window.removeEventListener('resize', checkMobileDevice.handler);
    console.log("情绪评估按钮组件卸载前清理完成");
  } catch (error) {
    console.error("情绪评估按钮清理时出错:", error);
  }
});
</script>

<style scoped>
.assessment-container {
  position: fixed;
  bottom: 30px;
  left: 25px;
  display: flex;
  flex-direction: column;
  gap: 15px;
  z-index: 100;
}

/* 添加移动端样式，修改位置 */
@media (max-width: 768px) {
  .assessment-container {
    bottom: 85px; /* 确保在输入区域上方 */
    left: 15px;
    gap: 10px;
  }
  
  .assessment-btn {
    transform: scale(0.9);
  }
}

/* 淡入动画 */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}
</style> 