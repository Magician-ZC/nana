import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import fs from 'fs'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: '0.0.0.0',    // 明确指定监听所有地址
    port: 5173,         // 指定端口
    strictPort: true,   // 端口被占用时直接报错
    cors: true,
    https: {
      key: fs.readFileSync(path.resolve(__dirname, 'server.key')),
      cert: fs.readFileSync(path.resolve(__dirname, 'server.crt')),
    },
    proxy: {
      // 将对API的请求代理到后端服务器
      '/api': {
        target: 'http://192.168.3.51:8666',
        changeOrigin: true,
        secure: false, // 不验证SSL证书
        rewrite: (path) => path
      }
    }
  },
  plugins: [
    vue()
  ],
})
