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
        <span v-if="assessmentStore.assessmentComplete || (!assessmentStore.uploadCallbackComplete && localAssessmentComplete)" class="ml-1 px-1.5 py-0.5 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 text-xs rounded-full">
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
          <!-- 评估完成且有结果时显示查看结果按钮 -->
          <div v-if="assessmentCompleted || localAssessmentComplete || 
                     (assessmentStore.assessmentComplete && assessmentStore.emotionalAssessmentData) || 
                     (!assessmentStore.uploadCallbackComplete && localAssessmentComplete)" class="mb-5">
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
          
          <!-- 视频已上传但评估未完成时显示处理中状态 -->
          <div v-else-if="assessmentStore.uploadCallbackComplete && !assessmentStore.assessmentComplete" class="mb-5">
            <div class="flex flex-col items-center justify-center py-8">
              <div class="w-16 h-16 mb-6 relative">
                <div class="absolute inset-0 rounded-full border-4 border-blue-100 dark:border-blue-900/30"></div>
                <div class="absolute inset-0 rounded-full border-4 border-blue-500 dark:border-blue-400 border-t-transparent animate-spin"></div>
              </div>
              <div class="text-xl font-semibold text-neutral-800 dark:text-neutral-200 mb-2">视频评估处理中</div>
              <div class="text-neutral-600 dark:text-neutral-400 text-center max-w-sm">
                <p class="mb-3">我们正在分析您的视频数据，这可能需要几分钟时间。</p>
                <p>分析完成后，您可以查看详细的评估结果。</p>
              </div>
              <div class="mt-6 flex flex-col items-center gap-2 text-sm text-neutral-500 dark:text-neutral-500">
                <div class="flex items-center gap-2">
                  <i class="fa-solid fa-circle-check text-green-500"></i>
                  <span>视频上传完成</span>
                </div>
                <div class="flex items-center gap-2">
                  <i class="fa-solid fa-spinner fa-spin text-blue-500"></i>
                  <span>情绪数据分析中</span>
                </div>
                <div class="flex items-center gap-2">
                  <i class="fa-regular fa-circle text-neutral-400"></i>
                  <span>生成评估报告</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 未上传视频或未完成评估时显示上传界面 -->
          <div v-else>
            <div class="mb-5 text-neutral-600 dark:text-neutral-300">
              请上传检测报告文件进行情绪评估分析
            </div>
            
            <div class="p-4 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg border border-neutral-200 dark:border-neutral-700 mb-4">
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
            
            <!-- 底部按钮栏 -->
            <div class="flex items-center justify-end p-5 border-t border-neutral-200 dark:border-neutral-700 gap-3">
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
          <div v-if="analysisData || assessmentStore.emotionalAssessmentData" class="space-y-8">
            
            <!-- 核心状态分析 -->
            <div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-5 border border-indigo-100 dark:border-indigo-800/30">
              <h4 class="text-lg font-semibold text-indigo-700 dark:text-indigo-300 mb-4 flex items-center gap-2">
                <i class="fa-solid fa-gauge-high"></i>
                核心状态分析
              </h4>
              
              <div class="space-y-3">
                <div class="flex flex-col">
                  <span class="text-sm text-indigo-600 dark:text-indigo-400 font-medium">总体状态</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ 
                    (analysisData && analysisData['核心状态分析'] && analysisData['核心状态分析']['总体状态']) || 
                    (assessmentStore.emotionalAssessmentData && assessmentStore.emotionalAssessmentData['核心状态分析'] && assessmentStore.emotionalAssessmentData['核心状态分析']['总体状态']) || 
                    '无数据' 
                  }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-indigo-600 dark:text-indigo-400 font-medium">情绪稳定性</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ 
                    (analysisData && analysisData['核心状态分析'] && analysisData['核心状态分析']['情绪稳定性']) || 
                    (assessmentStore.emotionalAssessmentData && assessmentStore.emotionalAssessmentData['核心状态分析'] && assessmentStore.emotionalAssessmentData['核心状态分析']['情绪稳定性']) || 
                    '无数据' 
                  }}</span>
                </div>
                
                <div class="flex flex-col">
                  <span class="text-sm text-indigo-600 dark:text-indigo-400 font-medium">能量水平</span>
                  <span class="text-neutral-700 dark:text-neutral-300">{{ 
                    (analysisData && analysisData['核心状态分析'] && analysisData['核心状态分析']['能量水平']) || 
                    (assessmentStore.emotionalAssessmentData && assessmentStore.emotionalAssessmentData['核心状态分析'] && assessmentStore.emotionalAssessmentData['核心状态分析']['能量水平']) || 
                    '无数据' 
                  }}</span>
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
                <!-- 使用本地analysisData -->
                <div v-if="analysisData && analysisData['重点指标异常']" v-for="(indicator, index) in analysisData['重点指标异常']" :key="'local-'+index" class="p-3 bg-white dark:bg-neutral-800/50 rounded-lg shadow-sm">
                  <div class="flex justify-between items-start">
                    <div class="font-medium text-neutral-800 dark:text-neutral-200">{{ indicator['指标名称'] }}</div>
                    <div class="px-2 py-0.5 bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 text-sm rounded">
                      {{ indicator['当前值'] }} / {{ indicator['正常范围'] }}
                    </div>
                  </div>
                  <div class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{{ indicator['影响分析'] }}</div>
                </div>

                <!-- 使用store中的数据 -->
                <div v-else-if="assessmentStore.emotionalAssessmentData && assessmentStore.emotionalAssessmentData['重点指标异常']" 
                     v-for="(indicator, index) in assessmentStore.emotionalAssessmentData['重点指标异常']" 
                     :key="'store-'+index" class="p-3 bg-white dark:bg-neutral-800/50 rounded-lg shadow-sm">
                  <div class="flex justify-between items-start">
                    <div class="font-medium text-neutral-800 dark:text-neutral-200">{{ indicator['指标名称'] }}</div>
                    <div class="px-2 py-0.5 bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 text-sm rounded">
                      {{ indicator['当前值'] }} / {{ indicator['正常范围'] }}
                    </div>
                  </div>
                  <div class="mt-2 text-sm text-neutral-600 dark:text-neutral-400">{{ indicator['影响分析'] }}</div>
                </div>
                
                <div v-if="(!analysisData || !analysisData['重点指标异常'] || analysisData['重点指标异常'].length === 0) && 
                          (!assessmentStore.emotionalAssessmentData || !assessmentStore.emotionalAssessmentData['重点指标异常'] || 
                           assessmentStore.emotionalAssessmentData['重点指标异常'].length === 0)" 
                     class="text-center text-neutral-500 dark:text-neutral-400 py-3">
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
                <!-- 使用本地analysisData -->
                <template v-if="analysisData && analysisData['针对性干预建议']">
                  <div v-for="(suggestions, indicator) in analysisData['针对性干预建议']" :key="'local-'+indicator" class="space-y-3">
                    <div class="font-medium text-green-700 dark:text-green-400 border-b border-green-200 dark:border-green-800/50 pb-1">针对{{ indicator }}</div>
                    
                    <div v-for="(suggestion, suggIndex) in suggestions" :key="'local-'+suggIndex" class="p-3 bg-white dark:bg-neutral-800/50 rounded-lg shadow-sm">
                      <div class="font-medium text-neutral-800 dark:text-neutral-200">{{ suggestion['建议标题'] }}</div>
                      <div class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{{ suggestion['具体方法'] }}</div>
                      <div v-if="suggestion['预期效果']" class="mt-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-1 rounded inline-block">
                        预期效果: {{ suggestion['预期效果'] }}
                      </div>
                    </div>
                  </div>
                </template>
                
                <!-- 使用store中的数据 -->
                <template v-else-if="assessmentStore.emotionalAssessmentData && assessmentStore.emotionalAssessmentData['针对性干预建议']">
                  <div v-for="(suggestions, indicator) in assessmentStore.emotionalAssessmentData['针对性干预建议']" :key="'store-'+indicator" class="space-y-3">
                    <div class="font-medium text-green-700 dark:text-green-400 border-b border-green-200 dark:border-green-800/50 pb-1">针对{{ indicator }}</div>
                    
                    <div v-for="(suggestion, suggIndex) in suggestions" :key="'store-'+suggIndex" class="p-3 bg-white dark:bg-neutral-800/50 rounded-lg shadow-sm">
                      <div class="font-medium text-neutral-800 dark:text-neutral-200">{{ suggestion['建议标题'] }}</div>
                      <div class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">{{ suggestion['具体方法'] }}</div>
                      <div v-if="suggestion['预期效果']" class="mt-2 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 px-2 py-1 rounded inline-block">
                        预期效果: {{ suggestion['预期效果'] }}
                      </div>
                    </div>
                  </div>
                </template>
                
                <div v-if="(!analysisData || !analysisData['针对性干预建议'] || Object.keys(analysisData['针对性干预建议']).length === 0) && 
                          (!assessmentStore.emotionalAssessmentData || !assessmentStore.emotionalAssessmentData['针对性干预建议'] || 
                           Object.keys(assessmentStore.emotionalAssessmentData['针对性干预建议'] || {}).length === 0)" 
                     class="text-center text-neutral-500 dark:text-neutral-400 py-3">
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
import { ref, onMounted, onUnmounted, watch } from 'vue';
import VideoRecorder from './VideoRecorder.vue'
import { useAssessmentStore } from '../stores/assessment'
import { useUserStore } from '../stores/user'
import { getApiUrl } from '../utils/api';

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
const localAssessmentComplete = ref(localStorage.getItem('localAssessmentComplete') === 'true');

// 定义状态检查间隔变量
let statusCheckInterval = null;

// 打开情绪评估弹窗
const openEmotionalAssessment = () => {
  // 打印当前处理状态，帮助调试
  console.log('[DEBUG] 情绪评估按钮点击', {
    processingAssessment: processingAssessment.value,
    assessmentCompleted: assessmentCompleted.value,
    emotionalProcessing: assessmentStore.emotionalProcessing?.value,
    emotionalAssessmentComplete: assessmentStore.emotionalAssessmentComplete?.value
  });
  
  // 如果正在处理中，则不允许操作
  if (processingAssessment.value) {
    console.log('[DEBUG] 情绪评估正在处理中，忽略点击');
    
    // 检查是否处于卡死状态 - 如果评估已完成但处理状态没更新
    if (assessmentStore.emotionalAssessmentComplete?.value) {
      console.log('[DEBUG] 检测到状态不一致: 评估已完成但处理状态仍为true，强制重置');
      processingAssessment.value = false;
      // 继续执行以下代码打开弹窗
    } else {
      return;
    }
  }

  console.log('[DEBUG] 打开情绪评估弹窗');
  console.log('[DEBUG] 当前状态:', {
    assessmentCompleted: assessmentCompleted.value,
    emotionalAssessmentComplete: assessmentStore.emotionalAssessmentComplete?.value,
    emotionalAssessmentData: assessmentStore.emotionalAssessmentData,
    latestAssessmentFile: latestAssessmentFile.value,
    videoAssessmentComplete: assessmentStore.videoAssessmentComplete?.value,
    videoAssessmentData: assessmentStore.videoAssessmentData
  });

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
  console.log('[DEBUG] 检查最新评估状态')
  
  try {
    const success = await assessmentStore.loadLatestEmotionalAssessment()
    
    if (success) {
      console.log('[DEBUG] 成功加载评估数据')
      assessmentCompleted.value = true
      processingAssessment.value = false
      
      // 如果需要，加载评估结果
      if (!analysisData.value) {
        await loadAssessmentResults()
      }
    } else {
      console.log('[DEBUG] 没有找到有效的评估数据')
      assessmentCompleted.value = false
      processingAssessment.value = false
      analysisData.value = null
    }
  } catch (error) {
    console.error('[DEBUG] 检查评估状态时发生错误:', error)
    assessmentCompleted.value = false
    processingAssessment.value = false
    analysisData.value = null
  }
}

const loadAssessmentResults = async () => {
  console.log('[DEBUG] 加载评估结果详情')
  
  try {
    const response = await fetch(getApiUrl('assessment_results'))
    const data = await response.json()
    
    if (data.success) {
      analysisData.value = data.results
      console.log('[DEBUG] 成功加载评估结果详情')
    } else {
      console.log('[DEBUG] 加载评估结果详情失败')
      analysisData.value = null
    }
  } catch (error) {
    console.error('[DEBUG] 加载评估结果详情时发生错误:', error)
    analysisData.value = null
  }
}

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
    const response = await fetch(getApiUrl('psychological_assessment'), {
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
    
    const response = await fetch(getApiUrl('emotional_assessment'), {
      method: 'POST',
      body: formData,
    });
    
    const result = await response.json();
    
    if (result.success) {
      uploadStatus.value = '上传成功，开始后台分析';
      // 清空选择的文件
      fileInput.value.value = '';
      selectedFile.value = null;
      
      // 重置本地评估状态
      localAssessmentComplete.value = false;
      localStorage.setItem('localAssessmentComplete', 'false');
      
      // 设置为处理中状态
      processingAssessment.value = true;
      
      // 开始轮询检查评估状态
      startLocalAssessmentCheck();
      
      // 关闭弹窗
      setTimeout(() => {
        showEmotionalModal.value = false;
        uploadStatus.value = '';
        
        // 显示后台处理通知
        showNotification({
          type: 'info',
          title: '情绪评估分析中',
          message: '分析完成后可在侧边栏查看结果'
        });
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

// 添加本地评估状态检查函数
let localAssessmentCheckInterval = null;

const startLocalAssessmentCheck = () => {
  // 清除可能存在的旧计时器
  if (localAssessmentCheckInterval) {
    clearInterval(localAssessmentCheckInterval);
  }
  
  // 设置检查间隔为3秒
  localAssessmentCheckInterval = setInterval(async () => {
    try {
      const response = await fetch(getApiUrl('assessment_results'));
      const data = await response.json();
      
      if (data.success && data.results) {
        // 评估完成，设置状态
        localAssessmentComplete.value = true;
        localStorage.setItem('localAssessmentComplete', 'true');
        
        // 保存评估数据
        analysisData.value = data.results;
        
        // 停止检查
        clearInterval(localAssessmentCheckInterval);
        localAssessmentCheckInterval = null;
        
        // 更新处理状态
        processingAssessment.value = false;
        
        // 显示完成通知
        showNotification({
          type: 'success',
          title: '情绪评估完成',
          message: '可以查看评估结果了'
        });
      }
    } catch (error) {
      console.error('[DEBUG] 检查评估状态失败:', error);
    }
  }, 3000);
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
    
    const response = await fetch(getApiUrl('parse_document'), {
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

// 启动状态检查 - 改为使用主轮询机制
function startAssessmentStatusCheck() {
  console.log('启动评估状态检查')
  
  // 必须有有效的etag才启动检查
  if (!videoUploadEtag.value) {
    console.warn('无法启动状态检查: 缺少有效的视频上传etag')
    return
  }
  
  // 启动主轮询机制而不是单独的状态检查
  assessmentStore.startMasterPolling()
}

// 在组件销毁时清理所有轮询
onUnmounted(() => {
  // 停止所有轮询和检查
  assessmentStore.stopMasterPolling()
  if (localAssessmentCheckInterval) {
    clearInterval(localAssessmentCheckInterval);
    localAssessmentCheckInterval = null;
  }
})

// 初始化时检查是否需要恢复上次的上传状态
onMounted(async () => {
  console.log('[DEBUG] 组件初始化')
  
  // 初始化状态
  try {
    const initResult = await assessmentStore.initialize()
    
    if (!initResult) {
      console.log('[DEBUG] 初始化失败，重置所有状态')
      assessmentCompleted.value = false
      processingAssessment.value = false
      localAssessmentComplete.value = false
      localStorage.setItem('localAssessmentComplete', 'false')
      return
    }
    
    // 记录初始化后的状态
    console.log(`[DEBUG] 初始化后状态: uploadCallbackComplete=${assessmentStore.uploadCallbackComplete}, ` + 
                `assessmentComplete=${assessmentStore.assessmentComplete}, reportId=${assessmentStore.reportId}`);
    
    // 如果已有进行中的上传，检查服务器视频状态
    if (assessmentStore.uploadCallbackComplete || assessmentStore.reportId) {
      console.log('[DEBUG] 检测到有视频上传状态，立即检查服务器状态');
      // 强制检查一次服务器状态，不依赖轮询
      assessmentStore.checkVideoStatus(true);
    }
    
    // 检查最新评估状态 - 即使assessment_status为false也请求列表
    try {
      const response = await fetch(getApiUrl('assessment_results'))
      const data = await response.json()
      
      if (data.success && data.results) {
        console.log('[DEBUG] 检测到有效的评估')
        assessmentCompleted.value = true
        processingAssessment.value = false
        
        // 保存评估数据
        analysisData.value = data.results
        
        // 如果没有视频上传进行中，设置本地评估状态
        if (!assessmentStore.uploadCallbackComplete) {
          localAssessmentComplete.value = true
          localStorage.setItem('localAssessmentComplete', 'true')
        }
      } else {
        console.log('[DEBUG] 无有效评估，但保留当前状态')
        // 保留现有状态，避免重置可能有效的状态
      }
    } catch (error) {
      console.error('[DEBUG] 检查评估状态失败:', error)
      // 不重置状态，保留可能存在的有效状态
    }
    
    // 如果有reportId但未下载，确保主轮询启动
    if (assessmentStore.reportId && !assessmentStore.reportDownloaded) {
      console.log('[DEBUG] 检测到有report但未下载状态，确保启动轮询');
      assessmentStore.startMasterPolling();
    }
  } catch (e) {
    console.error('[DEBUG] 组件初始化出错:', e)
  }
})

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
    // 如果已有上传进行中，显示提示 - 修复条件判断，移除.value
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
    const uploadResponse = await fetch(getApiUrl('upload-video'), {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`
      },
      body: formData,
    });
    
    if (!uploadResponse.ok) {
      throw new Error(`服务器响应错误: ${uploadResponse.status} ${uploadResponse.statusText}`);
    }
    
    const result = await uploadResponse.json();
    
    if (result.success) {
      // 重置本地评估状态
      localAssessmentComplete.value = false;
      localStorage.setItem('localAssessmentComplete', 'false');
      
      // 成功通知
      showNotification({
        type: 'success',
        title: '测试视频上传成功',
        message: '视频已上传，开始处理和评估'
      });
      
      // 获取上传数据
      const uploadData = result.data || {};
      
      console.log('[DEBUG] 测试视频上传成功，返回数据:', result);
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
      
      // 手动保存状态到localStorage 并重试直到成功
      console.log('[DEBUG] 主动调用saveVideoUploadState保存状态');
      const maxRetries = 3;
      let retryCount = 0;
      let saveSuccessful = false;
      
      const saveWithVerification = () => {
        // 保存状态
        assessmentStore.saveVideoUploadState();
        
        // 验证保存结果
        setTimeout(() => {
          try {
            const savedState = localStorage.getItem('video_upload_state');
            if (!savedState) {
              console.error('[DEBUG] localStorage保存失败: 未能读取到video_upload_state');
              retryCount++;
              if (retryCount < maxRetries) {
                console.log(`[DEBUG] 尝试重新保存 (${retryCount}/${maxRetries})`);
                saveWithVerification();
              }
              return;
            }
            
            const parsedState = JSON.parse(savedState);
            console.log('[DEBUG] 验证localStorage中保存的状态:', parsedState);
            
            // 检查关键状态是否与预期一致
            const isStateCorrect = 
              (uploadData.report_id ? parsedState.reportId === uploadData.report_id : true) && 
              parsedState.uploadCallbackComplete === hasCallback &&
              parsedState.assessmentComplete === isAssessmentComplete &&
              parsedState.reportDownloaded === isReportDownloaded;
            
            if (!isStateCorrect && retryCount < maxRetries) {
              console.warn('[DEBUG] localStorage中的状态与预期不符，再次尝试保存');
              retryCount++;
              console.log(`[DEBUG] 重试 (${retryCount}/${maxRetries})`);
              saveWithVerification();
            } else if (isStateCorrect) {
              console.log('[DEBUG] localStorage状态验证成功');
              saveSuccessful = true;
            } else {
              console.error('[DEBUG] 达到最大重试次数，状态可能未正确保存');
            }
          } catch (err) {
            console.error('[DEBUG] 读取或验证localStorage状态失败:', err);
            retryCount++;
            if (retryCount < maxRetries) {
              console.log(`[DEBUG] 出错后重试 (${retryCount}/${maxRetries})`);
              saveWithVerification();
            }
          }
        }, 200);
      };
      
      // 开始保存并验证过程
      saveWithVerification();
      
      // 根据上传回调状态决定是否启动轮询
      if (hasCallback === true) {
        console.log('[DEBUG] 上传回调已完成，启动主轮询');
        // 启动主轮询方法，整合所有状态检查
        assessmentStore.startMasterPolling();
      } else {
        console.log('[DEBUG] 上传回调未完成，启动状态轮询');
        assessmentStore.startStatusPolling();
      }
    } else {
      throw new Error(result.message || '视频上传失败');
    }
  } catch (error) {
    console.error('测试视频上传失败:', error);
    
    // 先重置状态，防止卡在上传中
    assessmentStore.setUploadCallbackComplete(false);
    assessmentStore.setAssessmentComplete(false);
    assessmentStore.saveVideoUploadState();
    
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

// 监听报告下载状态变化
watch(() => assessmentStore.reportDownloaded, async (newValue) => {
  if (newValue) {
    console.log('[DEBUG] 检测到报告下载完成，开始评估流程')
    
    // 重置本地评估状态
    localAssessmentComplete.value = false
    localStorage.setItem('localAssessmentComplete', 'false')
    
    // 设置为处理中状态
    processingAssessment.value = true
    
    // 开始轮询检查评估状态
    startLocalAssessmentCheck()
    
    // 显示处理中通知
    showNotification({
      type: 'info',
      title: '情绪评估分析中',
      message: '报告下载完成，正在进行分析...'
    })
  }
})

// 修改查看评估结果函数
const viewAssessmentResults = async () => {
  try {
    console.log('[DEBUG] 开始加载评估结果');
    
    // 如果本地已有数据，直接显示
    if (analysisData.value || assessmentStore.emotionalAssessmentData) {
      console.log('[DEBUG] 使用已有的评估数据');
      showAnalysisModal.value = true;
      return;
    }
    
    // 尝试从服务器获取最新数据
    console.log('[DEBUG] 尝试从服务器获取最新数据');
    const response = await fetch(getApiUrl('assessment_results'));
    const data = await response.json();
    
    if (data.success && data.results) {
      console.log('[DEBUG] 成功获取新的评估数据');
      analysisData.value = data.results;
      showAnalysisModal.value = true;
    } else {
      throw new Error('无法获取评估结果');
    }
  } catch (error) {
    console.error('[DEBUG] 获取评估结果失败:', error);
    showNotification({
      type: 'error',
      title: '获取评估结果失败',
      message: '请稍后重试'
    });
  }
};

// 修改 downloadVideoReport 方法
const downloadVideoReport = async (reportId) => {
  try {
    const response = await fetch(getApiUrl(`download_report/${reportId}`), {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userStore.getAuthToken()}`
      }
    });

    if (!response.ok) {
      throw new Error('下载失败');
    }

    const blob = await response.blob();
    const fileName = `assessment_${reportId}.pdf`;
    const filePath = `backend/save/assessments/${fileName}`;

    // 保存文件
    const formData = new FormData();
    formData.append('file', blob, fileName);
    
    const saveResponse = await fetch(getApiUrl('save_report'), {
      method: 'POST',
      body: formData
    });

    if (!saveResponse.ok) {
      throw new Error('保存报告失败');
    }

    // 开始处理报告
    const processResponse = await fetch(getApiUrl('process_report'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        report_path: filePath
      })
    });

    if (!processResponse.ok) {
      throw new Error('处理报告失败');
    }

    const processResult = await processResponse.json();
    
    if (processResult.success) {
      // 开始轮询检查评估状态
      startLocalAssessmentCheck();
      showNotification({
        type: 'success',
        title: '成功',
        message: '报告下载成功，正在处理分析...'
      });
    } else {
      throw new Error(processResult.message || '处理报告失败');
    }

  } catch (error) {
    console.error('下载或处理报告时出错:', error);
    showNotification({
      type: 'error',
      title: '错误',
      message: error.message || '下载或处理报告失败'
    });
  }
};
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