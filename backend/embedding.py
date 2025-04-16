import httpx
import asyncio
from typing import List, Optional
import time
import threading
from queue import Queue
import concurrent.futures

class EmbeddingService:
    def __init__(self, api_key: str, api_url: str, model: str, dimension: int):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.dimension = dimension
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        self.embedding_queue = Queue()
        self.embedding_cache = {}  # 简单的内存缓存
        
        # 启动后台工作线程
        self._start_background_worker()

    def _start_background_worker(self):
        """启动后台工作线程处理embedding请求"""
        threading.Thread(target=self._process_embedding_queue, daemon=True).start()
        print("Embedding后台处理线程已启动")
    
    def _process_embedding_queue(self):
        """后台线程函数，持续处理队列中的embedding请求"""
        while True:
            try:
                # 从队列获取任务: (text, callback)
                if self.embedding_queue.empty():
                    time.sleep(0.1)  # 轻微休眠以避免空转
                    continue
                    
                text, callback = self.embedding_queue.get()
                
                # 检查缓存
                if text in self.embedding_cache:
                    print(f"从缓存获取embedding: {text[:20]}...")
                    if callback:
                        callback(self.embedding_cache[text])
                    continue
                
                # 处理任务
                embedding = self._fetch_embedding(text)
                
                # 缓存结果
                if embedding:
                    self.embedding_cache[text] = embedding
                
                # 如果有回调函数，则调用它
                if callback:
                    callback(embedding)
                    
            except Exception as e:
                print(f"Embedding后台处理线程出错: {e}")
                # 继续处理下一个任务，不中断线程
                continue
    
    def get_embedding(
        self,
        text: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[List[float]]:
        """同步获取embedding，但内部实现为非阻塞，立即返回默认值"""
        # 如果输入为空，直接返回None
        if not text or not text.strip():
            return None
        
        # 检查缓存
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        
        # 创建默认embedding (全为0的向量)
        default_embedding = [0.0] * self.dimension
        
        # 提交到后台队列，但不等待结果
        self.submit_embedding_task(text)
        
        # 立即返回默认embedding
        return default_embedding
    
    def submit_embedding_task(self, text, callback=None):
        """提交embedding任务到后台队列"""
        # 如果输入为空，不处理
        if not text or not text.strip():
            return
            
        # 清理输入文本
        clean_text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 放入队列
        self.embedding_queue.put((clean_text, callback))
    
    def _fetch_embedding(
        self,
        text: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[List[float]]:
        """实际获取embedding的方法，会在后台线程中调用"""
        # 如果输入为空，直接返回None
        if not text or not text.strip():
            return None
            
        retry_count = 0
        
        # 清理输入文本
        clean_text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        while retry_count <= max_retries:
            try:
                with httpx.Client(verify=False, timeout=30.0) as client:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    
                    data = {
                        "model": self.model,
                        "input": clean_text
                    }
                    
                    response = client.post(
                        self.api_url,
                        json=data,
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Embedding API error: {response.status_code}")
                    
                    response_data = response.json()
                    if "data" not in response_data or not response_data["data"]:
                        raise Exception("Invalid API response format")
                        
                    embedding = response_data["data"][0]["embedding"]
                    print("embedding size:", len(embedding), "embedding:", embedding[0:10])
                    return embedding
                    
            except Exception as e:
                if retry_count == max_retries:
                    print(f"Embedding API调用失败, 超过最大重试次数: {str(e)}")
                    return None
                    
                retry_count += 1
                print(f"Embedding API调用失败，{retry_delay}秒后进行第{retry_count}次重试...")
                time.sleep(retry_delay)
    
    async def get_embedding_async(
        self,
        text: str,
        max_retries: int = 3, 
        retry_delay: float = 1.0
    ) -> Optional[List[float]]:
        """异步获取embedding（通过执行器在线程池中执行）"""
        # 如果输入为空，直接返回None
        if not text or not text.strip():
            return None
            
        # 检查缓存
        if text in self.embedding_cache:
            return self.embedding_cache[text]
            
        loop = asyncio.get_running_loop()
        
        try:
            # 使用线程池执行器在后台运行同步操作
            embedding = await loop.run_in_executor(
                self.executor, 
                lambda: self._fetch_embedding(text, max_retries, retry_delay)
            )
            
            # 缓存结果
            if embedding:
                self.embedding_cache[text] = embedding
                
            return embedding
        except Exception as e:
            print(f"异步获取embedding失败: {e}")
            return [0.0] * self.dimension 