import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

// 检查SSL证书是否存在
const sslDir = '../backend/ssl'
const certFile = path.resolve(sslDir, 'server.crt')
const keyFile = path.resolve(sslDir, 'server.key')

let httpsConfig = undefined

// 检查证书是否存在
if (fs.existsSync(certFile) && fs.existsSync(keyFile)) {
  try {
    httpsConfig = {
      cert: fs.readFileSync(certFile),
      key: fs.readFileSync(keyFile)
    }
    console.log('已加载SSL证书，将使用HTTPS启动服务器')
  } catch (err) {
    console.error('加载SSL证书失败:', err)
  }
} else {
  console.warn('SSL证书未找到，将使用HTTP启动服务器')
}

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: '0.0.0.0',    // 明确指定监听所有地址
    port: 5173,         // 指定端口
    strictPort: true,   // 端口被占用时直接报错
    cors: true,
    https: httpsConfig,  // 使用SSL证书启动HTTPS
    hmr: {
      protocol: httpsConfig ? 'wss' : 'ws' // 根据HTTPS状态自动选择WebSocket协议
    },
    // 显示详细启动信息
    logger: {
      prefix: '[vite]',
      timestamp: true,
      clearScreen: false
    },
    // 添加代理配置
    proxy: {
      // 移除了代理配置，因为我们现在直接使用WSS连接
    }
  },
  plugins: [vue()],
  // 显式开启源映射
  build: {
    sourcemap: true
  },
  // 改进WebSocket连接，减少断开
  optimizeDeps: {
    include: ['vue', 'pinia', 'lodash']
  }
})
