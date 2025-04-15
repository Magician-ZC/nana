/**
 * API服务配置
 */

// 检测当前环境、构建API基础URL
function detectApiBaseUrl() {
  try {
    // 获取当前hostname和协议
    const currentHost = window.location.hostname;
    const currentProtocol = window.location.protocol;
    
    // 默认使用HTTPS协议
    const apiProtocol = 'https:';
    
    // 决定API主机地址
    let apiHost;
    
    // 如果是localhost或127.0.0.1，直接使用localhost
    if (['localhost', '127.0.0.1'].includes(currentHost)) {
      apiHost = 'localhost';
    } else {
      // 对于IP地址访问，使用当前访问的IP
      apiHost = currentHost;
    }
    
    // 显式指定IP地址 - 用于直接通过IP访问的情况
    if (currentHost === '192.168.3.51') {
      apiHost = '192.168.3.51';
    }
    
    // 构建API URL
    const apiUrl = `${apiProtocol}//${apiHost}:8666`;
    console.log(`[API] 当前环境: ${currentProtocol}//${currentHost} -> API基础地址: ${apiUrl}`);
    
    return apiUrl;
  } catch (error) {
    console.error('检测API基础URL失败:', error);
    // 如果出错，返回默认值
    return 'https://localhost:8666';
  }
}

// API基础URL - 使用动态检测
export const API_BASE_URL = detectApiBaseUrl();

// 输出当前使用的API基础地址，方便调试
console.log(`[API] 使用API基础地址: ${API_BASE_URL}`);

// 构建完整的API URL
export function getApiUrl(endpoint) {
  try {
    // 确保endpoint不以/开头
    if (endpoint.startsWith('/')) {
      endpoint = endpoint.substring(1);
    }
    
    // 确保endpoint以api/开头
    if (!endpoint.startsWith('api/')) {
      endpoint = `api/${endpoint}`;
    }
    
    const fullUrl = `${API_BASE_URL}/${endpoint}`;
    return fullUrl;
  } catch (error) {
    console.error(`[API] 构建API URL失败(${endpoint}):`, error);
    return `${API_BASE_URL}/api/${endpoint}`;
  }
}

// 获取外部API完整URL (保持HTTP访问外部系统)
export function getExternalApiUrl(baseUrl, endpoint) {
  try {
    // 确保endpoint不以/开头
    if (endpoint.startsWith('/')) {
      endpoint = endpoint.substring(1);
    }
    
    return `${baseUrl}/${endpoint}`;
  } catch (error) {
    console.error(`[API] 构建外部API URL失败(${endpoint}):`, error);
    return `${baseUrl}/${endpoint}`;
  }
}

// 导出默认配置
export default {
  API_BASE_URL,
  getApiUrl,
  getExternalApiUrl
}; 