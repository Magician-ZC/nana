import asyncio
from typing import List, Dict
import json
import re
import base64
from openai import OpenAI, AsyncOpenAI

class LLMService:
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.client = OpenAI(
            base_url=api_url,
            api_key=api_key
        )
        # 检查API是否支持视觉功能
        try:
            self.vision_model_available = "GPT" in api_url or "gpt" in api_url
            print(f"视觉模型状态: {'可用' if self.vision_model_available else '不可用'}")
        except:
            self.vision_model_available = False
            print("视觉模型不可用")
        
    async def async_chat(self, message: str, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """简单的异步聊天方法，直接返回文本回复
        
        Args:
            message: 用户消息
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            str: 模型回复的文本
        """
        return await self.generate_response(
            message=message,
            temperature=temperature,
            max_tokens=max_tokens,
            is_json=False
        )
    
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
                
                # 使用异步客户端
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model="deepseek/deepseek-v3/community",  # 使用正确的模型
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                )
                
                raw_response = response.choices[0].message.content.strip()
                print("raw_response:", raw_response)
                
                if is_json:
                    return self._parse_json_response(raw_response)
                else:
                    return raw_response
                        
            except Exception as e:
                retry_count += 1
                print(f"LLM Error (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    await asyncio.sleep(1)
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
                # 先尝试匹配 ```json 格式
                pattern = r'```(?:json\n|\n)?([^`]*?)```'
                matches = re.search(pattern, raw_response, re.DOTALL)
                
                if matches:
                    json_str = matches.group(1).strip()
                    return json.loads(json_str)
                    
                # 如果上面的尝试失败，查找任何有效的JSON对象
                pattern = r'({[\s\S]*?})'
                matches = re.findall(pattern, raw_response)
                
                for potential_json in matches:
                    try:
                        # 清理，删除非标准JSON格式中的注释和多余字符
                        cleaned_json = re.sub(r'//.*?[\n\r]|/\*.*?\*/', '', potential_json, flags=re.DOTALL)
                        # 验证大括号是否匹配
                        if cleaned_json.count('{') == cleaned_json.count('}'):
                            parsed = json.loads(cleaned_json)
                            # 确保解析出的结果至少包含reply字段
                            if isinstance(parsed, dict) and 'reply' in parsed:
                                return parsed
                    except:
                        continue
                
                # 尝试查找最后一种情况：JSON可能没有被完全包裹
                pattern = r'({[^{}]*"reply":[^{}]*"[^"]*"[^{}]*})'
                matches = re.search(pattern, raw_response, re.DOTALL)
                if matches:
                    try:
                        return json.loads(matches.group(1).strip())
                    except:
                        pass
                    
                raise ValueError("No valid JSON block found")
            except Exception as e:
                print(f"JSON解析错误，原始响应: {raw_response}")
                # 如果所有尝试都失败，构造一个基本的回复
                return {
                    "reply": "对不起，我遇到了一些技术问题，无法正确回应。能请你重新表述一下吗？",
                    "expression": "生气"
                }