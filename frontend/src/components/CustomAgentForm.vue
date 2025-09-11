<template>
  <div class="fixed inset-0 bg-neutral-900/70 backdrop-blur-sm z-1100 flex items-center justify-center transition-all duration-300 ease-in-out" style="pointer-events: all;">
    <!-- 主内容区 -->
    <div class="w-full max-w-3xl max-h-[90vh] overflow-y-auto bg-white dark:bg-neutral-800 rounded-xl shadow-2xl transition-all duration-300 ease-in-out transform animate-fade-in">
      <!-- 顶部标题栏 -->
      <div class="flex items-center justify-between p-5 border-b border-neutral-200 dark:border-neutral-700">
        <h3 class="text-xl font-semibold text-neutral-800 dark:text-white">
          {{ props.editAgent ? '编辑角色' : '创建自定义角色' }}
        </h3>
        <button 
          @click="$emit('close')" 
          class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-white transition-all duration-200 hover:scale-110"
        >
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- 内容区 -->
      <div class="p-6 grid grid-cols-1 md:grid-cols-12 gap-6">
        <!-- 左侧表单区域 -->
        <div class="md:col-span-8">
          <div class="space-y-5">
            <!-- 角色名称 -->
            <div>
              <label for="agent-name" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">角色名称</label>
              <input 
                id="agent-name"
                v-model="form.name" 
                type="text" 
                class="w-full px-4 py-2.5 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-800 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 transition-all duration-200" 
                placeholder="请输入角色名称"
              >
            </div>

            <!-- 标签选择器 -->
            <div>
              <label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">角色特质 <span class="text-xs text-neutral-500">(最多4个)</span></label>
              <div class="flex flex-wrap gap-2">
                <button 
                  v-for="(tag, index) in tagOptions" 
                  :key="index"
                  @click="toggleTag(tag)"
                  :class="[
                    'text-xs py-1 px-3 rounded-full transition-all duration-200 font-medium shadow-sm', 
                    selectedTags.includes(tag) 
                      ? `${tagColors[index % tagColors.length].selected} ring-2 ring-primary-500 dark:ring-primary-600` 
                      : `${tagColors[index % tagColors.length].normal} hover:brightness-95 dark:hover:brightness-110`
                  ]"
                >
                  {{ tag }}
                </button>
              </div>
            </div>

            <!-- 角色外观选择 -->
            <div>
              <label for="agent-model" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">角色外观</label>
              <select 
                id="agent-model"
                v-model="form.model"
                class="w-full px-4 py-2.5 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-800 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 transition-all duration-200"
              >
                <option value="xiaozhi">小智 - 阳光小助手</option>
                <option value="linzong">林总 - 商业强人</option>
                <option value="zynx">李思思 - 产品经理</option>
                <option value="nanaA">娜娜A - 傲娇猫娘</option>
                <option value="nanaB">娜娜B - 知性大姐姐</option>
                <option value="nanaC">娜娜C - 元气少女</option>
              </select>
            </div>

            <!-- 角色特质详情 -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
              <!-- 性格特征 -->
              <div>
                <label for="agent-personality" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">性格特征</label>
                <textarea 
                  id="agent-personality"
                  v-model="form.personality" 
                  class="w-full px-4 py-2.5 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-800 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 transition-all duration-200 min-h-[100px] resize-none" 
                  placeholder="例如：外向开朗、善解人意、幽默风趣..."
                ></textarea>
              </div>
              
              <!-- 兴趣爱好 -->
              <div>
                <label for="agent-interests" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">兴趣爱好</label>
                <textarea 
                  id="agent-interests"
                  v-model="form.interests" 
                  class="w-full px-4 py-2.5 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-800 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 transition-all duration-200 min-h-[100px] resize-none" 
                  placeholder="例如：烹饪美食、阅读文学、旅行探险..."
                ></textarea>
              </div>
              
              <!-- 生活习惯 -->
              <div>
                <label for="agent-lifestyle" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">生活习惯</label>
                <textarea 
                  id="agent-lifestyle"
                  v-model="form.lifestyle" 
                  class="w-full px-4 py-2.5 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-800 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 transition-all duration-200 min-h-[100px] resize-none" 
                  placeholder="例如：早睡早起、规律作息、整洁有序..."
                ></textarea>
              </div>
              
              <!-- 价值观 -->
              <div>
                <label for="agent-values" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">价值观</label>
                <textarea 
                  id="agent-values"
                  v-model="form.values" 
                  class="w-full px-4 py-2.5 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-700 text-neutral-800 dark:text-white placeholder-neutral-400 focus:ring-2 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 transition-all duration-200 min-h-[100px] resize-none" 
                  placeholder="例如：追求公平正义、尊重多元文化、保护环境..."
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧辅助区域 -->
        <div class="md:col-span-4">
          <!-- 文件上传区域 - 仅在创建新角色时显示 -->
          <div v-if="!props.editAgent" class="mb-6 bg-neutral-50 dark:bg-neutral-700/50 rounded-xl p-4 shadow-sm border border-neutral-200 dark:border-neutral-700">
            <h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">通过文件创建</h4>
            
            <div class="space-y-3">
              <label 
                for="file-upload" 
                class="flex flex-col items-center justify-center w-full h-32 border-2 border-neutral-300 border-dashed rounded-lg cursor-pointer bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 transition-all duration-200"
              >
                <div class="flex flex-col items-center justify-center pt-5 pb-6">
                  <i class="fa-solid fa-cloud-arrow-up mb-2 text-2xl text-neutral-500 dark:text-neutral-400"></i>
                  <p class="text-sm text-neutral-600 dark:text-neutral-300">
                    <span class="font-medium">点击上传文件</span> 或拖放文件至此
                  </p>
                  <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">支持 TXT, PDF, DOC, DOCX</p>
                </div>
                <input 
                  id="file-upload" 
                  ref="fileInput"
                  type="file" 
                  class="hidden" 
                  @change="handleFileUpload" 
                  accept=".txt,.pdf,.doc,.docx"
                />
              </label>
              
              <!-- 上传状态展示 -->
              <div v-if="fileName || isUploading" class="mt-2 space-y-2">
                <div class="flex items-center text-sm">
                  <i class="fa-solid fa-file-lines mr-2 text-primary-500 dark:text-primary-400"></i>
                  <span class="text-neutral-700 dark:text-neutral-300 truncate">{{ fileName || '正在解析文件...' }}</span>
                </div>
                
                <!-- 进度条 -->
                <div v-if="isUploading" class="w-full bg-neutral-200 dark:bg-neutral-600 rounded-full h-1.5">
                  <div 
                    class="bg-primary-500 dark:bg-primary-400 h-1.5 rounded-full transition-all duration-300 ease-in-out" 
                    :style="{ width: uploadProgress + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 语音上传区域 -->
          <div class="mb-6 bg-neutral-50 dark:bg-neutral-700/50 rounded-xl p-4 shadow-sm border border-neutral-200 dark:border-neutral-700">
            <h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">自定义语音</h4>
            
            <div class="space-y-3">
              <!-- 录音按钮 -->
              <div class="flex flex-col items-center space-y-2">
                <button 
                  @click="toggleRecording" 
                  class="w-full flex items-center justify-center px-4 py-2 rounded-lg transition-all duration-200"
                  :class="isRecording ? 'bg-red-500 hover:bg-red-600 text-white' : 'bg-primary-600 hover:bg-primary-700 text-white'"
                >
                  <i class="fa-solid" :class="isRecording ? 'fa-stop' : 'fa-microphone'"></i>
                  <span class="ml-2">{{ isRecording ? '停止录音' : '开始录音' }}</span>
                </button>
                
                <div v-if="isRecording" class="text-xs text-neutral-500 dark:text-neutral-400 animate-pulse">
                  正在录音...{{ recordingTime }}秒
                </div>
              </div>
              
              <!-- 或者分割线 -->
              <div class="flex items-center my-3">
                <div class="flex-grow border-t border-neutral-200 dark:border-neutral-700"></div>
                <span class="mx-3 text-xs text-neutral-500 dark:text-neutral-400">或者</span>
                <div class="flex-grow border-t border-neutral-200 dark:border-neutral-700"></div>
              </div>
              
              <!-- 上传语音文件 -->
              <label 
                for="voice-upload" 
                class="flex flex-col items-center justify-center w-full h-24 border-2 border-neutral-300 border-dashed rounded-lg cursor-pointer bg-neutral-50 dark:border-neutral-600 dark:bg-neutral-700 hover:bg-neutral-100 dark:hover:bg-neutral-600 transition-all duration-200"
              >
                <div class="flex flex-col items-center justify-center pt-3 pb-3">
                  <i class="fa-solid fa-file-audio mb-1 text-xl text-neutral-500 dark:text-neutral-400"></i>
                  <p class="text-sm text-neutral-600 dark:text-neutral-300">
                    <span class="font-medium">上传语音文件</span>
                  </p>
                  <p class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">支持 WAV, MP3, M4A 文件 (最大5MB)</p>
                </div>
                <input 
                  id="voice-upload" 
                  ref="voiceInput"
                  type="file" 
                  class="hidden" 
                  @change="handleVoiceUpload" 
                  accept=".wav,.mp3,.m4a,.aac"
                />
              </label>
              
              <!-- 语音预览区域 -->
              <div v-if="voiceFile || form.hasVoice" class="mt-2 space-y-2">
                <div class="flex items-center justify-between text-sm">
                  <div class="flex items-center">
                    <i class="fa-solid fa-file-audio mr-2 text-primary-500 dark:text-primary-400"></i>
                    <span class="text-neutral-700 dark:text-neutral-300 truncate max-w-[180px]">{{ voiceFileName }}</span>
                  </div>
                  
                  <div class="flex items-center space-x-2">
                    <button 
                      v-if="voiceFile"
                      @click="playVoicePreview" 
                      class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 transition-all duration-200"
                    >
                      <i class="fa-solid" :class="isPlaying ? 'fa-pause' : 'fa-play'"></i>
                    </button>
                    
                    <button 
                      @click="removeVoice" 
                      class="w-8 h-8 flex items-center justify-center rounded-full bg-neutral-100 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-600 text-neutral-700 dark:text-neutral-300 transition-all duration-200"
                    >
                      <i class="fa-solid fa-trash-alt"></i>
                    </button>
                  </div>
                </div>
                
                <div v-if="form.hasVoice && !voiceFile" class="text-xs text-green-600 dark:text-green-400">
                  <i class="fa-solid fa-check-circle mr-1"></i>
                  已绑定语音文件（上传新文件将替换现有文件）
                </div>
                
                <!-- 上传进度条 -->
                <div v-if="isVoiceUploading" class="w-full bg-neutral-200 dark:bg-neutral-600 rounded-full h-1.5">
                  <div 
                    class="bg-primary-500 dark:bg-primary-400 h-1.5 rounded-full transition-all duration-300 ease-in-out" 
                    :style="{ width: voiceUploadProgress + '%' }"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 预览区域 -->
          <div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-xl p-4 shadow-sm border border-neutral-200 dark:border-neutral-700">
            <h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">角色预览</h4>
            <div class="space-y-4">
              <!-- 角色形象预览 -->
              <div class="w-full aspect-square rounded-lg bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center border border-neutral-200 dark:border-neutral-700 overflow-hidden">
                <div v-if="form.model === 'xiaozhi'" class="text-center">
                  <div class="mb-2 text-5xl text-primary-500 dark:text-primary-400">
                    <i class="fa-solid fa-robot"></i>
                  </div>
                  <div class="text-sm text-primary-600 dark:text-primary-400">小智</div>
                </div>
                <div v-else-if="form.model === 'nanaA'" class="flex items-center justify-center h-full">
                  <img src="/models/Haru/preview.png" alt="娜娜A" class="max-h-full max-w-full object-contain"/>
                </div>
                <div v-else-if="form.model === 'nanaB'" class="flex items-center justify-center h-full">
                  <img src="/models/Hiyori/preview.png" alt="娜娜B" class="max-h-full max-w-full object-contain"/>
                </div>
                <div v-else-if="form.model === 'nanaC'" class="flex items-center justify-center h-full">
                  <img src="/models/PinkFox/preview.png" alt="娜娜C" class="max-h-full max-w-full object-contain"/>
                </div>
                <div v-else class="text-center">
                  <div class="mb-2 text-5xl text-primary-500 dark:text-primary-400">
                    <i class="fa-solid fa-user"></i>
                  </div>
                  <div class="text-sm text-neutral-500 dark:text-neutral-400">预览不可用</div>
                </div>
              </div>
              
              <!-- 角色信息 -->
              <div class="p-3 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
                <div class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                  {{ form.name || '未命名角色' }}
                </div>
                <div class="text-xs text-neutral-500 dark:text-neutral-400 mt-1 flex flex-wrap gap-1">
                  <span v-for="(tag, index) in selectedTags" :key="index" 
                    :class="[
                      'inline-block px-2 py-0.5 rounded-full text-xs',
                      tagColors[tagOptions.indexOf(tag) % tagColors.length].badge
                    ]">
                    {{ tag }}
                  </span>
                  <span v-if="selectedTags.length === 0" class="text-neutral-400 dark:text-neutral-500">未选择特质</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部按钮栏 -->
      <div class="flex items-center justify-end p-5 border-t border-neutral-200 dark:border-neutral-700 gap-3">
        <button 
          @click="$emit('close')" 
          class="px-5 py-2.5 rounded-lg bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-all duration-200 font-medium"
        >
          取消
        </button>
        <button 
          @click="handleSave" 
          class="px-5 py-2.5 rounded-lg bg-primary-600 hover:bg-primary-700 text-white transition-all duration-200 font-medium flex items-center"
        >
          <i class="fa-solid fa-save mr-2"></i>
          保存角色
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { getApiUrl } from '../utils/api'

const props = defineProps({
  editAgent: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'save'])
const fileInput = ref(null)
const fileName = ref('')
const isUploading = ref(false)
const uploadProgress = ref(0)

// 语音相关
const voiceInput = ref(null)
const voiceFile = ref(null)
const voiceFileName = ref('')
const isVoiceUploading = ref(false)
const voiceUploadProgress = ref(0)
const isRecording = ref(false)
const recordingTime = ref(0)
const recordingInterval = ref(null)
const mediaRecorder = ref(null)
const audioChunks = ref([])
const audioURL = ref(null)
const audioPlayer = ref(null)
const isPlaying = ref(false)
const uploadedVoicePath = ref('')

// 角色标签选项
const tagOptions = [
  '温柔体贴', '阳光活泼', '冷酷高傲', '知性优雅', 
  '单纯天真', '幽默风趣', '古灵精怪', '深沉内敛',
  '率真直爽', '浪漫多情', '神秘莫测', '坚毅果断',
  '温暖治愈', '机智敏锐', '傲娇可爱'
]

// 标签颜色配置
const tagColors = [
  { 
    normal: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-300', 
    selected: 'bg-pink-200 text-pink-800 dark:bg-pink-800/50 dark:text-pink-200',
    badge: 'bg-pink-100 text-pink-700 dark:bg-pink-900/50 dark:text-pink-300'
  },
  { 
    normal: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300', 
    selected: 'bg-blue-200 text-blue-800 dark:bg-blue-800/50 dark:text-blue-200',
    badge: 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
  },
  { 
    normal: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300', 
    selected: 'bg-green-200 text-green-800 dark:bg-green-800/50 dark:text-green-200',
    badge: 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300'
  },
  { 
    normal: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300', 
    selected: 'bg-orange-200 text-orange-800 dark:bg-orange-800/50 dark:text-orange-200',
    badge: 'bg-orange-100 text-orange-700 dark:bg-orange-900/50 dark:text-orange-300'
  },
  { 
    normal: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300', 
    selected: 'bg-purple-200 text-purple-800 dark:bg-purple-800/50 dark:text-purple-200',
    badge: 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300'
  },
  { 
    normal: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300', 
    selected: 'bg-yellow-200 text-yellow-800 dark:bg-yellow-800/50 dark:text-yellow-200',
    badge: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300'
  },
  { 
    normal: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300', 
    selected: 'bg-teal-200 text-teal-800 dark:bg-teal-800/50 dark:text-teal-200',
    badge: 'bg-teal-100 text-teal-700 dark:bg-teal-900/50 dark:text-teal-300'
  },
  { 
    normal: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300', 
    selected: 'bg-red-200 text-red-800 dark:bg-red-800/50 dark:text-red-200',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300'
  },
  { 
    normal: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300', 
    selected: 'bg-indigo-200 text-indigo-800 dark:bg-indigo-800/50 dark:text-indigo-200',
    badge: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/50 dark:text-indigo-300'
  },
  { 
    normal: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300', 
    selected: 'bg-cyan-200 text-cyan-800 dark:bg-cyan-800/50 dark:text-cyan-200',
    badge: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/50 dark:text-cyan-300'
  },
  { 
    normal: 'bg-lime-100 text-lime-700 dark:bg-lime-900/30 dark:text-lime-300', 
    selected: 'bg-lime-200 text-lime-800 dark:bg-lime-800/50 dark:text-lime-200',
    badge: 'bg-lime-100 text-lime-700 dark:bg-lime-900/50 dark:text-lime-300'
  },
  { 
    normal: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-300', 
    selected: 'bg-fuchsia-200 text-fuchsia-800 dark:bg-fuchsia-800/50 dark:text-fuchsia-200',
    badge: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/50 dark:text-fuchsia-300'
  }
]

// 已选中的标签
const selectedTags = ref([])

// 初始化表单数据
const form = ref({
  name: '',
  description: '',
  model: 'linzong',
  personality: '',
  interests: '',
  lifestyle: '',
  values: '',
  // 新增语音文件字段
  voiceFile: '',
  hasVoice: false
})

// 组件挂载时，如果是编辑模式，则填充表单数据
onMounted(async () => {
  if (props.editAgent) {
    // 加载基本信息
    form.value = {
      name: props.editAgent.name || '',
      description: props.editAgent.description || '',
      model: props.editAgent.model || 'nanaA',
      personality: props.editAgent.personality || '',
      interests: props.editAgent.interests || '',
      lifestyle: props.editAgent.lifestyle || '',
      values: props.editAgent.values || ''
    }
    
    // 处理已有标签
    if (props.editAgent.description) {
      try {
        // 尝试从描述中提取标签，假设格式为: "标签1,标签2,标签3"
        const existingTags = props.editAgent.description.split(',')
          .map(tag => tag.trim())
          .filter(tag => tagOptions.includes(tag))
        
        // 只保留有效的标签，且最多4个
        selectedTags.value = existingTags.slice(0, 4)
      } catch (e) {
        console.error('解析标签失败', e)
        selectedTags.value = []
      }
    }
    
    // 尝试加载语音文件信息
    try {
      // 为了确保获取最新的agent配置，直接请求后端
      console.log('正在获取agent配置，ID:', props.editAgent.id)
      const response = await fetch(getApiUrl(`get_agent_config?agent_id=${props.editAgent.id}`))
      const data = await response.json()
      
      console.log('获取到的agent配置:', data)
      
      if (data.success && data.config && data.config.voice_file) {
        // 如果有voice_file，显示语音文件名
        const voiceFilePath = data.config.voice_file
        const fileName = voiceFilePath.split('/').pop() // 提取文件名
        
        console.log('检测到语音文件:', fileName, '路径:', voiceFilePath)
        
        // 设置语音预览信息（不上传文件，仅显示信息）
        voiceFileName.value = fileName || '已配置语音文件.wav'
        // 标记已有语音文件
        form.value.hasVoice = true
      } else {
        console.log('未检测到语音文件:', data)
        if (data.config) {
          console.log('配置中的字段:', Object.keys(data.config))
        }
      }
    } catch (error) {
      console.error('加载语音文件信息失败:', error)
    }
  }
})

// 处理文件上传
const handleFileUpload = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  fileName.value = file.name
  isUploading.value = true
  uploadProgress.value = 10  // 开始上传
  
  const formData = new FormData()
  formData.append('file', file)
  
  try {
    // 模拟上传进度
    const progressInterval = setInterval(() => {
      if (uploadProgress.value < 90) {
        uploadProgress.value += 10
      }
    }, 200)
    
    const response = await fetch(getApiUrl('extract_agent_info'), {
      method: 'POST',
      body: formData,
    })
    
    clearInterval(progressInterval)
    uploadProgress.value = 100  // 上传完成
    
    const data = await response.json()
    
    if (data.success) {
      // 填充表单数据
      if (data.name) form.value.name = data.name
      if (data.personality) form.value.personality = data.personality
      if (data.interests) form.value.interests = data.interests
      if (data.lifestyle) form.value.lifestyle = data.lifestyle
      if (data.values) form.value.values = data.values
      
      // 处理标签
      if (data.tags && Array.isArray(data.tags)) {
        // 只保留有效的标签，且最多4个
        selectedTags.value = data.tags
          .filter(tag => tagOptions.includes(tag))
          .slice(0, 4)
      }
      
      // 显示成功消息 - 使用 toast 通知
      const toastEl = document.createElement('div')
      toastEl.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in'
      toastEl.textContent = '文件解析成功，已自动填充表单'
      document.body.appendChild(toastEl)
      
      setTimeout(() => {
        toastEl.remove()
      }, 3000)
    } else {
      // 显示错误消息 - 使用 toast 通知
      const toastEl = document.createElement('div')
      toastEl.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in'
      toastEl.textContent = '解析文件失败: ' + data.message
      document.body.appendChild(toastEl)
      
      setTimeout(() => {
        toastEl.remove()
      }, 3000)
    }
  } catch (error) {
    console.error('文件上传错误:', error)
    // 显示错误消息 - 使用 toast 通知
    const toastEl = document.createElement('div')
    toastEl.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in'
    toastEl.textContent = '文件上传失败，请重试'
    document.body.appendChild(toastEl)
    
    setTimeout(() => {
      toastEl.remove()
    }, 3000)
  } finally {
    // 不管成功或失败，3秒后重置上传状态
    setTimeout(() => {
      isUploading.value = false
      uploadProgress.value = 0
    }, 3000)
  }
}

// 切换标签选择状态
const toggleTag = (tag) => {
  if (selectedTags.value.includes(tag)) {
    // 如果已选中，则移除
    selectedTags.value = selectedTags.value.filter(t => t !== tag)
  } else {
    // 如果未选中且未超过4个，则添加
    if (selectedTags.value.length < 4) {
      selectedTags.value.push(tag)
    } else {
      // 显示提示消息 - 使用 toast 通知
      const toastEl = document.createElement('div')
      toastEl.className = 'fixed bottom-4 right-4 bg-yellow-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in'
      toastEl.textContent = '最多只能选择4个标签'
      document.body.appendChild(toastEl)
      
      setTimeout(() => {
        toastEl.remove()
      }, 3000)
    }
  }
}

// 语音相关方法
const toggleRecording = async () => {
  if (isRecording.value) {
    stopRecording()
  } else {
    await startRecording()
  }
}

const startRecording = async () => {
  try {
    // 如果已经有上传的文件，先移除
    if (voiceFile.value) {
      removeVoice()
    }
    
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    mediaRecorder.value = new MediaRecorder(stream)
    audioChunks.value = []
    
    mediaRecorder.value.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.value.push(event.data)
      }
    }
    
    mediaRecorder.value.onstop = () => {
      // 创建音频Blob并保存
      const audioBlob = new Blob(audioChunks.value, { type: 'audio/wav' })
      
      // 检查文件大小
      if (audioBlob.size > 5 * 1024 * 1024) {
        alert('录音文件超过5MB大小限制，请录制较短的音频。')
        return
      }
      
      if (audioURL.value) {
        URL.revokeObjectURL(audioURL.value)
      }
      
      audioURL.value = URL.createObjectURL(audioBlob)
      
      // 创建File对象
      const file = new File([audioBlob], 'recording.wav', { type: 'audio/wav' })
      
      // 保存文件并显示预览
      voiceFile.value = file
      voiceFileName.value = '录音.wav'
      
      // 自动上传录音文件
      uploadVoiceFile(file)
    }
    
    // 开始录制
    mediaRecorder.value.start()
    isRecording.value = true
    recordingTime.value = 0
    
    // 设置计时器
    recordingInterval.value = setInterval(() => {
      recordingTime.value++
      
      // 限制录音时长最多60秒
      if (recordingTime.value >= 60) {
        stopRecording()
      }
    }, 1000)
  } catch (error) {
    console.error('录音初始化失败', error)
    alert('无法访问麦克风，请确保已授予麦克风权限。')
  }
}

const stopRecording = () => {
  if (mediaRecorder.value && mediaRecorder.value.state === 'recording') {
    mediaRecorder.value.stop()
    
    // 停止所有音轨
    if (mediaRecorder.value.stream) {
      mediaRecorder.value.stream.getTracks().forEach(track => track.stop())
    }
  }
  
  // 清除计时器
  if (recordingInterval.value) {
    clearInterval(recordingInterval.value)
    recordingInterval.value = null
  }
  
  isRecording.value = false
}

const handleVoiceUpload = (event) => {
  // 获取上传的文件
  const file = event.target.files[0]
  
  if (!file) return
  
  // 检查文件类型
  const allowedTypes = ['audio/wav', 'audio/mpeg', 'audio/mp4', 'audio/aac']
  const fileType = file.type
  
  if (!allowedTypes.includes(fileType) && 
      !file.name.endsWith('.wav') && 
      !file.name.endsWith('.mp3') && 
      !file.name.endsWith('.m4a') && 
      !file.name.endsWith('.aac')) {
    alert('请上传WAV、MP3、M4A或AAC格式的音频文件')
    event.target.value = null
    return
  }
  
  // 检查文件大小
  if (file.size > 5 * 1024 * 1024) {
    alert('文件大小不能超过5MB')
    event.target.value = null
    return
  }
  
  // 如果已经有录音，先移除
  if (voiceFile.value) {
    removeVoice()
  }
  
  // 保存文件
  voiceFile.value = file
  voiceFileName.value = file.name
  
  // 上传文件
  uploadVoiceFile(file)
  
  // 重置文件输入
  event.target.value = null
}

const uploadVoiceFile = async (file) => {
  try {
    isVoiceUploading.value = true
    voiceUploadProgress.value = 0
    
    // 创建FormData对象
    const formData = new FormData()
    formData.append('file', file)
    
    // 如果是编辑模式，添加agent_id
    if (props.editAgent) {
      formData.append('agent_id', props.editAgent.id)
    }
    
    // 创建模拟进度更新
    const progressInterval = setInterval(() => {
      if (voiceUploadProgress.value < 90) {
        voiceUploadProgress.value += 5
      }
    }, 200)
    
    // 上传文件
    const response = await fetch(getApiUrl('upload_custom_voice'), {
      method: 'POST',
      body: formData
    })
    
    // 清除进度更新
    clearInterval(progressInterval)
    
    // 设置进度为100%
    voiceUploadProgress.value = 100
    
    // 处理响应
    const result = await response.json()
    
    if (result.success) {
      // 保存上传后的文件路径
      uploadedVoicePath.value = result.file_name
      
      // 延迟隐藏进度条
      setTimeout(() => {
        isVoiceUploading.value = false
      }, 500)
    } else {
      alert(`上传失败: ${result.message}`)
      isVoiceUploading.value = false
      removeVoice()
    }
  } catch (error) {
    console.error('上传语音文件失败', error)
    alert('上传语音文件失败，请重试')
    isVoiceUploading.value = false
    removeVoice()
  }
}

const playVoicePreview = () => {
  if (!audioURL.value && voiceFile.value) {
    // 如果没有audioURL但有voiceFile，创建URL
    audioURL.value = URL.createObjectURL(voiceFile.value)
  }
  
  if (!audioURL.value) return
  
  if (!audioPlayer.value) {
    audioPlayer.value = new Audio(audioURL.value)
    
    audioPlayer.value.onended = () => {
      isPlaying.value = false
    }
    
    audioPlayer.value.onpause = () => {
      isPlaying.value = false
    }
  }
  
  if (isPlaying.value) {
    audioPlayer.value.pause()
    isPlaying.value = false
  } else {
    audioPlayer.value.play()
    isPlaying.value = true
  }
}

const removeVoice = () => {
  // 停止播放
  if (audioPlayer.value) {
    audioPlayer.value.pause()
    audioPlayer.value = null
  }
  
  // 释放URL
  if (audioURL.value) {
    URL.revokeObjectURL(audioURL.value)
    audioURL.value = null
  }
  
  // 清除文件
  voiceFile.value = null
  voiceFileName.value = ''
  uploadedVoicePath.value = ''
  isPlaying.value = false
  
  // 如果是编辑模式且有已绑定的语音，标记为需要删除
  if (form.value.hasVoice) {
    form.value.hasVoice = false
    form.value.removeVoice = true
    
    // 如果是编辑模式，显示确认消息
    if (props.editAgent && props.editAgent.id) {
      console.log('已标记移除现有语音文件')
    }
  }
}

// 组件销毁前清理
onBeforeUnmount(() => {
  // 停止录音
  if (isRecording.value) {
    stopRecording()
  }
  
  // 停止播放
  if (audioPlayer.value) {
    audioPlayer.value.pause()
    audioPlayer.value = null
  }
  
  // 释放URL
  if (audioURL.value) {
    URL.revokeObjectURL(audioURL.value)
    audioURL.value = null
  }
})

// 修改保存方法，加入语音绑定
const handleSave = async () => {
  // 验证表单
  if (!form.value.name.trim()) {
    alert('请输入角色名称')
    return
  }
  
  // 创建保存的对象
  const agent = {
    name: form.value.name,
    description: form.value.description || selectedTags.value.join('，'),
    model: form.value.model,
    personality: form.value.personality,
    interests: form.value.interests,
    lifestyle: form.value.lifestyle,
    values: form.value.values
  }
  
  try {
    // 首先保存角色信息
    await emit('save', agent)
    
    // 确定当前agent_id
    const agentId = props.editAgent ? props.editAgent.id : null
    
    // 如果没有agent_id，无法处理语音文件
    if (!agentId) {
      console.log('无法处理语音文件：缺少agent_id')
      return
    }
    
    // 处理语音文件
    if (form.value.removeVoice) {
      // 如果需要删除现有语音
      try {
        console.log('正在删除语音文件...')
        const response = await fetch(getApiUrl(`remove_agent_voice?agent_id=${agentId}`))
        const result = await response.json()
        console.log('删除语音结果:', result)
      } catch (error) {
        console.error('删除语音失败:', error)
      }
    } else if (uploadedVoicePath.value) {
      // 如果有新上传的语音，绑定到角色
      console.log('正在绑定语音文件:', uploadedVoicePath.value)
      
      // 使用URLSearchParams而非FormData，确保voice_file作为字符串传递
      const formData = new URLSearchParams();
      formData.append('agent_id', agentId);
      formData.append('voice_file', uploadedVoicePath.value);
      
      // 绑定语音到角色
      const response = await fetch(getApiUrl('bind_voice_to_agent'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        body: formData
      });
      
      const result = await response.json()
      console.log('语音绑定结果:', result);
      
      if (!result.success) {
        console.error('绑定语音失败:', result.message);
        alert(`绑定语音失败: ${result.message}`);
        // 不阻止窗口关闭，仅记录错误
      } else {
        console.log('成功绑定语音文件:', result.voice_path);
      }
    } else {
      // 没有语音文件的变更
      console.log('保留现有语音设置')
    }
  } catch (error) {
    console.error('保存角色失败', error)
    alert('保存角色失败，请重试')
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

/* 确保表单输入在深色模式下文本颜色正确 */
:deep(input), :deep(textarea), :deep(select) {
  color-scheme: light dark;
}

/* 自定义滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background-color: rgba(156, 163, 175, 0.5);
  border-radius: 8px;
}

::-webkit-scrollbar-thumb:hover {
  background-color: rgba(156, 163, 175, 0.7);
}
</style> 