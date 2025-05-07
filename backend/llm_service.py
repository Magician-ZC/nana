from typing import AsyncGenerator, Optional, List, Dict, Any
from conversation import ConversationHistory
from config import Config

class LLMService:
    async def stream_chat(self, message: str, conversation_history: ConversationHistory, 
                      agent_type: str = "nanaA", is_category: bool = False, personality: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        流式生成聊天回复
        
        Args:
            message: 用户消息
            conversation_history: 对话历史
            agent_type: 智能体类型，默认为"nanaA"
            is_category: 是否是分类对话
            personality: 可选的个性描述

        Yields:
            str: 生成的回复片段
        """
        # 设置prompt和模型
        if is_category:
            print(f"使用引导模式prompt，不使用角色个性，agent_type={agent_type}")
            system_prompt = self._get_guidance_prompt(agent_type, message)
            # 引导模式下，不使用角色个性
            personality = None
        else:
            print(f"使用普通对话prompt，agent_type={agent_type}, 个性={personality}")
            system_prompt = self._get_prompt(agent_type, personality)
        
        # 打印实际使用的system prompt
        print(f"使用的system prompt: {system_prompt[:200]}...")
        
        # 对话历史记录
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加历史对话记录
        for turn in conversation_history.get_history():
            messages.append({"role": "user", "content": turn["message"]})
            messages.append({"role": "assistant", "content": turn["reply"]})
        
        # 添加当前消息
        messages.append({"role": "user", "content": message})
        
        # 检查并调整token长度
        messages = self._check_context_length(messages)
        
        # 流式生成回复
        try:
            # 调用LLM API流式生成回复
            model = Config.LLM_MODEL
            temperature = 0.7  # 设置生成的随机性
            
            # 如果是引导模式，使用更低的temperature以保持对话更加聚焦
            if is_category:
                temperature = 0.5
            
            # 使用OpenAI客户端流式生成
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
            )
            
            # 处理流式响应
            response_content = ""
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_content += content
                    yield content
                    
        except Exception as e:
            error_message = f"生成回复时出错: {e}"
            print(error_message)
            yield error_message 