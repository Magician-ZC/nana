from typing import Optional, Tuple
from llm import LLMService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from main_agent import MainAgent
from conversation import ConversationHistory
import os
import json

class ChatService:
    def __init__(self):
        # 初始化LLM服务
        self.llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)
        
        # 初始化TTS服务（根据配置决定是否创建实例）
        self._refresh_tts_services()
         
        # 初始化对话历史和主Agent
        self.conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        self.main_agent = MainAgent(self.llm_service, self.conversation_history)
        
        # 自定义agent目录
        self.custom_agents_dir = "save/custom_agents"
        os.makedirs(self.custom_agents_dir, exist_ok=True)

    def _refresh_tts_services(self):
        """根据当前配置刷新TTS服务实例"""
        # 普通TTS服务
        self.tts_service = TTSService(Config.TTS_VCN) if Config.is_tts_enabled() else None
        # 超拟人TTS服务
        self.super_tts_service = SuperTTSService(Config.SUPER_TTS_VCN) if Config.is_super_tts_enabled() else None

    def change_agent(self, agent_name: str, session_id: str) -> bool:
        """
        切换智能体
        :param agent_name: 智能体名称
        :param session_id: 会话ID
        :return: 是否成功切换
        """
        if agent_name in ["nanaA", "nanaB", "nanaC"]:
            return self.main_agent.set_agent(agent_name)
        elif agent_name.startswith("custom_"):
            # 加载自定义角色
            config_path = os.path.join(self.custom_agents_dir, f"{agent_name}.json")
            prompt_path = os.path.join(self.custom_agents_dir, f"{agent_name}.txt")
            
            if os.path.exists(config_path) and os.path.exists(prompt_path):
                try:
                    # 读取配置文件
                    with open(config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    
                    # 读取提示词文件
                    with open(prompt_path, "r", encoding="utf-8") as f:
                        prompt = f.read()
                    
                    # 设置自定义角色
                    return self.main_agent.set_custom_agent(prompt, config)
                except Exception as e:
                    print(f"加载自定义角色失败: {e}")
                    return False
            else:
                print(f"自定义角色文件不存在: {agent_name}")
                return False
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
            # 确保消息非空
            if not message or not message.strip():
                return "请输入有效的消息内容", None, "生气", None
            
            # 确保TTS服务使用最新的配置
            self._refresh_tts_services()
            
            # 如果收到新的agent_type，先切换智能体
            if agent_type:
                self.change_agent(agent_type, session_id)
            
            # 使用 MainAgent 生成回复和表情，传入性格描述和快捷提问标志
            reply, expression = await self.main_agent.reply(message, personality=personality, is_category=is_category)
            
            # 确保回复不为空
            if not reply:
                return "抱歉，我现在无法回答您的问题，请稍后再试。", None, "生气", None
            
            # 检查是否有引导决策消息
            guidance_message = None
            if is_category:
                # 查看最近一次对话是否是系统引导
                if (len(self.main_agent.conversation_history.turns) >= 2 and 
                    self.main_agent.conversation_history.turns[-1].ask == "SYSTEM_GUIDANCE"):
                    guidance_message = self.main_agent.conversation_history.turns[-1].answer
            
            # 生成语音 (如果语音服务已启用)
            audio_data = None  
            super_tts_error = None
            tts_error = None
            
            # 优先使用超拟人TTS，如果启用
            if reply and self.super_tts_service:
                try:
                    print("尝试使用超拟人TTS生成语音...")
                    audio_data = self.super_tts_service.generate_audio(reply)
                    if audio_data and len(audio_data) > 100:  # 确保生成的音频数据有效
                        print(f"超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                    else:
                        super_tts_error = "生成的音频数据无效或过小"
                        print(f"超拟人TTS生成失败: {super_tts_error}")
                except Exception as e:
                    super_tts_error = str(e)
                    print(f"生成超拟人语音时出错: {e}")
            
            # 如果超拟人TTS失败或未启用，尝试使用普通TTS
            if (not audio_data or len(audio_data) < 100) and self.tts_service:
                try:
                    print("尝试使用普通TTS生成语音...")
                    audio_data = self.tts_service.generate_audio(reply)
                    if audio_data and len(audio_data) > 100:
                        print(f"普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                    else:
                        tts_error = "生成的音频数据无效或过小"
                        print(f"普通TTS生成失败: {tts_error}")
                except Exception as e:
                    tts_error = str(e)
                    print(f"生成普通语音时出错: {e}")
            
            # 如果两种TTS都失败了，记录详细错误
            if (not audio_data or len(audio_data) < 100) and (super_tts_error or tts_error):
                print("所有TTS服务都失败了:")
                if super_tts_error:
                    print(f"- 超拟人TTS错误: {super_tts_error}")
                if tts_error:
                    print(f"- 普通TTS错误: {tts_error}")
                
                # 尝试对回复进行截断处理，再次生成语音
                if len(reply) > 50:  # 如果回复较长，尝试只处理前50个字符
                    short_reply = reply[:50] + "..."
                    print(f"尝试使用截断回复生成语音: {short_reply}")
                    
                    try:
                        if self.tts_service:
                            audio_data = self.tts_service.generate_audio(short_reply)
                            if audio_data and len(audio_data) > 100:
                                print(f"使用截断回复生成语音成功，音频大小: {len(audio_data)} 字节")
                    except Exception as e:
                        print(f"使用截断回复生成语音也失败了: {e}")
            
            return reply, audio_data, expression, guidance_message
            
        except Exception as e:
            print(f"生成回复时出错: {e}")
            error_message = "对不起，我现在有点累了，能稍后再聊吗？"
            
            # 记录详细错误信息供调试
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            
            return error_message, None, "生气", None