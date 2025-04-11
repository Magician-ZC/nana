from typing import Optional, Tuple
from llm import LLMService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from main_agent import MainAgent
from conversation import ConversationHistory
import os
import json
import asyncio

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

        self.current_agent = "nanaA"
        self.guidance_state = {
            "is_guiding": False,
            "current_category": None,
            "question_count": 0,
            "last_question_type": None,
            "conversation_summary": [],
            "off_topic_count": 0,  # 跟踪连续偏离主题的次数
            "last_strategies": [],  # 记录已经使用过的策略
            "awaiting_exit_confirmation": False,  # 是否正在等待用户确认退出
            "confirmed_exit": False  # 用户是否已确认退出
        }

    def _refresh_tts_services(self):
        """刷新TTS服务配置"""
        try:
            self.tts_service = TTSService()
            self.super_tts_service = SuperTTSService()  # 添加超拟人TTS服务的初始化
        except Exception as e:
            print(f"刷新TTS服务失败: {e}")
            self.tts_service = None
            self.super_tts_service = None  # 确保在失败时也设置属性

    def _reset_guidance_state(self):
        """重置引导状态"""
        self.guidance_state = {
            "is_guiding": False,
            "current_category": None,
            "question_count": 0,
            "last_question_type": None,
            "conversation_summary": [],
            "off_topic_count": 0,  # 跟踪连续偏离主题的次数
            "last_strategies": [],  # 记录已经使用过的策略
            "awaiting_exit_confirmation": False,  # 是否正在等待用户确认退出
            "confirmed_exit": False  # 用户是否已确认退出
        }

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
            
            # 检查是否是结束引导的明确指令
            exit_guidance_keywords = ["结束话题", "结束引导", "不想聊了", "换个话题", "不想继续", "结束对话", "不想讨论这个", "不讨论", "换话题", "算了", "不聊了", "结束"]
            is_exit_guidance = (self.guidance_state["is_guiding"] and 
                              (any(keyword in message for keyword in exit_guidance_keywords) or message.strip() == "结束"))
            
            # 如果用户表示想要结束话题，直接结束引导
            if is_exit_guidance:
                print(f"用户请求结束引导，直接结束：{message}")
                self.guidance_state["confirmed_exit"] = True
                # 准备一个回复，表明已经结束引导
                reply_text = "已结束当前话题。您还有其他想讨论的问题吗？"
                reply_data = {
                    "reply": reply_text,
                    "expression": "微笑",
                    "is_question": True,
                    "is_summary": True,
                    "question_type": "summary"
                }
                
                # 重置引导状态
                self._reset_guidance_state()
                
                # 生成语音
                audio_data = None
                if Config.is_tts_enabled() and self.tts_service:
                    try:
                        print("为结束引导回复生成普通TTS...")
                        audio_data = self.tts_service.generate_audio(reply_text)
                    except Exception as e:
                        print(f"为结束引导回复生成普通语音时出错: {e}")
                
                if (not audio_data or len(audio_data) < 100) and Config.is_super_tts_enabled() and self.super_tts_service:
                    try:
                        print("为结束引导回复生成超拟人TTS...")
                        audio_data = self.super_tts_service.generate_audio(reply_text)
                    except Exception as e:
                        print(f"为结束引导回复生成超拟人语音时出错: {e}")
                
                return reply_text, audio_data, reply_data.get("expression", "微笑"), None
            
            # 处理引导式提问状态
            if is_category and not self.guidance_state["is_guiding"]:
                print(f"开始引导式提问：{message}")
                self.guidance_state["is_guiding"] = True
                self.guidance_state["current_category"] = message
                self.guidance_state["question_count"] = 0
                self.guidance_state["conversation_summary"] = []
                self.guidance_state["off_topic_count"] = 0
                self.guidance_state["last_strategies"] = []
                self.guidance_state["awaiting_exit_confirmation"] = False
                self.guidance_state["confirmed_exit"] = False
            
            # 使用 MainAgent 生成回复和表情，传入性格描述和快捷提问标志
            current_is_category = is_category or self.guidance_state["is_guiding"] 
            reply, expression = await self.main_agent.reply(message, personality=personality, is_category=current_is_category)
            
            # 确保回复不为空
            if not reply:
                return "抱歉，我现在无法回答您的问题，请稍后再试。", None, "生气", None
            
            # 处理引导式提问的回复
            if self.guidance_state["is_guiding"]:
                try:
                    reply_data = json.loads(reply)
                    
                    # 更新引导状态
                    question_type = reply_data.get("question_type", "")
                    self.guidance_state["last_question_type"] = question_type
                    self.guidance_state["question_count"] += 1
                    
                    # 更新偏离主题计数
                    if question_type == "refocus":
                        self.guidance_state["off_topic_count"] += 1
                    else:
                        # 如果不是refocus，重置计数
                        self.guidance_state["off_topic_count"] = 0
                    
                    # 记录对话内容
                    if message and not reply_data.get("is_summary") and not reply_data.get("is_confirmation", False):
                        self.guidance_state["conversation_summary"].append({
                            "question": reply_data.get("reply", ""),
                            "answer": message,
                            "type": question_type
                        })
                    
                    # 如果是总结或者用户已确认退出，重置引导状态
                    if reply_data.get("is_summary") or self.guidance_state.get("confirmed_exit", False):
                        print("引导结束，重置状态")
                        self._reset_guidance_state()
                    
                    print(f"引导状态: 问题类型={question_type}, 偏离主题次数={self.guidance_state['off_topic_count']}")
                    
                    # 为xinli_agent生成语音
                    reply_text = reply_data.get("reply", "")
                    audio_data = None
                    
                    # 根据配置决定使用哪个TTS服务为心理咨询回复生成语音
                    if Config.is_tts_enabled() and self.tts_service:
                        try:
                            print("为心理咨询回复生成普通TTS...")
                            audio_data = self.tts_service.generate_audio(reply_text)
                            if audio_data and len(audio_data) > 100:
                                print(f"心理咨询回复普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                            else:
                                print("心理咨询回复普通TTS生成失败: 生成的音频数据无效或过小")
                        except Exception as e:
                            print(f"为心理咨询回复生成普通语音时出错: {e}")
                    
                    # 如果普通TTS失败或未启用，且配置了使用超拟人TTS，则尝试使用超拟人TTS
                    if (not audio_data or len(audio_data) < 100) and Config.is_super_tts_enabled() and self.super_tts_service:
                        try:
                            print("为心理咨询回复生成超拟人TTS...")
                            audio_data = self.super_tts_service.generate_audio(reply_text)
                            if audio_data and len(audio_data) > 100:
                                print(f"心理咨询回复超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                            else:
                                print("心理咨询回复超拟人TTS生成失败: 生成的音频数据无效或过小")
                        except Exception as e:
                            print(f"为心理咨询回复生成超拟人语音时出错: {e}")
                    
                    return reply_text, audio_data, reply_data.get("expression", "咪咪眼"), None
                except json.JSONDecodeError:
                    print(f"解析引导式提问回复失败: {reply}")
                    # 如果是退出指令，强制重置状态
                    if self.guidance_state.get("confirmed_exit", False):
                        self._reset_guidance_state()
                    
                    # 尝试为解析失败的回复也生成语音
                    audio_data = None
                    if Config.is_tts_enabled() and self.tts_service:
                        try:
                            print("为解析失败的回复生成普通TTS...")
                            audio_data = self.tts_service.generate_audio(reply)
                            if audio_data and len(audio_data) > 100:
                                print(f"解析失败回复普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                            else:
                                print("解析失败回复普通TTS生成失败: 生成的音频数据无效或过小")
                        except Exception as e:
                            print(f"为解析失败的回复生成普通语音时出错: {e}")
                    
                    # 如果普通TTS失败，尝试超拟人TTS
                    if (not audio_data or len(audio_data) < 100) and Config.is_super_tts_enabled() and self.super_tts_service:
                        try:
                            print("为解析失败的回复生成超拟人TTS...")
                            audio_data = self.super_tts_service.generate_audio(reply)
                            if audio_data and len(audio_data) > 100:
                                print(f"解析失败回复超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                            else:
                                print("解析失败回复超拟人TTS生成失败: 生成的音频数据无效或过小")
                        except Exception as e:
                            print(f"为解析失败的回复生成超拟人语音时出错: {e}")
                    
                    # 尝试手动构建一个有效的回复
                    return reply, audio_data, expression, None
            
            # 检查是否有引导决策消息
            guidance_message = None
            if is_category:
                # 查看最近一次对话是否是系统引导
                if (len(self.main_agent.conversation_history.turns) >= 2 and 
                    self.main_agent.conversation_history.turns[-1].ask == "SYSTEM_GUIDANCE"):
                    guidance_message = self.main_agent.conversation_history.turns[-1].answer
            elif hasattr(self.main_agent.conversation_history, 'last_guidance_message'):
                guidance_message = self.main_agent.conversation_history.last_guidance_message
            
            # 生成语音 (如果语音服务已启用)
            audio_data = None
            super_tts_error = None
            tts_error = None
            
            # 根据配置决定使用哪个TTS服务
            if Config.is_tts_enabled() and self.tts_service:
                try:
                    print("尝试使用普通TTS生成语音...")
                    audio_data = self.tts_service.generate_audio(reply)
                    if audio_data and len(audio_data) > 100:  # 确保生成的音频数据有效
                        print(f"普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                    else:
                        tts_error = "生成的音频数据无效或过小"
                        print(f"普通TTS生成失败: {tts_error}")
                except Exception as e:
                    tts_error = str(e)
                    print(f"生成普通语音时出错: {e}")
            
            # 如果普通TTS失败或未启用，且配置了使用超拟人TTS，则尝试使用超拟人TTS
            if (not audio_data or len(audio_data) < 100) and Config.is_super_tts_enabled() and self.super_tts_service:
                try:
                    print("尝试使用超拟人TTS生成语音...")
                    audio_data = self.super_tts_service.generate_audio(reply)
                    if audio_data and len(audio_data) > 100:
                        print(f"超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                    else:
                        super_tts_error = "生成的音频数据无效或过小"
                        print(f"超拟人TTS生成失败: {super_tts_error}")
                except Exception as e:
                    super_tts_error = str(e)
                    print(f"生成超拟人语音时出错: {e}")
            
            # 如果有引导决策消息，同样为其生成语音并保存到临时属性中
            if guidance_message:
                try:
                    # 使用异步方式生成语音，避免阻塞
                    loop = asyncio.get_running_loop()
                    
                    # 根据配置决定使用哪个TTS服务
                    if Config.is_tts_enabled() and self.tts_service:
                        print("尝试为引导决策消息生成普通TTS...")
                        
                        # 使用超时控制，防止阻塞
                        try:
                            guidance_audio = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None, 
                                    self.tts_service.generate_audio, 
                                    guidance_message
                                ),
                                timeout=10.0
                            )
                            
                            if guidance_audio and len(guidance_audio) > 100:
                                # 将引导决策音频保存到临时属性中，供API响应获取
                                self.main_agent.conversation_history.guidance_audio = guidance_audio
                                print(f"引导决策普通TTS生成成功，音频大小: {len(guidance_audio)} 字节")
                        except asyncio.TimeoutError:
                            print("引导决策普通TTS生成超时")
                        except Exception as e:
                            print(f"引导决策普通TTS生成出错: {e}")
                    
                    # 如果普通TTS失败或未启用，且配置了使用超拟人TTS，则尝试使用超拟人TTS
                    if not hasattr(self.main_agent.conversation_history, 'guidance_audio') and Config.is_super_tts_enabled() and self.super_tts_service:
                        print("尝试为引导决策消息生成超拟人TTS...")
                        
                        # 使用超时控制，防止阻塞
                        try:
                            guidance_audio = await asyncio.wait_for(
                                loop.run_in_executor(
                                    None, 
                                    self.super_tts_service.generate_audio, 
                                    guidance_message
                                ),
                                timeout=10.0
                            )
                            
                            if guidance_audio and len(guidance_audio) > 100:
                                # 将引导决策音频保存到临时属性中，供API响应获取
                                self.main_agent.conversation_history.guidance_audio = guidance_audio
                                print(f"引导决策超拟人TTS生成成功，音频大小: {len(guidance_audio)} 字节")
                        except asyncio.TimeoutError:
                            print("引导决策超拟人TTS生成超时")
                        except Exception as e:
                            print(f"引导决策超拟人TTS生成出错: {e}")
                
                except Exception as e:
                    print(f"生成引导决策语音时出错: {e}")
            
            return reply, audio_data, expression, guidance_message
            
        except Exception as e:
            print(f"生成回复时出错: {e}")
            return "抱歉，发生了错误，请稍后再试。", None, "生气", None