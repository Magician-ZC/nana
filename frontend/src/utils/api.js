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
      apiHost = '192.168.3.51';
    } else {
      // 对于IP地址访问，使用当前访问的IP
      apiHost = 'woaiwo.oamicnet.com';
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

/**
 * 创建带有认证信息的请求选项
 * @param {Object} options - 基础请求选项
 * @returns {Object} - 带有认证信息的请求选项
 */
export function createAuthenticatedRequest(options = {}) {
  // 获取会话ID
  const sessionId = localStorage.getItem('session_id');
  
  // 默认请求选项
  const defaultOptions = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include', // 确保跨域请求时携带Cookie
  };
  
  // 合并默认选项和传入的选项
  const mergedOptions = { ...defaultOptions, ...options };
  
  // 如果存在合并后的headers，则使用它，否则使用空对象
  mergedOptions.headers = { ...defaultOptions.headers, ...(options.headers || {}) };
  
  // 添加Authorization头
  if (sessionId) {
    mergedOptions.headers['Authorization'] = `Bearer ${sessionId}`;
    
    // 额外设置Cookie (以增加兼容性)
    document.cookie = `session_id=${sessionId}; path=/; SameSite=Lax`;
  }
  
  return mergedOptions;
}

/**
 * 获取API响应，自动处理认证
 * @param {string} endpoint - API端点
 * @param {Object} options - 请求选项
 * @returns {Promise<Response>} - 响应对象
 */
export async function fetchApi(endpoint, options = {}) {
  const url = getApiUrl(endpoint);
  const requestOptions = createAuthenticatedRequest(options);
  
  try {
    return await fetch(url, requestOptions);
  } catch (error) {
    console.error(`[API] 请求API失败(${endpoint}):`, error);
    throw error;
  }
}

/**
 * 显示通知消息
 * @param {string} message - 通知消息内容
 * @param {string} type - 通知类型 ('success' 或 'error')
 */
export function showNotification(message, type = 'success') {
  const notificationEl = document.createElement('div');
  
  if (type === 'success') {
    // 成功通知 - 绿色、居中、3秒后自动消失
    notificationEl.className = 'fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-green-500 text-white px-6 py-4 rounded-lg shadow-xl z-50 flex items-center transition-all';
    notificationEl.innerHTML = `<i class="fa-solid fa-check-circle mr-2 text-xl"></i>${message}`;
    
    // 添加渐入动画
    notificationEl.style.opacity = '0';
    notificationEl.style.transform = 'translate(-50%, calc(-50% + 20px))';
    
    document.body.appendChild(notificationEl);
    
    // 触发渐入动画
    setTimeout(() => {
      notificationEl.style.opacity = '1';
      notificationEl.style.transform = 'translate(-50%, -50%)';
      notificationEl.style.transition = 'opacity 0.3s, transform 0.3s';
    }, 10);
    
    // 3秒后自动消失
    setTimeout(() => {
      notificationEl.style.opacity = '0';
      notificationEl.style.transform = 'translate(-50%, calc(-50% - 20px))';
      
      // 等待动画完成后移除元素
      setTimeout(() => {
        notificationEl.remove();
      }, 300);
    }, 3000);
  } else {
    // 错误通知 - 红色、底部、需要手动关闭
    notificationEl.className = 'fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center transition-all';
    notificationEl.innerHTML = `
      <i class="fa-solid fa-exclamation-circle mr-2 text-xl"></i>
      ${message}
      <button class="ml-3 bg-red-400 hover:bg-red-300 rounded-full w-6 h-6 flex items-center justify-center" onclick="this.parentNode.remove()">
        <i class="fa-solid fa-times text-sm"></i>
      </button>
    `;
    
    // 添加渐入动画
    notificationEl.style.opacity = '0';
    notificationEl.style.transform = 'translate(-50%, 20px)';
    
    document.body.appendChild(notificationEl);
    
    // 触发渐入动画
    setTimeout(() => {
      notificationEl.style.opacity = '1';
      notificationEl.style.transform = 'translate(-50%, 0)';
      notificationEl.style.transition = 'opacity 0.3s, transform 0.3s';
    }, 10);
  }
}

// 导出默认配置
export default {
  API_BASE_URL,
  getApiUrl,
  getExternalApiUrl,
  createAuthenticatedRequest,
  fetchApi,
  showNotification
}; 