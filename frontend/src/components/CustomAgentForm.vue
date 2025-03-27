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
          
          <!-- 预览区域 -->
          <div class="bg-neutral-50 dark:bg-neutral-700/50 rounded-xl p-4 shadow-sm border border-neutral-200 dark:border-neutral-700">
            <h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">角色预览</h4>
            <div class="space-y-4">
              <!-- 角色形象预览 -->
              <div class="w-full aspect-square rounded-lg bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center border border-neutral-200 dark:border-neutral-700 overflow-hidden">
                <div v-if="form.model === 'nanaA'" class="flex items-center justify-center h-full">
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
import { ref, onMounted } from 'vue'

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

const form = ref({
  name: '',
  description: '', // 将存储选中的标签
  model: 'nanaA',
  personality: '',
  interests: '',
  lifestyle: '',
  values: ''
})

// 组件挂载时，如果是编辑模式，则填充表单数据
onMounted(() => {
  if (props.editAgent) {
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
    
    const response = await fetch('http://localhost:8666/api/extract_agent_info', {
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

const handleSave = () => {
  if (!form.value.name) {
    // 显示提示消息 - 使用 toast 通知
    const toastEl = document.createElement('div')
    toastEl.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 animate-fade-in'
    toastEl.textContent = '请填写角色名称'
    document.body.appendChild(toastEl)
    
    setTimeout(() => {
      toastEl.remove()
    }, 3000)
    return
  }
  
  // 将选中的标签组合为描述
  form.value.description = selectedTags.value.join(', ')
  
  emit('save', { ...form.value })
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