import { useLayoutEffect, useRef, forwardRef, useImperativeHandle, useState, useEffect } from 'react'
import * as PIXI from 'pixi.js'
import { Live2DModel } from 'pixi-live2d-display/cubism4'

// 将 PIXI 暴露到 window 上
window.PIXI = PIXI;

const MODEL_PATHS = {
  nanaA: '/models/Haru/Haru.model3.json',
  nanaB: '/models/Hiyori/Hiyori.model3.json',
  nanaC: '/models/PinkFox/PinkFox.model3.json'
}

const Live2DDisplay = forwardRef((props, ref) => {
  const pixiContainerRef = useRef(null)
  const appRef = useRef(null)
  const modelRef = useRef(null)
  const [currentModel, setCurrentModel] = useState(props.modelId || 'nanaA')
  const [isLoading, setIsLoading] = useState(false)

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

  // 当modelId发生变化时，切换模型
  useEffect(() => {
    if (props.modelId && props.modelId !== currentModel && !isLoading) {
      setCurrentModel(props.modelId)
      loadModel(props.modelId)
    }
  }, [props.modelId, isLoading])

  // 暴露方法给父组件
  useImperativeHandle(ref, () => ({
    // 使用中文参数的表情方法
    showExpression: (expression, active = true) => {
      if (modelRef.current) {
        // 如果是重置表情请求，或者是取消表情
        if (expression === 'default' || !active) {
          // 重置所有表情参数
          Object.values(EXPRESSIONS).forEach(expressionId => {
            try {
              modelRef.current.internalModel.coreModel.setParameterValueById(
                expressionId, 
                0
              )
            } catch (e) {
              // 忽略不存在的表情参数
            }
          });
          return;
        }
        
        // 先重置所有表情
        Object.values(EXPRESSIONS).forEach(expressionId => {
          try {
            modelRef.current.internalModel.coreModel.setParameterValueById(
              expressionId, 
              0
            )
          } catch (e) {
            // 忽略不存在的表情参数
          }
        });
        
        // 然后设置当前表情
        const expressionId = EXPRESSIONS[expression]
        if (expressionId) {
          modelRef.current.internalModel.coreModel.setParameterValueById(
            expressionId, 
            1
          )
          console.log(`设置表情: ${expression}(${expressionId}) => ${active ? '开启' : '关闭'}`)
        } else {
          console.warn(`未知的表情: ${expression}`)
        }
      }
    },
    
    // 设置跟踪功能
    setTracking: (enabled) => {
      if (modelRef.current) {
        modelRef.current.autoInteract = enabled;
        modelRef.current.internalModel.motionManager.settings.autoAddRandomMotion = enabled;
        console.log(`模型跟踪功能已${enabled ? '开启' : '关闭'}~`);
      }
    },
    
    // 切换模型
    changeModel: (modelId) => {
      if (modelId && modelId !== currentModel && !isLoading) {
        setCurrentModel(modelId)
        loadModel(modelId)
      }
    }
  }))
  
  // 加载模型的方法
  const loadModel = async (modelId) => {
    if (!appRef.current || isLoading) return
    
    setIsLoading(true)
    
    // 移除当前模型 - 彻底清理
    if (modelRef.current) {
      try {
        // 先移除事件监听
        modelRef.current.removeAllListeners()
        
        // 从舞台移除
        if (modelRef.current.parent) {
          modelRef.current.parent.removeChild(modelRef.current)
        }
        
        // 销毁模型
        await modelRef.current.destroy()
        modelRef.current = null
        
        // 清理舞台上可能残留的所有其他显示对象
        while (appRef.current.stage.children.length > 0) {
          const child = appRef.current.stage.children[0]
          appRef.current.stage.removeChild(child)
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
      if (appRef.current) {
        appRef.current.destroy(true, { children: true, texture: true, baseTexture: true })
      }
      
      // 清空容器
      if (pixiContainerRef.current) {
        while (pixiContainerRef.current.firstChild) {
          pixiContainerRef.current.removeChild(pixiContainerRef.current.firstChild)
        }
      }
      
      // 创建新的应用
      const app = new PIXI.Application({
        width: window.innerWidth,
        height: window.innerHeight,
        backgroundColor: 0x000000,
        resizeTo: window,
        antialias: true,
      })
      appRef.current = app
      pixiContainerRef.current.appendChild(app.view)
    } catch (e) {
      console.error('重建PIXI应用出错:', e)
    }
    
    try {
      const modelPath = MODEL_PATHS[modelId] || MODEL_PATHS.nanaA
      console.log(`加载模型: ${modelPath}`)
      
      // 添加一个加载指示文本
      if (appRef.current) {
        const loadingText = new PIXI.Text('正在加载模型...', {
          fill: 0xffffff,
          fontSize: 24
        })
        loadingText.anchor.set(0.5)
        loadingText.x = appRef.current.view.width / 2
        loadingText.y = appRef.current.view.height / 2
        appRef.current.stage.addChild(loadingText)
      }
      
      const model = await Live2DModel.from(modelPath)
      
      // 清除加载文本
      if (appRef.current && appRef.current.stage.children.length > 0) {
        const loadingText = appRef.current.stage.children[0]
        appRef.current.stage.removeChild(loadingText)
        loadingText.destroy()
      }
      
      // 确保应用仍然存在（防止在加载过程中组件被卸载）
      if (!appRef.current) {
        model.destroy()
        setIsLoading(false)
        return
      }
      
      // 如果加载成功，设置为当前模型
      modelRef.current = model
      
      // 设置模型的初始跟踪状态
      model.internalModel.motionManager.settings.autoAddRandomMotion = true
      model.autoInteract = true
      model.draggable = false
      
      const scale = Math.min(
        appRef.current.view.width / model.width * 1.8,
        appRef.current.view.height / model.height * 1.8
      )
      model.scale.set(scale)
      
      model.x = appRef.current.view.width / 2
      model.y = appRef.current.view.height * 0.9
      model.anchor.set(0.5, 0.5)

      appRef.current.stage.addChild(model)

      model.on('hit', (hitAreas) => {
        console.log('Hit:', hitAreas)
        model.motion('TapBody')
      })
    } catch (error) {
      console.error('Error loading model:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useLayoutEffect(() => {
    // 确保清理之前的内容
    if (appRef.current) {
      // 清理舞台上的所有显示对象
      while (appRef.current.stage && appRef.current.stage.children.length > 0) {
        const child = appRef.current.stage.children[0]
        appRef.current.stage.removeChild(child)
        if (typeof child.destroy === 'function') {
          child.destroy()
        }
      }
      
      appRef.current.destroy(true, { children: true, texture: true, baseTexture: true })
      appRef.current = null
    }
    
    if (pixiContainerRef.current) {
      while (pixiContainerRef.current.firstChild) {
        pixiContainerRef.current.removeChild(pixiContainerRef.current.firstChild)
      }
    }

    if (!pixiContainerRef.current) return

    const app = new PIXI.Application({
      width: window.innerWidth,
      height: window.innerHeight,
      backgroundColor: 0x000000,
      resizeTo: window,
      antialias: true,
    })
    appRef.current = app
    pixiContainerRef.current.appendChild(app.view)

    let isDestroyed = false

    ;(async function() {
      if (isDestroyed || !appRef.current) return
      await loadModel(currentModel)
    })()

    return () => {
      isDestroyed = true
      if (modelRef.current) {
        try {
          modelRef.current.removeAllListeners()
          modelRef.current.destroy()
          modelRef.current = null
        } catch (e) {
          console.error('销毁模型出错:', e)
        }
      }
      if (appRef.current) {
        appRef.current.destroy(true, { children: true, texture: true, baseTexture: true })
        appRef.current = null
      }
    }
  }, [])

  return <div ref={pixiContainerRef} className="live2d-container"></div>
})

export default Live2DDisplay 