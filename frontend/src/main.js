import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useUserStore } from './stores/user'
import { useChatStore } from './stores/chat'

const app = createApp(App)
// 安装pinia插件
const pinia = createPinia()
app.use(pinia)
app.use(router)

// 初始化应用后，初始化用户认证token
const userStore = useUserStore(pinia)
userStore.initializeSession()

// 初始化聊天存储
const chatStore = useChatStore(pinia)
// 延迟初始化聊天，确保用户信息已加载
setTimeout(() => {
  chatStore.initializeChat()
  console.log('聊天存储已初始化')
}, 100)

console.log('应用程序已启动，auth_token已初始化')

app.mount('#app') 