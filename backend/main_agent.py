from llm import LLMService
from typing import List, Dict, Tuple
import os
from datetime import datetime
from conversation import ConversationHistory

class MainAgent:
    def __init__(self, llm_service: LLMService, conversation_history: ConversationHistory):
        self.conversation_history = conversation_history
        self.llm_service = llm_service
        self.current_agent = "nanaA"  # 默认使用娜娜A
        self._load_prompt_template()
            
        # 确保日志和个人信息目录存在
        self.log_dir = 'save/log'
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 读取个人信息文件
        self.user_info_file = 'save/me.txt'
        self.user_info = self._load_user_info()
    
    def _load_prompt_template(self):
        """根据当前选择的智能体加载对应的提示词模板"""
        prompt_file = f'prompts/{self.current_agent}.txt'
        if not os.path.exists(prompt_file):
            prompt_file = 'prompts/nanaA.txt'  # 回退到默认模板
            
        with open(prompt_file, 'r', encoding='utf-8') as file:
            self.prompt_template = file.read()
    
    def set_agent(self, agent_name: str) -> bool:
        """设置当前使用的智能体
        
        Args:
            agent_name: 智能体名称（nanaA, nanaB, nanaC）
            
        Returns:
            bool: 是否成功切换
        """
        if agent_name not in ["nanaA", "nanaB", "nanaC"]:
            return False
            
        self.current_agent = agent_name
        self._load_prompt_template()
        return True

    def _log_conversation(self, role: str, content: str) -> None:
        """记录对话到日志文件"""
        current_date = datetime.now().strftime('%Y%m%d')
        current_time = datetime.now().strftime('%H:%M:%S')
        log_file = os.path.join(self.log_dir, f'{current_date}.txt')
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f'[{current_time}] {role.capitalize()}: {content}\n')
        
    async def reply(self, message: str, personality: str = None) -> Tuple[str, str]:
        """生成回复
        
        Args:
            message: 用户消息
            personality: 可选的性格描述，用于调整回复风格
            
        Returns:
            Tuple[str, str]: (回复内容, 表情)
        """
        # 记录用户消息
        self._log_conversation('user', message)
        
        # 获取相关记忆
        memory_text = self._get_relevant_memories(message)
        print("相关记忆:", memory_text)
        
        # 生成回复，传入性格参数
        reply_content, expression = await self._generate_reply(message, memory_text, personality)
        
        # 处理回复
        if reply_content:
            await self._handle_successful_reply(message, reply_content)
            
        return reply_content, expression

    async def _generate_reply(self, message: str, memory_text: str = "无补充信息", personality: str = None) -> Tuple[str, str]:
        """生成回复的核心方法
        
        Args:
            message: 用户消息
            memory_text: 相关记忆文本
            personality: 可选的性格描述，用于调整回复风格
            
        Returns:
            Tuple[str, str]: (回复内容, 表情)
        """
        # 准备prompt
        context = self.conversation_history.get_context()
        
        # 如果提供了性格描述，添加到提示词中
        personality_prompt = ""
        if personality:
            personality_prompt = f"\n请以以下性格特点回复: {personality}"
        
        prompt = self.prompt_template.format(
            chat_history=context,
            user_message=message,
            memory=memory_text,
            user_info=self.user_info
        ) + personality_prompt
        
        # 获取LLM回复
        reply = await self.llm_service.generate_response(prompt, is_json=True)
        if not reply:
            return "对不起，我现在有点累了，能稍后再聊吗？", "生气"
        
        # 检查是否有用户信息更新
        if "user_info" in reply:
            self._save_user_info(reply["user_info"])
            self.user_info = reply["user_info"]
        
        return reply.get("reply", ""), reply.get("expression", "")

    def _get_relevant_memories(self, message: str) -> str:
        """获取相关记忆"""
        memories = self.conversation_history.retrieve(message, n_results=2)
        if not memories:
            return "无补充信息"
            
        # 合并所有记忆，去除重复信息
        combined_memory = {}
        for memory in memories:
            # 解析记忆文本
            lines = memory.split('\n')
            for line in lines:
                if '：' in line or ':' in line:
                    key, value = line.replace('：', ':').split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        combined_memory[key] = value
        
        # 格式化输出
        if combined_memory:
            return "用户画像信息：\n" + "\n".join(f"{k}: {v}" for k, v in combined_memory.items())
        return "无补充信息"

    async def _handle_successful_reply(self, message: str, reply_content: str) -> None:
        """处理成功的回复"""
        self._log_conversation('assistant', reply_content)
        await self.conversation_history.add_dialog(message, reply_content)

    def _load_user_info(self) -> str:
        """加载用户个人信息"""
        try:
            if os.path.exists(self.user_info_file):
                with open(self.user_info_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
        except Exception as e:
            print(f"读取个人信息文件出错: {e}")
        return ""

    def _save_user_info(self, info: str) -> None:
        """保存用户个人信息"""
        try:
            with open(self.user_info_file, 'w', encoding='utf-8') as f:
                f.write(info)
        except Exception as e:
            print(f"保存个人信息文件出错: {e}")