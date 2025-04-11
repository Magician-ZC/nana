import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { useUserStore } from './stores/user'

const app = createApp(App)
// 安装pinia插件
const pinia = createPinia()
app.use(pinia)

// 初始化应用后，初始化用户认证token
const userStore = useUserStore(pinia)
userStore.initializeToken()

console.log('应用程序已启动，auth_token已初始化')

app.mount('#app') 