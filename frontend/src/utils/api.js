/**
 * API服务配置
 */

// 检测当前环境、构建API基础URL
function detectApiBaseUrl() {
  // 获取当前hostname (支持自定义IP访问)
  const currentHost = window.location.hostname;
  
  // 如果是localhost或127.0.0.1，直接使用localhost
  const apiHost = ['localhost', '127.0.0.1'].includes(currentHost) 
    ? 'localhost' 
    : currentHost;
    
  // 使用检测到的host构建API URL
  return `https://${apiHost}:8666`;
}

// API基础URL - 使用动态检测
export const API_BASE_URL = 'https://192.168.3.51:8666';

// 输出当前使用的API基础地址，方便调试
console.log(`当前API基础地址: ${API_BASE_URL}`);

// 构建完整的API URL
export function getApiUrl(endpoint) {
  // 确保endpoint不以/开头
  if (endpoint.startsWith('/')) {
    endpoint = endpoint.substring(1);
  }
  
  // 确保endpoint以api/开头
  if (!endpoint.startsWith('api/')) {
    endpoint = `api/${endpoint}`;
  }
  
  return `${API_BASE_URL}/${endpoint}`;
}

// 获取外部API完整URL (保持HTTP访问外部系统)
export function getExternalApiUrl(baseUrl, endpoint) {
  // 确保endpoint不以/开头
  if (endpoint.startsWith('/')) {
    endpoint = endpoint.substring(1);
  }
  
  return `${baseUrl}/${endpoint}`;
}

// 导出默认配置
export default {
  API_BASE_URL,
  getApiUrl,
  getExternalApiUrl
}; 