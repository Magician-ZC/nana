<template>
  <div class="assessment-buttons-container">
    <!-- 情绪评估按钮 -->
    <button 
      @click="openEmotionalAssessment" 
      class="assessment-btn emotional-btn"
      title="情绪评估"
    >
      情绪评估
    </button>
    
    <!-- 心理评估按钮 -->
    <button 
      @click="openPsychologicalAssessment" 
      class="assessment-btn psychological-btn"
      :class="{ 'disabled': !psychAssessmentReady }"
      :title="psychAssessmentReady ? '心理评估' : '需要20轮有效对话'"
    >
      {{ psychAssessmentReady ? '心理评估（评估完成）' : '心理评估（评估中）' }}
    </button>
    
    <!-- 情绪评估上传弹窗 -->
    <div class="modal" v-if="showEmotionalModal">
      <div class="modal-content">
        <span class="close-btn" @click="showEmotionalModal = false">&times;</span>
        <h2>情绪评估</h2>
        <p>请上传检测报告文件进行情绪评估</p>
        <p class="supported-formats">支持格式：PDF、图片(PNG/JPG)、TXT文本</p>
        <input type="file" ref="fileInput" accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx" @change="handleFileUpload" />
        <div class="upload-status" v-if="uploadStatus">{{ uploadStatus }}</div>
        <div class="button-group">
          <button @click="uploadFile" :disabled="!selectedFile || isUploading" class="upload-btn">
            {{ isUploading ? '上传中...' : '上传' }}
          </button>
          <button @click="parseFile" :disabled="!selectedFile || isUploading" class="parse-btn">
            查看解析文本
          </button>
        </div>
      </div>
    </div>
    
    <!-- 解析结果弹窗 -->
    <div class="modal" v-if="showParseModal">
      <div class="modal-content parse-content">
        <span class="close-btn" @click="showParseModal = false">&times;</span>
        <h2>文档解析结果</h2>
        <div class="parse-result-container">
          <pre class="parse-result">{{ parseResult }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const psychAssessmentReady = ref(false);
const showEmotionalModal = ref(false);
const showParseModal = ref(false);
const fileInput = ref(null);
const selectedFile = ref(null);
const isUploading = ref(false);
const uploadStatus = ref('');
const parseResult = ref('');

// 打开情绪评估弹窗
const openEmotionalAssessment = () => {
  showEmotionalModal.value = true;
};

// 打开心理评估
const openPsychologicalAssessment = async () => {
  if (!psychAssessmentReady.value) {
    return; // 如果评估未完成，按钮不可点击
  }
  
  try {
    // 显示加载状态
    uploadStatus.value = '正在生成心理评估报告...';
    
    // 发送请求以生成和下载报告
    const response = await fetch('http://localhost:8666/api/psychological_assessment', {
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
    
    const response = await fetch('http://localhost:8666/api/emotional_assessment', {
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
    
    const response = await fetch('http://localhost:8666/api/parse_document', {
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
    const response = await fetch('http://localhost:8666/api/assessment_status');
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
  // 初始检查
  checkAssessmentStatus();
  
  // 每5分钟检查一次
  checkInterval = setInterval(checkAssessmentStatus, 5 * 60 * 1000);
});

onUnmounted(() => {
  // 清理定时器
  if (checkInterval) {
    clearInterval(checkInterval);
  }
});
</script>

<style scoped>
.assessment-buttons-container {
  position: absolute;
  top: 20px;
  left: 60px;
  z-index: 100;
  display: flex;
  gap: 10px;
}

.assessment-btn {
  padding: 5px 10px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #ccc;
  background-color: white;
  color: #333;
}

:global(.dark) .assessment-btn {
  background-color: #333;
  color: #f0f0f0;
  border-color: #555;
}

.assessment-btn.disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 弹窗样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  min-width: 300px;
  position: relative;
}

:global(.dark) .modal-content {
  background-color: #333;
  color: #f0f0f0;
}

.close-btn {
  position: absolute;
  right: 10px;
  top: 10px;
  font-size: 20px;
  cursor: pointer;
}

.upload-btn {
  margin-top: 15px;
  padding: 8px 16px;
  background-color: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.upload-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.upload-status {
  margin: 10px 0;
  color: #ff6b6b;
}

:global(.dark) .upload-status {
  color: #ffaaaa;
}

.supported-formats {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
}

:global(.dark) .supported-formats {
  color: #aaa;
}

.parse-btn {
  padding: 8px 16px;
  background-color: #2196F3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.parse-btn:disabled {
  background-color: #cccccc;
  cursor: not-allowed;
}

.parse-content {
  max-width: 90%;
  width: 900px;
  max-height: 80vh;
  overflow-y: hidden;
  display: flex;
  flex-direction: column;
}

.parse-result-container {
  flex: 1;
  max-height: calc(80vh - 80px);
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 10px;
  margin-top: 10px;
  background-color: #f9f9f9;
}

.parse-result {
  white-space: pre-wrap;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
}

:global(.dark) .parse-result-container {
  background-color: #333;
  border-color: #444;
  color: #f0f0f0;
}

:global(.dark) .parse-btn {
  background-color: #0d47a1;
}
</style> 