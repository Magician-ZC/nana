import asyncio
import httpx
import json
from config import Config

async def check_ollama_health(base_url):
    """检查Ollama服务是否可访问"""
    print(f"\n===== 检查Ollama服务健康状态 =====")
    print(f"尝试连接: {base_url}")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 首先检查模型列表API
            models_url = f"{base_url}/api/tags"
            print(f"检查模型列表 URL: {models_url}")
            
            response = await client.get(models_url)
            if response.status_code == 200:
                models = response.json()
                print(f"服务可访问! 发现以下模型:")
                for model in models.get('models', []):
                    print(f" - {model.get('name')}: {model.get('size')}")
                return True
            else:
                print(f"错误: 状态码 {response.status_code}, 响应: {response.text}")
                return False
    
    except Exception as e:
        print(f"连接失败: {str(e)}")
        return False

async def test_different_endpoints(base_url, model_name):
    """测试不同的API端点和模型名称"""
    print(f"\n===== 测试不同API端点 =====")
    
    # 测试几个模型变体
    test_models = [
        model_name,
        model_name.replace(":", "-"),
        model_name.split(":")[0]
    ]
    
    # 测试不同的API端点
    api_endpoints = [
        "api/generate",
        "api/chat",  # 某些Ollama版本可能支持chat API
    ]
    
    for endpoint in api_endpoints:
        for test_model in test_models:
            print(f"\n尝试 endpoint: {endpoint}, 模型: {test_model}")
            
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    request_data = {
                        "model": test_model,
                        "prompt": "简短回复: 你好",
                        "stream": False
                    }
                    
                    url = f"{base_url}/{endpoint}"
                    print(f"请求URL: {url}")
                    print(f"请求数据: {json.dumps(request_data, ensure_ascii=False)}")
                    
                    response = await client.post(
                        url,
                        json=request_data,
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"成功! 响应: {result}")
                        print(f"=> 有效的组合: endpoint={endpoint}, 模型={test_model}")
                        return (endpoint, test_model)
                    else:
                        print(f"失败: 状态码 {response.status_code}, 响应: {response.text}")
            
            except Exception as e:
                print(f"请求出错: {str(e)}")
    
    print("所有组合都失败了")
    return None

async def main():
    # 获取配置
    ollama_url = Config.LLM_API_URL
    model_name = Config.LLM_MODEL
    
    print(f"Ollama URL: {ollama_url}")
    print(f"模型名称: {model_name}")
    
    # 检查Ollama服务健康状态
    if await check_ollama_health(ollama_url):
        print("Ollama服务正常运行!")
    else:
        print("警告: Ollama服务可能不可用")
    
    # 测试不同的API端点
    result = await test_different_endpoints(ollama_url, model_name)
    
    if result:
        endpoint, model = result
        print(f"\n===== 诊断结果 =====")
        print(f"发现有效配置:")
        print(f"URL: {ollama_url}")
        print(f"API端点: {endpoint}")
        print(f"模型名称: {model}")
        
        # 更新建议
        print(f"\n建议更新config.py中的配置:")
        print(f"LLM_API_URL = \"{ollama_url}\"")
        print(f"LLM_MODEL = \"{model}\"")
        
        # 更新llm.py中的API路径
        print(f"\n在llm.py中，请确保_ollama_generate方法中的API路径为:")
        print(f"f\"{{self.api_url}}/{endpoint}\"")
    else:
        print("\n===== 诊断结果 =====")
        print("无法找到有效的配置组合。请检查:")
        print("1. Ollama服务是否正在运行")
        print("2. IP地址和端口是否正确")
        print("3. 请求的模型是否已加载到Ollama中")
        print("4. 网络连接是否正常")
        
        print("\n可以尝试手动加载模型:")
        print(f"ollama pull {model_name}")

if __name__ == "__main__":
    asyncio.run(main()) 