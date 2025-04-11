# Token管理指南

## 概述

本项目使用了全局统一的token管理方案，所有需要授权token的地方应该从userStore获取，而不是直接访问localStorage。

## 使用方法

### 1. 引入userStore

在需要使用token的组件或store中，首先引入userStore：

```js
import { useUserStore } from '../stores/user'

// 在setup函数或组件中获取userStore实例
const userStore = useUserStore()
```

### 2. 获取token

通过userStore的getAuthToken方法获取token：

```js
// 获取授权令牌
const authToken = userStore.getAuthToken()

// 在API请求中使用
fetch('http://example.com/api/endpoint', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(data)
})
```

### 3. 设置token

如果需要设置或更新token，使用setAuthToken方法：

```js
// 登录成功后设置token
userStore.setAuthToken(response.token)
```

### 4. 清除token

退出登录时，使用clearAuthToken方法：

```js
// 退出登录
userStore.clearAuthToken()
```

### 5. 开发环境测试token

在开发环境中，如果没有有效token，可以使用setDevelopmentToken方法设置一个测试token：

```js
// 设置测试token
userStore.setDevelopmentToken()
```

## 注意事项

1. **禁止直接操作localStorage**：不要直接使用`localStorage.getItem('auth_token')`或`localStorage.setItem('auth_token', token)`，统一通过userStore管理
   
2. **token初始化**：应用程序在main.js中已经初始化了userStore和token，通常不需要手动初始化

3. **token格式**：在API请求头中使用token时，格式应为`Bearer {token}`

4. **token刷新**：如果实现了token刷新逻辑，应当只更新userStore中的token

## 实现详情

userStore中token的实现采用了以下策略：

1. 在内存中通过Pinia store维护token状态
2. 在localStorage中持久化存储token
3. 获取token时优先使用内存中的值，如果不存在则从localStorage获取
4. 设置token时同时更新内存和localStorage

这种方案确保了token的统一管理，避免了多处直接访问localStorage可能导致的不一致问题。 