import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: '0.0.0.0',    // 明确指定监听所有地址
    port: 5173,         // 指定端口
    strictPort: true,   // 端口被占用时直接报错
    cors: true,  
  },
  plugins: [vue()],
})
