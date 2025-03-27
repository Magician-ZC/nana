import httpx
import asyncio
from typing import List, Optional
import time

class EmbeddingService:
    def __init__(self, api_key: str, api_url: str, model: str, dimension: int):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.dimension = dimension

    def get_embedding(
        self,
        text: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[List[float]]:
        # 如果输入为空，直接返回 None
        if not text or not text.strip():
            print("输入文本为空，无法获取向量表示")
            return None
            
        retry_count = 0
        
        # 清理输入文本
        clean_text = text.replace('\r\n', '\n').replace('\r', '\n')
        print(f"开始获取文本的向量表示，文本长度: {len(clean_text)}字符")
        
        while retry_count <= max_retries:
            try:
                print(f"使用模型 {self.model} 请求嵌入API...")
                with httpx.Client(verify=False, timeout=30.0) as client:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    
                    data = {
                        "model": self.model,
                        "input": clean_text
                    }
                    
                    print(f"发送请求到 {self.api_url}...")
                    response = client.post(
                        self.api_url,
                        json=data,
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Embedding API error: {response.status_code}, Response: {response.text}")
                    
                    print("收到API响应，开始解析...")
                    response_data = response.json()
                    if "data" not in response_data or not response_data["data"]:
                        raise Exception(f"Invalid API response format: {response_data}")
                        
                    embedding = response_data["data"][0]["embedding"]
                    print(f"向量表示获取成功，维度: {len(embedding)}, 预期维度: {self.dimension}")
                    return embedding
                    
            except Exception as e:
                if retry_count == max_retries:
                    print(f"Embedding API调用失败, 超过最大重试次数: {str(e)}")
                    return None
                    
                retry_count += 1
                print(f"Embedding API调用失败，{retry_delay}秒后进行第{retry_count}次重试..., 错误: {str(e)}")
                time.sleep(retry_delay) 