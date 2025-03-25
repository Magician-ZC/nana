from typing import Optional, Tuple
from llm import LLMService
from tts import TTSService
from config import Config
from main_agent import MainAgent
from conversation import ConversationHistory

class ChatService:
    def __init__(self):
        # 初始化LLM服务
        self.llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)
        
        # 只在启用TTS时初始化TTS服务
        self.tts_service = TTSService(Config.FISH_API_KEY, Config.FISH_REFERENCE_ID) if Config.is_tts_enabled() else None
         
        # 初始化对话历史和主Agent
        self.conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        self.main_agent = MainAgent(self.llm_service, self.conversation_history)

    def change_agent(self, agent_name: str, session_id: str) -> bool:
        """
        切换智能体
        :param agent_name: 智能体名称
        :param session_id: 会话ID
        :return: 是否成功切换
        """
        if agent_name in ["nanaA", "nanaB", "nanaC"]:
            return self.main_agent.set_agent(agent_name)
        return False

    async def generate_reply(self, message: str, session_id: str, agent_type: Optional[str] = None, personality: Optional[str] = None, is_category: bool = False) -> Tuple[str, Optional[bytes], str, Optional[str]]:
        """
        生成回复
        :param message: 用户消息
        :param session_id: 会话ID
        :param agent_type: 智能体类型
        :param personality: 智能体的性格描述
        :param is_category: 是否是快捷提问类别
        :return: (回复文本, 语音数据, 表情, 引导决策消息)
        """
        try:
            # 如果收到新的agent_type，先切换智能体
            if agent_type and agent_type in ["nanaA", "nanaB", "nanaC"]:
                self.main_agent.set_agent(agent_type)
            
            # 使用 MainAgent 生成回复和表情，传入性格描述和快捷提问标志
            reply, expression = await self.main_agent.reply(message, personality=personality, is_category=is_category)
            
            # 检查是否有引导决策消息
            guidance_message = None
            if is_category:
                # 查看最近一次对话是否是系统引导
                if (len(self.main_agent.conversation_history.turns) >= 2 and 
                    self.main_agent.conversation_history.turns[-1].ask == "SYSTEM_GUIDANCE"):
                    guidance_message = self.main_agent.conversation_history.turns[-1].answer
            
            # 生成语音 (如果TTS服务已启用)
            audio_data = None   
            if reply and self.tts_service:
                try:
                    audio_data = self.tts_service.generate_audio(reply)
                except Exception as e:
                    print(f"生成语音时出错了喵: {e}")
            
            return reply, audio_data, expression, guidance_message
            
        except Exception as e:
            print(f"生成回复时出错了喵: {e}")
            return "对不起，我现在有点累了，能稍后再聊吗？", None, "生气", None