# Nana前端

这是Nana项目的前端部分，基于Vue.js和Vite构建。

## 环境要求
- Node.js 16+
- npm 8+

## 安装依赖
```bash
npm install
```

## 开发模式运行
```bash
npm run dev
```

## HTTPS访问配置
本项目已配置支持HTTPS访问，以便支持摄像头和麦克风权限请求。

### 自动配置
1. 后端会自动生成SSL证书（确保先运行后端）
2. 前端会自动使用后端生成的证书运行HTTPS服务

### 手动配置证书
如需手动创建证书：
```bash
cd ../backend
python generate_cert.py
```

### 摄像头和麦克风权限测试
1. 启动后端服务：`python main.py` (将自动生成SSL证书)
2. 启动前端服务：`npm run dev`
3. 访问URL: `https://192.168.3.51:5173/?test-permissions`
4. 接受安全警告（自签名证书）
5. 点击测试按钮验证摄像头和麦克风权限

## 注意事项
- 初次访问HTTPS站点时，浏览器会显示安全警告，需要手动确认接受
- 自签名证书仅用于开发环境，生产环境请使用受信任的SSL证书
- 摄像头和麦克风权限只能在HTTPS或localhost环境下请求

## 技术栈

- Vue 3 组合式API
- Pinia 状态管理
- Vite 构建工具
- Live2D 模型展示

## 功能特性

- 多种Live2D角色形象
- 实时语音交互
- 聊天历史记录
- 角色动态表情反馈
