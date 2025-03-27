<template>
  <div class="time-weather-container">
    <div class="weather-row">
      <!-- 桌面端显示完整信息 -->
      <template v-if="!isMobile">
        <span class="date">{{ currentDate }} {{ weekDay }}</span>
        <span class="divider">|</span>
      </template>
      
      <!-- 所有端都显示地区和天气 -->
      <span class="location">{{ weather.city }}</span>
      <span class="weather-icon">
        <svg v-if="weather.condition === 'sunny'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
        <svg v-else-if="weather.condition === 'cloudy'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 7l.2.02a4.5 4.5 0 0 1 4.3 4.5c0 2.5-1.9 4.5-4.3 4.5H7l-.2-.02A4.5 4.5 0 0 1 2.5 11.5C2.5 9 4.4 7 6.8 7H17z"></path>
        </svg>
        <svg v-else-if="weather.condition === 'rainy'" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 16.2A4.5 4.5 0 0 0 17.5 8h-1.8A7 7 0 1 0 4 14.9"></path>
          <path d="M16 14v6"></path>
          <path d="M8 14v6"></path>
          <path d="M12 16v6"></path>
        </svg>
      </span>
      <span class="condition">{{ weather.conditionText }}</span>
      <span class="temp">{{ weather.temperature }}°C</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const currentDate = ref('')
const weekDay = ref('')
const isMobile = ref(false)
const weather = ref({
  temperature: 25,
  condition: 'sunny', // 可选值: sunny, cloudy, rainy
  conditionText: '晴朗',
  city: '北京'
})

// 检测是否为移动设备
const checkMobileDevice = () => {
  isMobile.value = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
};

// 星期对照表
const WEEKDAYS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']

// 更新时间和日期函数
const updateDateTime = () => {
  const now = new Date()
  
  // 更新日期
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  currentDate.value = `${year}.${month}.${day}`
  
  // 更新星期
  weekDay.value = WEEKDAYS[now.getDay()]
}

// 获取天气信息
const fetchWeather = async () => {
  try {
    // 这里可以替换为实际的天气API调用
    // const response = await fetch('your-weather-api-url')
    // const data = await response.json()
    
    // 模拟天气数据
    setTimeout(() => {
      const conditions = [
        { id: 'sunny', text: '晴朗' },
        { id: 'cloudy', text: '多云' },
        { id: 'rainy', text: '小雨' }
      ]
      const cities = ['北京', '上海', '广州', '深圳']
      
      const selectedCondition = conditions[Math.floor(Math.random() * conditions.length)]
      
      weather.value = {
        temperature: Math.floor(Math.random() * 15) + 15, // 15-30度
        condition: selectedCondition.id,
        conditionText: selectedCondition.text,
        city: cities[Math.floor(Math.random() * cities.length)]
      }
    }, 1000)
  } catch (error) {
    console.error('获取天气信息失败:', error)
  }
}

let timeInterval = null

onMounted(() => {
  // 检测移动设备
  checkMobileDevice();
  
  // 监听窗口大小变化
  window.addEventListener('resize', checkMobileDevice);
  
  // 立即更新一次时间和日期
  updateDateTime()
  
  // 设置定时器，每分钟更新一次时间
  timeInterval = setInterval(updateDateTime, 60000)
  
  // 获取天气信息
  fetchWeather()
})

onBeforeUnmount(() => {
  // 组件卸载时清除定时器
  if (timeInterval) {
    clearInterval(timeInterval)
  }
  
  // 移除窗口大小变化监听
  window.removeEventListener('resize', checkMobileDevice);
})
</script>

<style scoped>
.time-weather-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background-color: rgba(0, 0, 0, 0.4);
  padding: 8px 15px;
  border-radius: 20px;
  color: white;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(5px);
  z-index: 100;
  font-size: 0.9rem;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .time-weather-container {
    top: 10px; /* 置顶 */
    bottom: auto; /* 取消旧的底部定位 */
    padding: 6px 12px;
    font-size: 0.8rem;
    width: auto;
    max-width: 90%;
  }
  
  .weather-row {
    justify-content: center;
    flex-wrap: nowrap;
  }
}

.weather-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date {
  font-weight: 500;
}

.divider {
  opacity: 0.5;
}

.location {
  font-weight: 500;
}

.weather-icon {
  display: flex;
  align-items: center;
  color: white;
}

.condition {
  opacity: 0.9;
}

.temp {
  font-weight: 500;
}
</style> 