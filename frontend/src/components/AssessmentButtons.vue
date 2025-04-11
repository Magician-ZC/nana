<template>
  <div>
    <!-- 评估按钮组 -->
    <div class="fixed top-5 left-16 z-50 flex gap-3">
      <button 
        @click="openEmotionalAssessment" 
        class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 shadow-md hover:shadow-lg transition-all duration-200 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700"
        :class="{ 'opacity-60 cursor-not-allowed': processingAssessment }"
        :title="processingAssessment ? '情绪评估分析中，请稍候' : '情绪评估'"
      >
        <i class="fa-solid fa-heart-pulse text-rose-500 dark:text-rose-400"></i>
        <span>情绪评估</span>
        <span v-if="assessmentStore.assessmentComplete" class="ml-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded-full">
          <i class="fa-solid fa-check"></i>
        </span>
      </button>
      
      <!-- 视频评估按钮 -->
      <button 
        @click="openVideoAssessment" 
        class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 shadow-md hover:shadow-lg transition-all duration-200 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700"
        :class="{ 'opacity-60 cursor-not-allowed': assessmentStore.uploadCallbackComplete }"
        :title="assessmentStore.uploadCallbackComplete ? '视频已上传处理中' : '视频评估'"
      >
        <i class="fa-solid fa-video text-blue-500 dark:text-blue-400"></i>
        <span>视频评估</span>
        <span v-if="assessmentStore.uploadCallbackComplete" class="ml-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded-full">
          <i class="fa-solid fa-check"></i>
        </span>
      </button>
      
      <!-- 测试上传按钮 -->
      <button 
        @click="uploadTestVideo" 
        class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 shadow-md hover:shadow-lg transition-all duration-200 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700"
        :class="{ 'opacity-60 cursor-not-allowed': assessmentStore.uploadCallbackComplete }"
        :title="assessmentStore.uploadCallbackComplete ? '视频已上传处理中' : '测试视频上传'"
      >
        <i class="fa-solid fa-vial text-purple-500 dark:text-purple-400"></i>
        <span>测试上传</span>
      </button>
      
      <button 
        @click="openPsychologicalAssessment" 
        class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 shadow-md hover:shadow-lg transition-all duration-200 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-700"
        :class="{ 'opacity-60 cursor-not-allowed': !psychAssessmentReady }"
        :title="psychAssessmentReady ? '心理评估' : '需要20轮有效对话'"
      >
        <i class="fa-solid fa-brain text-indigo-500 dark:text-indigo-400"></i>
        <span>{{ psychAssessmentReady ? '心理评估' : '心理评估 (进行中)' }}</span>
        <span v-if="psychAssessmentReady" class="ml-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded-full">完成</span>
      </button>
    </div>
    
    <!-- 情绪评估弹窗 -->
    <div v-if="showEmotionalModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-[1100] flex items-center justify-center transition-all duration-300 ease-in-out">
      <div class="w-full max-w-xl bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in">
        <!-- 顶部标题栏 -->
        <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
          <h3 class="text-xl font-semibold text-neutral-800 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-heart-pulse text-rose-500"></i>
            情绪评估
          </h3>
          <button 
            @click="showEmotionalModal = false" 
            class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        
        <!-- 内容区域 -->
        <div class="p-5">
          <div v-if="assessmentCompleted" class="mb-5">
            <div class="bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
              <i class="fa-solid fa-check-circle text-xl"></i>
              <div>
                <div class="font-medium">情绪评估已完成</div>
                <div class="text-sm opacity-80">您可以查看详细的分析结果</div>
              </div>
            </div>
            <button 
              @click="viewAssessmentResults" 
              class="w-full py-3 rounded-lg bg-blue-500 hover:bg-blue-600 text-white transition-all duration-200 font-medium flex items-center justify-center gap-2"
            >
              <i class="fa-solid fa-chart-pie"></i>
              查看分析结果
            </button>
          </div>
          
          <div v-else class="mb-5 text-neutral-600 dark:text-neutral-300">
            请上传检测报告文件进行情绪评估分析
          </div>
          
          <div v-if="!assessmentCompleted" class="p-4 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg border border-neutral-200 dark:border-neutral-700 mb-4">
            <div class="text-xs text-neutral-500 dark:text-neutral-400 mb-3 flex items-center gap-1.5">
              <i class="fa-solid fa-circle-info"></i>
              支持格式：PDF、图片(PNG/JPG)、TXT文本、Word文档
            </div>
            
            <div class="mb-4">
              <label for="file-upload" class="flex items-center justify-center w-full h-20 border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-700/30 transition-all">
                <div class="flex flex-col items-center">
                  <i class="fa-solid fa-file-arrow-up text-2xl text-neutral-400 dark:text-neutral-500 mb-2"></i>
                  <span class="text-sm text-neutral-500 dark:text-neutral-400">{{ selectedFile ? selectedFile.name : '点击或拖拽文件到此处' }}</span>
                </div>
                <input 
                  id="file-upload" 
                  type="file" 
                  ref="fileInput" 
                  accept=".pdf,.png,.jpg,.jpeg,.txt,.doc,.docx" 
                  @change="handleFileUpload" 
                  class="hidden"
                />
              </label>
            </div>
            
            <div v-if="uploadStatus" class="mb-3 py-2 px-3 rounded-md text-sm" :class="[
              uploadStatus.includes('成功') ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300' : 
              'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
            ]">
              <div class="flex items-center gap-2">
                <i :class="[
                  uploadStatus.includes('成功') ? 'fa-solid fa-circle-check' : 
                  (isUploading ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-circle-exclamation')
                ]"></i>
                <span>{{ uploadStatus }}</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 底部按钮栏 -->
        <div v-if="!assessmentCompleted" class="flex items-center justify-end p-5 border-t border-neutral-200 dark:border-neutral-700 gap-3">
          <button 
            @click="parseFile" 
            :disabled="!selectedFile || isUploading" 
            class="px-4 py-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800/30 transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <i class="fa-solid fa-file-lines"></i>
            查看解析文本
          </button>
          <button 
            @click="uploadFile" 
            :disabled="!selectedFile || isUploading" 
            class="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 dark:bg-primary-700 dark:hover:bg-primary-600 text-white transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <i class="fa-solid fa-upload"></i>
            {{ isUploading ? '上传中...' : '上传文件' }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- 解析结果弹窗 -->
    <div v-if="showParseModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-[1100] flex items-center justify-center transition-all duration-300 ease-in-out">
      <div class="w-full max-w-4xl max-h-[90vh] overflow-hidden bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in flex flex-col">
        <!-- 顶部标题栏 -->
        <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
          <h3 class="text-xl font-semibold text-neutral-800 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-file-lines text-blue-500"></i>
            文档解析结果
          </h3>
          <button 
            @click="showParseModal = false" 
            class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        
        <!-- 内容区域 -->
        <div class="flex-1 overflow-hidden p-5">
          <div class="h-full overflow-auto rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50 p-4 font-mono text-sm whitespace-pre-wrap">
            {{ parseResult }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分析结果弹窗 -->
    <div v-if="showAnalysisModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-[1100] flex items-center justify-center transition-all duration-300 ease-in-out">
      <div class="w-full max-w-5xl max-h-[90vh] overflow-hidden bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in flex flex-col">
        <!-- 顶部标题栏 -->
        <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
          <h3 class="text-xl font-semibold text-neutral-800 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-chart-column text-indigo-500"></i>
            情绪评估分析结果
          </h3>
          <button 
            @click="showAnalysisModal = false" 
            class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        
        <!-- 内容区域 -->
        <div class="flex-1 overflow-auto p-6">
          <div v-if="analysisData" class="space-y-8">
            
            <!-- 核心状态分析 -->
            <div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-5 border border-indigo-100 dark:border-indigo-800/30">
              <h4 class="text-lg font-semibold text-indigo-700 dark:text-indigo-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-gauge-high"></i>
                核心状态分析
              </h4>
              
              <div class="space-y-3">
                <div class="flex flex-col">
                  <span class="text-sm text-indigo-600 dark:text-indigo-400 font-medium">总体状态</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ analysisData['核心状态分析']['总体状态'] }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-indigo-600 dark:text-indigo-400 font-medium">情绪稳定性</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ analysisData['核心状态分析']['情绪稳定性'] }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-indigo-600 dark:text-indigo-400 font-medium">能量水平</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ analysisData['核心状态分析']['能量水平'] }}</span>
                </div>
              </div>
            </div>
            
            <!-- 重点指标异常 -->
            <div class="bg-rose-50 dark:bg-rose-900/20 rounded-lg p-5 border border-rose-100 dark:border-rose-800/30">
              <h4 class="text-lg font-semibold text-rose-700 dark:text-rose-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-triangle-exclamation"></i>
                重点指标异常
              </h4>
              
              <div class="space-y-4">
                <div v-for="(indicator, index) in analysisData['重点指标异常']" :key="index" class="p-3 bg-white dark:bg-neutral-800/50 rounded-lg shadow-sm">
                  <div class="flex justify-between items-start">
                    <div class="font-medium text-neutral-800 dark:text-neutral-200">{{ indicator['指标名称'] }}</div>
                    <div class="px-2 py-0.5 bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 text-sm rounded">
                      {{ indicator['当前值'] }} / {{ indicator['正常范围'] }}
                    </div>
                  </div>
                  <div class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{{ indicator['影响分析'] }}</div>
                </div>
                
                <div v-if="!analysisData['重点指标异常'] || analysisData['重点指标异常'].length === 0" class="text-center text-neutral-500 dark:text-neutral-400 py-3">
                  未发现异常指标
                </div>
              </div>
            </div>
            
            <!-- 针对性干预建议 -->
            <div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-5 border border-green-100 dark:border-green-800/30">
              <h4 class="text-lg font-semibold text-green-700 dark:text-green-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-lightbulb"></i>
                针对性干预建议
              </h4>
              
              <div class="space-y-5">
                <div v-for="(suggestions, indicator) in analysisData['针对性干预建议']" :key="indicator" class="space-y-3">
                  <div class="font-medium text-green-700 dark:text-green-400 border-b border-green-200 dark:border-green-800/50 pb-1">针对{{ indicator }}</div>
                  
                  <div v-for="(suggestion, suggIndex) in suggestions" :key="suggIndex" class="p-3 bg-white dark:bg-neutral-800/50 rounded-lg shadow-sm">
                    <div class="font-medium text-neutral-800 dark:text-neutral-200">{{ suggestion['建议标题'] }}</div>
                    <div class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{{ suggestion['具体方法'] }}</div>
                    <div v-if="suggestion['预期效果']" class="mt-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-1 rounded inline-block">
                      预期效果: {{ suggestion['预期效果'] }}
                    </div>
                  </div>
                </div>
                
                <div v-if="!analysisData['针对性干预建议'] || Object.keys(analysisData['针对性干预建议']).length === 0" class="text-center text-neutral-500 dark:text-neutral-400 py-3">
                  未提供针对性建议
                </div>
              </div>
            </div>
            
          </div>
          
          <div v-else class="flex items-center justify-center h-full">
            <div class="flex flex-col items-center">
              <i class="fa-solid fa-spinner fa-spin text-4xl text-indigo-500 mb-4"></i>
              <div class="text-lg font-medium text-neutral-700 dark:text-neutral-300">正在加载分析结果...</div>
            </div>
          </div>
          
        </div>
      </div>
    </div>
    
    <!-- 视频评估弹窗 -->
    <div v-if="showVideoModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-[1100] flex items-center justify-center transition-all duration-300 ease-in-out">
      <div class="w-full max-w-2xl h-[70vh] bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in overflow-hidden">
        <VideoRecorder @close="showVideoModal = false" @recording-complete="handleVideoRecordingComplete" />
      </div>
    </div>
    
    <!-- 视频分析结果弹窗 -->
    <div v-if="showVideoAnalysisModal" class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-[1100] flex items-center justify-center transition-all duration-300 ease-in-out">
      <div class="w-full max-w-5xl max-h-[90vh] overflow-hidden bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in flex flex-col">
        <!-- 顶部标题栏 -->
        <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
          <h3 class="text-xl font-semibold text-neutral-800 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-video text-blue-500"></i>
            视频情绪评估结果
          </h3>
          <button 
            @click="showVideoAnalysisModal = false" 
            class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
          >
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        
        <!-- 内容区域 -->
        <div class="flex-1 overflow-auto p-6">
          <div v-if="assessmentStore.videoAssessmentData" class="space-y-8">
            <!-- 情绪状态分析 -->
            <div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-5 border border-blue-100 dark:border-blue-800/30">
              <h4 class="text-lg font-semibold text-blue-700 dark:text-blue-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-face-smile"></i>
                情绪状态分析
              </h4>
              
              <div class="space-y-3">
                <div class="flex flex-col">
                  <span class="text-sm text-blue-600 dark:text-blue-400 font-medium">主要情绪</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['情绪状态分析']?.['主要情绪'] || '未检测到明显情绪' }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-blue-600 dark:text-blue-400 font-medium">情绪强度</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['情绪状态分析']?.['情绪强度'] || '未知' }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-blue-600 dark:text-blue-400 font-medium">情绪稳定性</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['情绪状态分析']?.['情绪稳定性'] || '未知' }}</span>
                </div>
              </div>
            </div>
            
            <!-- 面部表情分析 -->
            <div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-5 border border-purple-100 dark:border-purple-800/30">
              <h4 class="text-lg font-semibold text-purple-700 dark:text-purple-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-face-grin"></i>
                面部表情分析
              </h4>
              
              <div class="space-y-3">
                <div class="flex flex-col">
                  <span class="text-sm text-purple-600 dark:text-purple-400 font-medium">主要表情</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['面部表情分析']?.['主要表情'] || '未检测到明显表情' }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-purple-600 dark:text-purple-400 font-medium">表情变化</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['面部表情分析']?.['表情变化'] || '未知' }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-purple-600 dark:text-purple-400 font-medium">微表情检测</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['面部表情分析']?.['微表情检测'] || '未检测到明显微表情' }}</span>
                </div>
              </div>
            </div>
            
            <!-- 综合评估 -->
            <div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-5 border border-amber-100 dark:border-amber-800/30">
              <h4 class="text-lg font-semibold text-amber-700 dark:text-amber-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-clipboard-check"></i>
                综合评估
              </h4>
              
              <div class="space-y-3">
                <div class="flex flex-col">
                  <span class="text-sm text-amber-600 dark:text-amber-400 font-medium">总体心理状态</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['综合评估']?.['总体心理状态'] || '未知' }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-amber-600 dark:text-amber-400 font-medium">建议</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ assessmentStore.videoAssessmentData['综合评估']?.['建议'] || '暂无具体建议' }}</span>
                </div>
              </div>
            </div>
          </div>
          
          <div v-else class="flex flex-col items-center justify-center h-64 text-neutral-500 dark:text-neutral-400">
            <i class="fa-solid fa-file-circle-exclamation text-4xl mb-4"></i>
            <p>暂无视频评估数据</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import VideoRecorder from './VideoRecorder.vue'
import { useAssessmentStore } from '../stores/assessment'
import { useUserStore } from '../stores/user'

const psychAssessmentReady = ref(false);
const showEmotionalModal = ref(false);
const showParseModal = ref(false);
const showAnalysisModal = ref(false);
const showVideoModal = ref(false);
const showVideoAnalysisModal = ref(false);
const fileInput = ref(null);
const selectedFile = ref(null);
const isUploading = ref(false);
const uploadStatus = ref('');
const parseResult = ref('');
const processingAssessment = ref(false);
const assessmentCompleted = ref(false);
const analysisData = ref(null);
const latestAssessmentFile = ref(null);
const assessmentStore = useAssessmentStore();
const userStore = useUserStore();

// 定义状态检查间隔变量
let statusCheckInterval = null;

// 打开情绪评估弹窗
const openEmotionalAssessment = () => {
  // 如果正在处理中，则不允许操作
  if (processingAssessment.value) {
    return;
  }

  showEmotionalModal.value = true;
  // 重置状态
  uploadStatus.value = '';
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
  
  // 检查是否有已完成的评估
  checkLatestAssessment();
};

// 检查是否有最新的评估文件和处理状态
const checkLatestAssessment = async () => {
  try {
    // 首先检查是否有评估结果
    const response = await fetch('http://localhost:8666/api/latest_assessment');
    const data = await response.json();
    
    if (data.success && data.has_assessment) {
      assessmentCompleted.value = true;
      latestAssessmentFile.value = data.file_path;
      // 如果评估已完成，则不再处于处理中状态
      processingAssessment.value = false;
    } else {
      assessmentCompleted.value = false;
      latestAssessmentFile.value = null;
      
      // 如果没有评估结果，检查是否有正在处理的评估
      try {
        const statusResponse = await fetch('http://localhost:8666/api/assessment_status');
        const statusData = await statusResponse.json();
        
        // 根据后端返回状态设置处理中状态
        if (statusData.success && statusData.processing_assessment) {
          processingAssessment.value = true;
        } else {
          processingAssessment.value = false;
        }
      } catch (statusError) {
        console.error('获取评估处理状态失败:', statusError);
        processingAssessment.value = false;
      }
    }
  } catch (error) {
    console.error('获取最新评估状态失败:', error);
    assessmentCompleted.value = false;
    processingAssessment.value = false;
  }
};

// 查看评估结果
const viewAssessmentResults = async () => {
  showAnalysisModal.value = true;
  
  // 清空之前的数据
  analysisData.value = null;
  
  try {
    // 获取最新的评估结果
    const response = await fetch('http://localhost:8666/api/assessment_results');
    const data = await response.json();
    
    if (data.success) {
      analysisData.value = data.results;
    } else {
      console.error('获取评估结果失败:', data.message);
    }
  } catch (error) {
    console.error('获取评估结果失败:', error);
  }
};

// 打开心理评估
const openPsychologicalAssessment = async () => {
  if (!psychAssessmentReady.value) {
    return; // 如果评估未完成，按钮不可点击
  }
  
  try {
    // 显示加载状态
    uploadStatus.value = '正在生成心理评估报告...';
    showEmotionalModal.value = true; // 显示弹窗以显示状态
    
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
    
    uploadStatus.value = '报告生成成功，已开始下载';
    
    // 3秒后关闭弹窗
    setTimeout(() => {
      showEmotionalModal.value = false;
      uploadStatus.value = '';
    }, 3000);
    
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
      uploadStatus.value = '上传成功，开始后台分析';
      // 清空选择的文件
      fileInput.value.value = '';
      selectedFile.value = null;
      
      // 设置为处理中状态
      processingAssessment.value = true;
      
      // 关闭弹窗
      setTimeout(() => {
        showEmotionalModal.value = false;
        uploadStatus.value = '';
        
        // 显示后台处理通知
        const processingNotification = document.createElement('div');
        processingNotification.className = 'fixed bottom-4 right-4 bg-blue-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2';
        processingNotification.innerHTML = `
          <i class="fa-solid fa-spinner fa-spin"></i>
          <div>
            <div class="font-medium">情绪评估分析中</div>
            <div class="text-sm opacity-90">分析完成后可在侧边栏查看结果</div>
          </div>
        `;
        document.body.appendChild(processingNotification);
        
        // 8秒后移除通知
        setTimeout(() => {
          processingNotification.classList.add('animate-fade-out');
          setTimeout(() => {
            processingNotification.remove();
          }, 500);
        }, 8000);
        
        // 开始定期检查评估状态
        startAssessmentStatusCheck();
      }, 1500);
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

// 定期检查评估状态的函数 - 使用store中的方法
const checkAssessmentStatus = () => {
  assessmentStore.loadAssessmentStatus().then(() => {
    // 从store中更新本地状态
    psychAssessmentReady.value = assessmentStore.psychologicalAssessmentReady.value;
    processingAssessment.value = assessmentStore.psychologicalProcessing.value;
  }).catch(error => {
    console.error('通过store获取评估状态失败:', error);
  });
};

// 定期检查情绪评估状态
const startAssessmentStatusCheck = () => {
  // 每10秒检查一次状态，直到评估完成
  const checkForCompletion = () => {
    assessmentStore.loadLatestEmotionalAssessment().then(() => {
      // 从store中获取完成状态
      const isComplete = assessmentStore.emotionalAssessmentComplete.value;
      
      if (isComplete) {
        // 更新本地状态
        assessmentCompleted.value = true;
        processingAssessment.value = false;
        
        // 如果有评估数据，获取文件名
        if (assessmentStore.emotionalAssessmentData.value && 
            assessmentStore.emotionalAssessmentData.value.file_name) {
          latestAssessmentFile.value = assessmentStore.emotionalAssessmentData.value.file_name;
        }
        
        // 显示完成通知
        const completionNotification = document.createElement('div');
        completionNotification.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2';
        completionNotification.innerHTML = `
          <i class="fa-solid fa-check-circle"></i>
          <div>
            <div class="font-medium">情绪评估已完成</div>
            <div class="text-sm opacity-90">点击情绪评估按钮查看结果</div>
          </div>
        `;
        document.body.appendChild(completionNotification);
        
        // 5秒后移除通知
        setTimeout(() => {
          completionNotification.classList.add('animate-fade-out');
          setTimeout(() => {
            completionNotification.remove();
          }, 500);
        }, 5000);
        
        // 停止检查
        if (statusCheckInterval) {
          clearInterval(statusCheckInterval);
          statusCheckInterval = null;
        }
      }
    }).catch(error => {
      console.error('检查情绪评估状态失败:', error);
    });
  };
  
  // 清除之前的检查间隔（如果有）
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }
  
  // 立即检查一次
  checkForCompletion();
  
  // 设置定时检查
  statusCheckInterval = setInterval(checkForCompletion, 10000); // 每10秒检查一次
};

// 设置定时检查
let checkInterval = null;

onMounted(async () => {
  try {
    // 加载心理评估状态
    await assessmentStore.initialize()
    // 检查心理评估是否就绪
    psychAssessmentReady.value = assessmentStore.psychologicalAssessmentReady
    
    // 加载情绪评估状态
    await assessmentStore.loadAssessmentStatus()
    assessmentCompleted.value = assessmentStore.emotionalAssessmentComplete
    
    // 加载视频上传状态（通过localStorage）
    assessmentStore.loadVideoUploadState()
    
    // 如果视频上传回调成功但评估未完成，启动轮询
    if (assessmentStore.videoUploadEtag && 
        assessmentStore.uploadCallbackComplete && 
        !assessmentStore.assessmentComplete) {
      assessmentStore.startStatusPolling(assessmentStore.videoUploadEtag)
    }
  } catch (e) {
    console.error('初始化评估状态失败:', e);
  }
});

onUnmounted(() => {
  // 清理定时器
  if (checkInterval) {
    clearInterval(checkInterval);
  }
  
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }
});

// 视频评估相关
// 打开视频评估弹窗
const openVideoAssessment = () => {
  // 如果已经上传过视频并在处理中，则不允许再次录制
  if (assessmentStore.uploadCallbackComplete) {
    return;
  }
  showVideoModal.value = true;
}

// 处理视频录制完成
const handleVideoRecordingComplete = () => {
  showVideoModal.value = false;
  
  if (assessmentStore.videoAssessmentComplete) {
    showVideoAnalysisModal.value = true;
  }
}

// 查看视频评估结果
const viewVideoAssessmentResults = () => {
  if (assessmentStore.videoAssessmentComplete) {
    showVideoAnalysisModal.value = true;
  }
}

// 获取视频按钮的提示文本
function getVideoButtonTitle() {
  if (assessmentStore.videoProcessing) {
    return '视频分析处理中，请稍候'
  } else if (assessmentStore.assessmentComplete) {
    return '查看视频评估结果'
  } else if (assessmentStore.uploadCallbackComplete && !assessmentStore.assessmentComplete) {
    return '视频已上传，评估中...'
  } else {
    return '视频评估'
  }
}

// 测试上传视频
const uploadTestVideo = async () => {
  try {
    // 如果已有上传进行中，显示提示
    if (assessmentStore.uploadCallbackComplete) {
      showNotification({
        type: 'warning',
        title: '上传已在进行中',
        message: '请等待当前上传完成'
      });
      return;
    }
    
    // 显示加载中通知
    showNotification({
      type: 'info',
      title: '准备测试视频',
      message: '正在获取本地测试视频...'
    });
    
    // 获取授权令牌
    const authToken = userStore.getAuthToken();
    
    // 确保token存储在userStore中
    if (authToken) {
      userStore.setAuthToken(authToken);
    }
    
    // 获取测试视频文件
    // 使用本地测试视频文件
    const testVideoUrl = '/videos/emotion_assessment.avi';
    const response = await fetch(testVideoUrl);
    
    if (!response.ok) {
      throw new Error(`无法获取测试视频: ${response.status} ${response.statusText}`);
    }
    
    const videoBlob = await response.blob();
    
    // 显示上传中通知
    showNotification({
      type: 'info',
      title: '上传测试视频',
      message: '正在上传视频到服务器...'
    });

    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', videoBlob, 'emotion_assessment.avi');
    
    // 上传视频
    const uploadResponse = await fetch('http://localhost:8666/api/upload-video', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      body: formData,
    });
    
    const result = await uploadResponse.json();
    
    if (result.success) {
      // 成功通知
      showNotification({
        type: 'success',
        title: '测试视频上传成功',
        message: '视频已上传，开始处理和评估'
      });
      
      // 获取上传数据
      const uploadData = result.data;
      const etag = uploadData?.etag;
      
      if (etag) {
        console.log(`设置并保存视频上传状态: etag=${etag}`);
        // 设置视频上传etag值和处理状态
        assessmentStore.setVideoUploadEtag(etag);
        assessmentStore.setUploadCallbackComplete(uploadData.upload_callback_status || false);
        assessmentStore.setAssessmentComplete(uploadData.assessment_status || false);
        
        // 保存状态到localStorage
        assessmentStore.saveVideoUploadState();
        
        // 根据上传回调状态决定是否启动轮询
        if (uploadData.upload_callback_status === true) {
          console.log('上传回调已完成，启动视频评估状态轮询');
          assessmentStore.startStatusPolling(etag);
        }
      } else {
        console.warn('未获取到视频etag，无法启动状态轮询');
      }
    } else {
      throw new Error(result.message || '视频上传失败');
    }
  } catch (error) {
    console.error('测试视频上传失败:', error);
    
    // 显示错误通知
    showNotification({
      type: 'error',
      title: '测试视频上传失败',
      message: error.message || '请检查网络连接并重试'
    });
  }
}

// 通用通知函数
const showNotification = ({ type = 'info', title, message, duration = 3000 }) => {
  try {
    const notification = document.createElement('div');
    notification.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg z-[1100] animate-fade-in flex items-center gap-2`;
    
    // 根据类型设置样式
    if (type === 'success') {
      notification.classList.add('bg-green-500', 'text-white');
    } else if (type === 'error') {
      notification.classList.add('bg-red-500', 'text-white');
    } else if (type === 'warning') {
      notification.classList.add('bg-yellow-500', 'text-white');
    } else {
      notification.classList.add('bg-blue-500', 'text-white');
    }
    
    // 设置图标
    let icon = '';
    if (type === 'success') icon = 'fa-check-circle';
    else if (type === 'error') icon = 'fa-exclamation-circle';
    else if (type === 'warning') icon = 'fa-exclamation-triangle';
    else icon = 'fa-info-circle';
    
    notification.innerHTML = `
      <i class="fa-solid ${icon}"></i>
      <div>
        <div class="font-medium">${title}</div>
        <div class="text-sm opacity-90">${message}</div>
      </div>
    `;
    
    document.body.appendChild(notification);
    
    // 设置超时移除通知
    setTimeout(() => {
      notification.classList.add('animate-fade-out');
      setTimeout(() => {
        notification.remove();
      }, 500);
    }, duration);
  } catch (e) {
    console.error('显示通知出错:', e);
  }
}
</script>

<style scoped>
/* 淡入动画 */
@keyframes fade-in {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
  animation: fade-in 0.3s ease-out forwards;
}

/* 淡出动画 */
@keyframes fade-out {
  from { opacity: 1; transform: translateY(0); }
  to { opacity: 0; transform: translateY(10px); }
}

.animate-fade-out {
  animation: fade-out 0.5s ease-in forwards;
}
</style> 