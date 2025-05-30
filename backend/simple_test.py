import requests
import json
import sys

def test_ollama_connection(url="http://192.168.3.95:11434", model="qwen2.5", prompt="你好"):
    """测试Ollama连接的简单函数
    
    Args:
        url: Ollama服务URL，无需/api后缀
        model: 模型名称，可能需要不带版本号
        prompt: 测试提示词
    """
    print(f"\n===== 测试Ollama连接 =====")
    print(f"URL: {url}")
    print(f"模型: {model}")
    
    # 1. 首先测试服务是否可用
    try:
        models_response = requests.get(f"{url}/api/tags", timeout=5)
        if models_response.status_code == 200:
            print("Ollama服务可用! 现有模型:")
            models = models_response.json().get('models', [])
            for m in models:
                print(f" - {m.get('name')}: {m.get('size')}")
        else:
            print(f"无法连接到Ollama: 状态码 {models_response.status_code}")
            print(f"错误信息: {models_response.text}")
    except Exception as e:
        print(f"无法连接到Ollama: {e}")
        print("请确认:")
        print("1. Ollama服务是否正在运行")
        print("2. URL是否正确")
        print("3. 网络连接是否正常")
        return
    
    # 2. 尝试使用模型
    print("\n===== 测试模型 =====")
    api_endpoints = ["api/generate", "api/chat"]
    model_names = [model, model.split(":")[0], f"{model}:latest"]
    
    # 尝试所有组合
    success = False
    for endpoint in api_endpoints:
        if success:
            break
        for model_name in model_names:
            print(f"\n尝试 {endpoint} 和模型 {model_name}...")
            try:
                # 构建请求
                request_data = {
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                }
                
                # 发送请求
                response = requests.post(
                    f"{url}/{endpoint}", 
                    json=request_data,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )
                
                # 处理响应
                if response.status_code == 200:
                    result = response.json()
                    print(f"成功! 响应: {result}")
                    print(f"✅ 成功的配置: URL={url}, endpoint={endpoint}, model={model_name}")
                    success = True
                    
                    # 建议配置
                    print("\n===== 建议配置 =====")
                    print(f"在config.py中使用:")
                    print(f'LLM_API_URL = "{url}"')
                    print(f'LLM_MODEL = "{model_name}"')
                    print("\n在llm.py的_ollama_generate方法中使用:")
                    print(f'f"{{self.api_url}}/{endpoint}"')
                    
                    break
                    
                else:
                    print(f"失败: 状态码 {response.status_code}")
                    print(f"错误信息: {response.text}")
                
            except Exception as e:
                print(f"请求失败: {e}")
    
    if not success:
        print("\n❌ 所有组合均失败。请检查:")
        print("1. 模型是否已加载 (使用 `ollama pull qwen` 加载模型)")
        print("2. Ollama服务是否正常运行")
        print("3. 网络是否能正常连接")

if __name__ == "__main__":
    # 从命令行参数获取URL和模型
    url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.3.95:11434"
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5"
    prompt = sys.argv[3] if len(sys.argv) > 3 else "简短回复: 你好"
    
    test_ollama_connection(url, model, prompt) 