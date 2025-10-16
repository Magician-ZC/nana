import asyncio
from typing import List, Dict, Optional, Any, Tuple
import json
import re
import base64
from openai import OpenAI, AsyncOpenAI
import aiohttp
import os
import httpx
from datetime import datetime
from config import Config

class LLMService:
    def __init__(self, api_key: str = "", api_url: str = "", model: str = None):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model if model else Config.LLM_MODEL
        self.chat_service = None  # 添加对ChatService的引用
        
        # 创建日志目录
        self.log_dir = 'save/llm_log'
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 构造OpenAI客户端，处理空API密钥的情况
        client_kwargs = {
            "base_url": api_url
        }
        
        # 仅当API密钥不为空时添加到客户端参数中
        if api_key:
            client_kwargs["api_key"] = api_key
        else:
            # 对于Ollama等不需要API密钥的服务，添加无意义但有效的API密钥
            client_kwargs["api_key"] = "sk_no_key_required"
        
        self.client = OpenAI(**client_kwargs)
        
        # 检查API是否支持视觉功能
        try:
            self.vision_model_available = "GPT" in api_url or "gpt" in api_url
            print(f"视觉模型状态: {'可用' if self.vision_model_available else '不可用'}")
        except:
            self.vision_model_available = False
            print("视觉模型不可用")
        
    def set_chat_service(self, chat_service):
        """设置ChatService引用"""
        self.chat_service = chat_service
    
    async def async_chat(self, message: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """简单的异步聊天方法，直接返回文本回复
        
        Args:
            message: 用户消息
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: 模型回复的文本
        """
        # 检测URL是否是Ollama服务（没有/v1路径）
        if "ollama" in self.api_url.lower() or "11434" in self.api_url:
            return await self._ollama_generate(message, temperature, max_tokens)
        else:
            # 使用OpenAI兼容接口
            return await self.generate_response(
                message=message,
                temperature=temperature,
                max_tokens=max_tokens,
                is_json=False
            )

    async def _ollama_generate(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """使用Ollama原生API接口生成回复
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: 生成的回复
        """
        try:
            # 创建异步HTTP客户端
            timeout = httpx.Timeout(90.0, connect=30.0)  # 增加超时时间到90秒
            async with httpx.AsyncClient(timeout=timeout) as client:
                # 构建请求数据 - 使用Ollama原生API格式
                request_data = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                # 直接使用固定的api/generate端点
                url = f"{self.api_url}/api/generate"
                print(f"发送请求到: {url}")
                
                response = await client.post(
                    url,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                # 检查响应状态
                if response.status_code != 200:
                    raise Exception(f"Ollama API错误: 状态码 {response.status_code}, 响应: {response.text}")
                
                # 解析响应
                response_data = response.json()
                if "response" in response_data:
                    return response_data["response"].strip()
                else:
                    raise Exception(f"Ollama响应格式异常: {response_data}")
                    
        except Exception as e:
            print(f"Ollama调用出错: {str(e)}")
            raise
    
    async def analyze_image(self, img_base64: str, prompt: str = None) -> str:
        """分析图片内容并返回描述文本
        
        Args:
            img_base64: Base64编码的图片数据
            prompt: 可选的提示词，指导模型关注图片的特定方面
            
        Returns:
            str: 图片内容的描述文本
        """
        # 如果没有提供具体指令，使用默认提示词
        if not prompt:
            prompt = """请分析这张图片，识别图片中的所有文本、表格和图表数据。
如果包含情绪评估相关的数据，请特别关注"攻击性"、"自信"、"能量"、"压力"、"抑郁"等指标及其数值。
请以结构化格式返回所有识别到的数据。"""
        
        # 检查是否支持视觉功能
        if not self.vision_model_available:
            print("视觉模型不可用，跳过图像分析")
            return ""
        
        try:
            # 构建消息，包含文本和图像内容
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}",
                                "detail": "high"  # 请求高详细度，以便读取文本和表格
                            }
                        }
                    ]
                }
            ]
            
            # 调用视觉模型API
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4-vision-preview",  # 使用支持视觉的模型
                messages=messages,
                temperature=0.2,  # 低温度，更精确的回答
                max_tokens=2000,
                stream=False
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"图像分析出错: {str(e)}")
            return f"无法分析图像: {str(e)}"
        
    async def generate_response(
        self, 
        message: str,
        temperature: float = 0.7,
        max_retries: int = 3,
        is_json: bool = False,
        max_tokens: int = 1024
    ) -> str:
        # 检测URL是否是Ollama服务
        if "ollama" in self.api_url.lower() or "11434" in self.api_url:
            # 使用Ollama原生API
            response = await self._ollama_generate(message, temperature, max_tokens)
            if is_json:
                return self._parse_json_response(response)
            else:
                return response
        
        # 使用OpenAI兼容的API
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 构建消息列表，只包含用户消息
                messages = [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
                
                # 使用真正的异步API调用，而不是asyncio.to_thread
                # 创建异步HTTP客户端，添加超时设置
                timeout = httpx.Timeout(30.0, connect=10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    # 构建请求数据
                    request_data = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                    
                    # 构建请求头，仅在API密钥不为空时添加Authorization头
                    headers = {
                        "Content-Type": "application/json"
                    }
                    if self.api_key:
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    # 发送请求到API
                    response = await client.post(
                        f"{self.api_url}/chat/completions",
                        json=request_data,
                        headers=headers
                    )
                    
                    # 检查响应状态
                    if response.status_code != 200:
                        raise Exception(f"API错误: 状态码 {response.status_code}, 响应: {response.text}")
                    
                    # 解析响应
                    response_data = response.json()
                    raw_response = response_data["choices"][0]["message"]["content"].strip()
                    print("raw_response:", raw_response)
                    
                    # 根据请求选择返回格式
                    if is_json:
                        return self._parse_json_response(raw_response)
                    else:
                        return raw_response
                        
            except Exception as e:
                retry_count += 1
                print(f"LLM Error (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    # 增加指数退避重试延迟
                    await asyncio.sleep(2 ** retry_count)
                else:
                    raise
                
    @staticmethod
    def _parse_json_response(raw_response: str) -> Dict:
        # 尝试直接解析
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # 使用正则表达式匹配 ```json 或 ``` 包裹的内容
            try:
                # 清理输入，删除可能影响解析的换行符和多余空格
                cleaned_text = raw_response.strip()
                
                # 先尝试匹配 ```json 格式
                pattern = r'```(?:json\n|\n)?([^`]*?)```'
                matches = re.search(pattern, cleaned_text, re.DOTALL)
                
                if matches:
                    json_str = matches.group(1).strip()
                    return json.loads(json_str)
                
                # 如果上面的尝试失败，查找任何有效的JSON对象
                # 这个更宽松的正则表达式查找由 { 开始和 } 结束的内容
                pattern = r'({[\s\S]*?})'
                matches = re.findall(pattern, cleaned_text)
                
                for potential_json in matches:
                    try:
                        # 清理，删除非标准JSON格式中的注释和多余字符
                        cleaned_json = re.sub(r'//.*?[\n\r]|/\*.*?\*/', '', potential_json, flags=re.DOTALL)
                        # 尝试查找并修复常见的不规范格式
                        cleaned_json = re.sub(r'(?<!")(\w+)(?=":)', r'"\1"', cleaned_json)  # 修复没有引号的键
                        cleaned_json = re.sub(r',(\s*})', r'\1', cleaned_json)  # 修复JSON对象末尾多余的逗号
                        # 验证大括号是否匹配
                        if cleaned_json.count('{') == cleaned_json.count('}'):
                            parsed = json.loads(cleaned_json)
                            # 确保解析出的结果至少包含reply字段
                            if isinstance(parsed, dict) and 'reply' in parsed:
                                return parsed
                    except:
                        continue
                
                # 检查是否是纯文本回复，尝试手动构造JSON
                if not any(char in cleaned_text for char in ['{', '}', '[', ']']):
                    print(f"收到纯文本回复，尝试构造JSON: {cleaned_text[:100]}...")
                    return {
                        "reply": cleaned_text,
                        "expression": "咪咪眼",
                        "is_question": "?" in cleaned_text,
                        "is_summary": False,
                        "question_type": "follow_up"
                    }
                
                # 尝试查找最后一种情况：JSON可能没有被完全包裹
                pattern = r'({[^{}]*"reply":[^{}]*"[^"]*"[^{}]*})'
                matches = re.search(pattern, cleaned_text, re.DOTALL)
                if matches:
                    try:
                        return json.loads(matches.group(1).strip())
                    except:
                        pass
                
                # 如果所有尝试都失败，返回一个基本的JSON对象
                return {
                    "reply": "抱歉，我无法理解您的问题。",
                    "expression": "疑惑",
                    "is_question": False,
                    "is_summary": False,
                    "question_type": "confusion"
                }
            except Exception as e:
                print(f"解析JSON时出错: {e}")
                return {
                    "reply": "抱歉，处理您的请求时出现了错误。",
                    "expression": "疑惑",
                    "is_question": False,
                    "is_summary": False,
                    "question_type": "error"
                }
                
    async def generate_streaming(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048):
        """生成流式响应
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            str: 文本块
        """
        # 检测URL是否是Ollama服务（没有/v1路径）
        if "ollama" in self.api_url.lower() or "11434" in self.api_url:
            async for text_chunk in self._ollama_generate_streaming(prompt, temperature, max_tokens):
                yield text_chunk
        else:
            # 使用OpenAI兼容接口
            try:
                # 构建消息列表
                messages = [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
                
                # 使用流式API
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                )
                
                # 流式输出文本块
                for chunk in response:
                    if chunk.choices and len(chunk.choices) > 0:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            # 尝试检查是否是JSON格式的数据，如果是，尝试解析JSON并只返回reply字段
                            try:
                                # 只对疑似JSON字符串进行检查（以{开头的内容）
                                if '{' in content and ('"reply"' in content or '"is_question"' in content):
                                    parsed_json = json.loads(content)
                                    if isinstance(parsed_json, dict) and 'reply' in parsed_json:
                                        yield parsed_json['reply']
                                        continue
                            except json.JSONDecodeError:
                                # 如果解析失败，继续将原始内容传递
                                pass
                            
                            yield content
            except Exception as e:
                print(f"流式生成回复时出错: {e}")
                yield f"生成回复出错: {str(e)}"

    async def _ollama_generate_streaming(self, prompt: str, temperature: float = 0.7, max_tokens: int = 2048):
        """使用Ollama原生API接口进行流式生成
        
        Args:
            prompt: 提示词
            temperature: 温度参数
            max_tokens: 最大token数
            
        Yields:
            str: 文本块
        """
        try:
            # 创建异步HTTP客户端
            timeout = httpx.Timeout(90.0, connect=30.0)  # 增加超时时间到90秒
            async with httpx.AsyncClient(timeout=timeout) as client:
                # 构建请求数据 - 使用Ollama原生API格式
                request_data = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,  # 开启流式响应
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
                
                # 直接使用固定的api/generate端点
                url = f"{self.api_url}/api/generate"
                print(f"发送流式请求到: {url}")
                
                # 发送请求到Ollama API
                async with client.stream("POST", 
                                        url, 
                                        json=request_data,
                                        headers={"Content-Type": "application/json"}) as response:
                    if response.status_code != 200:
                        raise Exception(f"Ollama API错误: 状态码 {response.status_code}")
                    
                    # 处理流式响应
                    async for chunk in response.aiter_text():
                        if not chunk or chunk.isspace():
                            continue
                        
                        try:
                            # Ollama流式响应格式是一系列JSON对象
                            data = json.loads(chunk)
                            if "response" in data:
                                yield data["response"]
                        except json.JSONDecodeError:
                            # 如果不是有效的JSON，直接返回内容
                            yield chunk
                
        except Exception as e:
            print(f"Ollama流式生成出错: {str(e)}")
            yield f"生成回复出错: {str(e)}"