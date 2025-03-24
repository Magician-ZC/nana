import asyncio
from typing import List, Dict
import json
import re
from openai import OpenAI, AsyncOpenAI

class LLMService:
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.client = OpenAI(
            base_url=api_url,
            api_key=api_key
        )
        
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
                raise ValueError("No valid JSON block found")
            except Exception as e:
                raise ValueError(f"Failed to parse JSON response: {str(e)}")