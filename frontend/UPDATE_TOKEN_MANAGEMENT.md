# Token管理系统更新说明

## 更新概述

我们对认证token的管理进行了重构，实现了全局统一的token管理方案。主要目的是确保所有需要使用auth_token的地方都从同一个来源获取，避免不一致问题。

## 主要变更

1. **增强了userStore**
   - 添加了`initializeToken`方法用于应用启动时初始化token
   - 改进了`getAuthToken`方法，确保返回最新的token
   - 统一了开发测试token的管理

2. **修改了应用初始化流程**
   - 在`main.js`中添加了token初始化逻辑
   - 在`App.vue`组件挂载时添加了token检查逻辑

3. **统一了token的使用方式**
   - 所有组件和store中都使用`userStore.getAuthToken()`获取token
   - 所有token的设置都通过`userStore.setAuthToken()`完成

4. **添加了文档**
   - 创建了`README_TOKEN.md`文档，详细介绍了token的使用方法和注意事项

## 如何使用

请参考`README_TOKEN.md`文件了解详细的token使用方法。

基本上，您只需要知道：

```js
// 获取userStore实例
const userStore = useUserStore()

// 获取token
const authToken = userStore.getAuthToken()

// 设置token
userStore.setAuthToken(newToken)

// 清除token
userStore.clearAuthToken()

// 在开发环境中设置测试token
userStore.setDevelopmentToken()
```

## 迁移指南

1. 搜索代码中所有直接使用`localStorage.getItem('auth_token')`或`localStorage.setItem('auth_token', ...)`的地方
2. 替换为对应的userStore方法
3. 确保所有API请求都使用userStore获取的token

## 注意事项

- token会在应用启动时自动初始化，不需要手动初始化
- 在开发环境中，如果没有token，会自动设置一个开发测试token
- 所有的后端API调用都应该使用从userStore获取的token 