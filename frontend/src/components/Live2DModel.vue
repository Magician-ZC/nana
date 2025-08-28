<template>
  <div ref="pixiContainer" class="live2d-container"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as PIXI from 'pixi.js'
import { Live2DModel } from 'pixi-live2d-display/cubism4'

// 将 PIXI 暴露到 window 上
window.PIXI = PIXI

const props = defineProps({
  modelId: {
    type: String,
    default: 'linzong'
  }
})

const MODEL_PATHS = {
  linzong: '/models/Lin/Lin.model3.json',
  xiaozhi: '/models/xiaozhi/xiaozhi.model3.json',
  nanaA: '/models/Haru/Haru.model3.json',
  nanaB: '/models/Hiyori/Hiyori.model3.json',
  nanaC: '/models/PinkFox/PinkFox.model3.json',
}

// 表情映射对象，使用中文作为 key
const EXPRESSIONS = {
  '吐舌': 'key2',
  '黑脸': 'key3',
  '眼泪': 'key4',
  '脸红': 'key5',
  'nn眼': 'key6',
  '生气瘪嘴': 'key7',
  '死鱼眼': 'key8',
  '生气': 'key9',
  '咪咪眼': 'key10',
  '嘟嘴': 'key11',
  '钱钱眼': 'key12',
  '爱心': 'key16',
  '泪眼': 'key17',
  // 新增角色相关表情
  '酷酷': 'key8',    // 用死鱼眼表示酷酷的表情
  '开心': 'key16',   // 用爱心表示开心
  '害羞': 'key5',    // 用脸红表示害羞
  '傲娇': 'key11',   // 用嘟嘴表示傲娇
  '惊讶': 'key4',    // 用眼泪表示惊讶
  '困惑': 'key3',    // 用黑脸表示困惑
  '兴奋': 'key12'    // 用钱钱眼表示兴奋
}

const pixiContainer = ref(null)
const app = ref(null)
const model = ref(null)
const currentModel = ref(props.modelId)
const isLoading = ref(false)

// 监听modelId变化
watch(() => props.modelId, (newModelId, oldModelId) => {
  console.log(`模型ID变更: ${oldModelId} => ${newModelId}`)
  if (newModelId && newModelId !== currentModel.value && !isLoading.value) {
    currentModel.value = newModelId
    loadModel(newModelId)
  }
}, { immediate: true }) // 添加immediate确保首次加载时也会执行

// 加载模型的方法
const loadModel = async (modelId) => {
  if (!app.value || isLoading.value) return
  
  console.log(`开始加载模型: ${modelId}`)
  isLoading.value = true
  
  // 移除当前模型 - 彻底清理
  if (model.value) {
    try {
      // 先移除事件监听
      model.value.removeAllListeners()
      
      // 从舞台移除
      if (model.value.parent) {
        model.value.parent.removeChild(model.value)
      }
      
      // 销毁模型
      await model.value.destroy()
      model.value = null
      
      // 清理舞台上可能残留的所有其他显示对象
      while (app.value.stage.children.length > 0) {
        const child = app.value.stage.children[0]
        app.value.stage.removeChild(child)
        if (typeof child.destroy === 'function') {
          child.destroy()
        }
      }
    } catch (e) {
      console.error('清理旧模型出错:', e)
    }
  }
  
  // 尝试完全重建PIXI应用以确保彻底清理
  try {
    // 销毁旧的应用
    if (app.value) {
      app.value.destroy(true, { children: true, texture: true, baseTexture: true })
    }
    
    // 清空容器
    if (pixiContainer.value) {
      while (pixiContainer.value.firstChild) {
        pixiContainer.value.removeChild(pixiContainer.value.firstChild)
      }
    }
    
    // 创建新的应用
    const newApp = new PIXI.Application({
      width: window.innerWidth,
      height: window.innerHeight,
      transparent: true,
      backgroundAlpha: 0,
      resizeTo: window,
      antialias: true
    })
    app.value = newApp
    pixiContainer.value.appendChild(newApp.view)
  } catch (e) {
    console.error('重建PIXI应用出错:', e)
  }
  
  try {
    const modelPath = MODEL_PATHS[modelId] || MODEL_PATHS.nanaA
    console.log(`加载模型路径: ${modelPath}`)
    
    // 添加一个加载指示文本
    if (app.value) {
      const loadingText = new PIXI.Text('正在加载模型...', {
        fill: 0x333333,
        fontSize: 24,
        fontWeight: 'bold',
        stroke: 0xffffff,
        strokeThickness: 2
      })
      loadingText.anchor.set(0.5)
      loadingText.x = app.value.view.width / 2
      loadingText.y = app.value.view.height / 2
      app.value.stage.addChild(loadingText)
    }
    
    const newModel = await Live2DModel.from(modelPath)
    
    // 清除加载文本
    if (app.value && app.value.stage.children.length > 0) {
      app.value.stage.removeChild(app.value.stage.children[0])
    }
    
    if (!app.value) {
      // 如果在加载过程中应用被销毁，则不继续
      newModel.destroy()
      isLoading.value = false
      return
    }
    
    model.value = newModel
    
    // 设置模型位置和缩放
    const scale = Math.min(
      app.value.view.width / model.value.width,
      app.value.view.height / model.value.height
    ) * 0.8  // 使用80%的最大缩放比例
    
    model.value.scale.set(scale, scale)
    model.value.anchor.set(0.5, 0.5)
    model.value.x = app.value.view.width / 2
    model.value.y = app.value.view.height / 2
    
    // 启用追踪
    model.value.autoInteract = true
    
    // 启用随机动作
    model.value.internalModel.motionManager.settings.autoAddRandomMotion = true
    
    // 添加到舞台
    app.value.stage.addChild(model.value)
    
    console.log('模型加载成功!')
  } catch (error) {
    console.error('加载模型出错:', error)
  } finally {
    isLoading.value = false
  }
}

// 显示表情的方法
const showExpression = (expression, active = true) => {
  if (model.value) {
    // 如果是重置表情请求，或者是取消表情
    if (expression === 'default' || !active) {
      // 重置所有表情参数
      Object.values(EXPRESSIONS).forEach(expressionId => {
        try {
          model.value.internalModel.coreModel.setParameterValueById(
            expressionId, 
            0
          )
        } catch (e) {
          // 忽略不存在的表情参数
        }
      })
      return
    }
    
    // 先重置所有表情
    Object.values(EXPRESSIONS).forEach(expressionId => {
      try {
        model.value.internalModel.coreModel.setParameterValueById(
          expressionId, 
          0
        )
      } catch (e) {
        // 忽略不存在的表情参数
      }
    })
    
    // 然后设置当前表情
    const expressionId = EXPRESSIONS[expression]
    if (expressionId) {
      model.value.internalModel.coreModel.setParameterValueById(
        expressionId, 
        1
      )
      console.log(`设置表情: ${expression}(${expressionId}) => ${active ? '开启' : '关闭'}`)
    } else {
      console.warn(`未知的表情: ${expression}`)
    }
  }
}

// 设置跟踪功能
const setTracking = (enabled) => {
  if (model.value) {
    model.value.autoInteract = enabled
    model.value.internalModel.motionManager.settings.autoAddRandomMotion = enabled
    console.log(`模型跟踪功能已${enabled ? '开启' : '关闭'}~`)
  }
}

// 暴露方法给父组件
defineExpose({
  showExpression,
  setTracking,
  changeModel: (modelId) => {
    console.log(`changeModel被调用: ${currentModel.value} => ${modelId}`)
    if (modelId && modelId !== currentModel.value && !isLoading.value) {
      currentModel.value = modelId
      loadModel(modelId)
      return true
    }
    return false
  }
})

// 调整窗口大小的处理函数
const handleResize = () => {
  if (app.value && model.value) {
    // 更新模型位置
    model.value.x = app.value.view.width / 2
    model.value.y = app.value.view.height / 2
    
    // 更新模型缩放
    const scale = Math.min(
      app.value.view.width / model.value.width,
      app.value.view.height / model.value.height
    ) * 0.8
    
    model.value.scale.set(scale, scale)
  }
}

onMounted(() => {
  // 创建PIXI应用
  app.value = new PIXI.Application({
    width: window.innerWidth,
    height: window.innerHeight,
    transparent: true,
    backgroundAlpha: 0,
    resizeTo: window,
    antialias: true
  })
  
  // 添加到DOM
  pixiContainer.value.appendChild(app.value.view)
  
  // 加载初始模型
  loadModel(currentModel.value)
  
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  // 移除窗口大小变化监听
  window.removeEventListener('resize', handleResize)
  
  // 销毁模型
  if (model.value) {
    model.value.destroy()
    model.value = null
  }
  
  // 销毁PIXI应用
  if (app.value) {
    app.value.destroy(true, { children: true, texture: true, baseTexture: true })
    app.value = null
  }
})
</script>

<style scoped>
.live2d-container {
  width: 100%;
  height: 100%;
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 1;
  background-color: transparent;
}
</style> 