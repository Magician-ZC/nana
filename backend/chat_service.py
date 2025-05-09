from typing import Optional, Tuple, List, Dict, Any, AsyncGenerator
from llm import LLMService
from tts import TTSService
from super_tts import SuperTTSService
from config import Config
from main_agent import MainAgent
from conversation import ConversationHistory
import os
import json
import asyncio
import base64
from datetime import datetime
import re
import traceback
import time

class ChatService:
    def __init__(self):
        # 初始化LLM服务
        self.llm_service = LLMService(Config.LLM_API_KEY, Config.LLM_API_URL)
        
        # 设置LLM服务的chat_service引用为自身
        self.llm_service.chat_service = self
        
        # 初始化TTS服务（根据配置决定是否创建实例）
        self._refresh_tts_services()
         
        # 初始化对话历史记录
        self.conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        
        # 添加引导模式专用的对话历史记录
        self.guided_conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        
        # 添加引导模式专用的用户信息
        self.guided_user_info = None
        
        # 自定义agent目录
        self.custom_agents_dir = "save/custom_agents"
        os.makedirs(self.custom_agents_dir, exist_ok=True)

        self.current_agent = "nanaA"
        self.current_response = ""  # 初始化当前响应变量
        self.guidance_state = {
            "is_guiding": False,
            "category": None,
            "stage": None,
            "question_count": 0,
            "divergent_count": 0,
            "last_update_time": time.time()
        }

        # 初始化主智能体
        self.main_agent = MainAgent(self.llm_service, self.conversation_history)

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
        """重置引导式会话状态"""
        print("重置引导式会话状态")
        
        # 重置引导状态标志
        self.guidance_state = {
            "is_guiding": False,
            "category": None,
            "stage": None,
            "question_count": 0,
            "divergent_count": 0,
            "last_update_time": time.time()
        }
        
        # 重置引导式用户信息
        self.guided_user_info = None
        
        # 清除引导式对话历史的临时属性
        if hasattr(self.main_agent.conversation_history, 'last_guidance_message'):
            delattr(self.main_agent.conversation_history, 'last_guidance_message')
        
        if hasattr(self.main_agent.conversation_history, 'guidance_audio'):
            delattr(self.main_agent.conversation_history, 'guidance_audio')
            
        # 清除可能导致状态混乱的标记
        # 重置最近的消息分类，防止普通消息被误认为引导消息
        for turn in self.main_agent.conversation_history.turns[-5:]:
            if hasattr(turn, 'is_guidance'):
                delattr(turn, 'is_guidance')
                
        print("引导式会话状态已完全重置")

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

    async def generate_reply(self, message: str, session_id: str, agent_type: Optional[str] = None, personality: Optional[str] = None, is_category: bool = False, stream: bool = False) -> Tuple[str, Optional[bytes]]:
        """生成回复
        
        Args:
            message: 用户消息
            session_id: 会话ID
            agent_type: 智能体类型
            personality: 智能体的性格描述
            is_category: 是否是快捷提问类别
            stream: 是否使用流式生成
            
        Returns:
            Tuple[str, Optional[bytes]]: (回复文本, 语音数据) 或者在流式模式下 (AsyncGenerator[str, None], None)
        """
        try:
            # 确保消息非空
            if not message or not message.strip():
                return "请输入有效的消息内容", None
            
            # 确保TTS服务使用最新的配置
            self._refresh_tts_services()
            
            # 如果收到新的agent_type，先切换智能体
            if agent_type:
                self.change_agent(agent_type, session_id)
            
            # 记录用户消息到日志，但不立即添加到对话历史
            self.main_agent._log_conversation('user', message)
            
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
                
                # 添加本次对话到历史
                await self.main_agent.conversation_history.add_dialog(message, reply_text, self.main_agent.user_info_processor)
                
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
                
                return reply_text, audio_data
            
            # 处理引导式提问状态
            if is_category and not self.guidance_state["is_guiding"]:
                print(f"开始引导式提问：{message}")
                # 设置引导状态
                self.guidance_state["is_guiding"] = True
                self.guidance_state["current_category"] = message
                self.guidance_state["question_count"] = 0
                self.guidance_state["conversation_summary"] = []
                self.guidance_state["off_topic_count"] = 0
                self.guidance_state["last_strategies"] = []
                self.guidance_state["awaiting_exit_confirmation"] = False
                self.guidance_state["confirmed_exit"] = False
                
                # 初始化引导模式的局部用户信息，只保留基本信息
                if self.main_agent.user_info:
                    # 提取用户的基本信息（姓名、年龄、性别、学校、专业等）
                    basic_info_lines = []
                    user_info_lines = self.main_agent.user_info.split('\n')
                    for line in user_info_lines:
                        if any(key in line.lower() for key in ["姓名:", "年龄:", "性别:", "学校:", "专业:", "年级:"]):
                            basic_info_lines.append(line)
                    
                    # 创建引导模式的局部用户信息
                    self.guided_user_info = '\n'.join(basic_info_lines)
                    if self.guided_user_info:
                        self.guided_user_info += "\n\n当前引导主题：" + message
                else:
                    self.guided_user_info = "当前引导主题：" + message
                
                # 保存当前的对话历史并切换到引导模式的对话历史
                self.main_agent.conversation_history = self.guided_conversation_history
                print(f"已切换到引导模式对话历史，当前引导模式对话历史长度: {len(self.guided_conversation_history.turns)}")
            
            # 获取当前对话上下文
            context = self.main_agent.conversation_history.get_context()
            print(f"使用对话上下文：\n{context}")
            
            # 将当前用户消息临时添加到上下文，但不添加到对话历史
            current_context = context
            if context:
                current_context += f"\n用户: {message}"
            else:
                current_context = f"用户: {message}"
            
            # 使用 MainAgent 生成回复和表情，但传入增强的上下文
            current_is_category = is_category or self.guidance_state["is_guiding"] 
            current_personality = None if self.guidance_state["is_guiding"] else personality
            
            # 使用增强的上下文调用_generate_reply方法
            memory_text = "无补充信息"
            if not current_is_category:
                memory_text = self.main_agent._get_relevant_memories(message)
                print("相关记忆:", memory_text)
            else:
                print("引导模式中，不使用用户记忆信息")
            
            # 如果是流式模式，使用流式API生成回复
            if stream:
                # 构建完整提示词
                prompt_template = self.main_agent.prompt_template
                if current_personality:
                    prompt_template += f"\n请以以下性格特点回复: {current_personality}"
                    
                # 构建提示词
                prompt = f"{prompt_template}\n\n用户信息：\n{self.main_agent.user_info}\n\n当前对话记录：\n{current_context}\n\n当前所有对话相关的历史记忆：\n{memory_text}\n\n助手:"
                print("发送流式请求...")
                
                # 添加对话到历史（先添加用户消息）
                # 添加一个空回复，后续通过历史检索获取完整内容
                await self.main_agent.conversation_history.add_dialog(message, "", self.main_agent.user_info_processor)
                
                # 返回流式生成器和None作为语音
                return self.llm_service.generate_streaming(prompt), None
                
            # 直接调用_generate_reply，传入当前上下文
            reply, expression = await self.main_agent._generate_reply_with_context(
                message, 
                current_context,
                memory_text, 
                current_personality, 
                current_is_category
            )
            
            # 确保回复不为空
            if not reply:
                return "抱歉，我现在无法回答您的问题，请稍后再试。", None
            
            # 添加对话到历史
            await self.main_agent.conversation_history.add_dialog(message, reply, self.main_agent.user_info_processor)
            print(f"对话已添加到历史记录，当前对话历史长度: {len(self.main_agent.conversation_history.turns)}")
            
            # 检查是否需要压缩对话历史（对话超过8轮时）
            if len(self.main_agent.conversation_history.turns) > 8:
                self._compress_guided_conversation_history(max_recent_turns=4)
            
            # 记录会话总结（如果不是总结类型）
            try:
                # 如果reply_data已经定义并且是一个字典
                if 'reply_data' in locals() and isinstance(reply_data, dict):
                    if message and not reply_data.get("is_summary") and not reply_data.get("is_confirmation", False):
                        self.guidance_state["conversation_summary"].append({
                            "question": reply_data.get("reply", ""),
                            "answer": message,
                            "type": reply_data.get("question_type", "")
                        })
            except Exception as e:
                print(f"记录对话摘要时出错: {e}")
            
            # 处理引导式提问的回复
            if self.guidance_state["is_guiding"]:
                try:
                    reply_data = json.loads(reply)
                    
                    # 更新引导状态
                    question_type = reply_data.get("question_type", "")
                    self.guidance_state["last_question_type"] = question_type
                    self.guidance_state["question_count"] += 1
                    
                    # 检查是否包含用户信息更新（user_info字段）
                    if "user_info" in reply_data and isinstance(reply_data["user_info"], dict):
                        # 更新引导模式的局部用户信息
                        for key, value in reply_data["user_info"].items():
                            self.update_guided_user_info(key, value)
                    
                    # 检查回复文本是否包含明确的用户信息
                    if reply_data.get("reply", "") and reply_data.get("question_type", "") != "summary":
                        # 识别基于冒号的模式 "主题: 内容"
                        info_matches = re.findall(r'([^:：]+)[：:]\s*([^\n]+)', reply_data["reply"])
                        for key, value in info_matches:
                            key = key.strip()
                            value = value.strip()
                            if key and value and key.lower() not in ["ai", "助手", "我", "你", "我们", "您"]:
                                self.update_guided_user_info(key, value)
                    
                    # 更新偏离主题计数
                    if question_type == "refocus":
                        self.guidance_state["off_topic_count"] += 1
                    else:
                        # 如果不是refocus，重置计数
                        self.guidance_state["off_topic_count"] = 0
                    
                    # 记录对话内容
                    if reply_data.get("reply", "") and not reply_data.get("is_summary") and not reply_data.get("is_confirmation", False):
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
                    
                    return reply_text, audio_data
                except json.JSONDecodeError:
                    print(f"解析引导式提问回复失败: {reply}")
                    # 如果是退出指令，强制重置状态
                    if self.guidance_state.get("confirmed_exit", False):
                        self._reset_guidance_state()
                    
                    # 尝试为解析失败的回复也生成语音
                    audio_data = None
                    
                    # 处理可能是JSON格式的回复
                    reply_text = reply
                    try:
                        if reply.strip().startswith('{') and reply.strip().endswith('}'):
                            # 尝试解析JSON
                            reply_json = json.loads(reply)
                            if "reply" in reply_json:
                                reply_text = reply_json["reply"]
                                print(f"解析失败，但从JSON中提取到纯文本: {reply_text}")
                    except:
                        # 如果解析失败，使用原始回复
                        pass
                    
                    if Config.is_tts_enabled() and self.tts_service:
                        try:
                            print("为解析失败的回复生成普通TTS...")
                            audio_data = self.tts_service.generate_audio(reply_text)  # 使用处理过的纯文本
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
                            audio_data = self.super_tts_service.generate_audio(reply_text)  # 使用处理过的纯文本
                            if audio_data and len(audio_data) > 100:
                                print(f"解析失败回复超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                            else:
                                print("解析失败回复超拟人TTS生成失败: 生成的音频数据无效或过小")
                        except Exception as e:
                            print(f"为解析失败的回复生成超拟人语音时出错: {e}")
                    
                    # 尝试手动构建一个有效的回复
                    return reply, audio_data
            
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
            
            # 处理可能是JSON格式的回复
            reply_text = reply
            try:
                if reply.strip().startswith('{') and reply.strip().endswith('}'):
                    # 尝试解析JSON
                    reply_json = json.loads(reply)
                    if "reply" in reply_json:
                        reply_text = reply_json["reply"]
                        print(f"从JSON格式的回复中提取纯文本: {reply_text}")
            except:
                # 如果解析失败，使用原始回复
                pass
            
            # 根据配置决定使用哪个TTS服务
            if Config.is_tts_enabled() and self.tts_service:
                try:
                    print("尝试使用普通TTS生成语音...")
                    audio_data = self.tts_service.generate_audio(reply_text)  # 使用处理过的纯文本
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
                    audio_data = self.super_tts_service.generate_audio(reply_text)  # 使用处理过的纯文本
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
            
            return reply, audio_data
            
        except Exception as e:
            print(f"生成回复时出错: {e}")
            return "抱歉，发生了错误，请稍后再试。", None

    async def generate_response(self, history, model_name="gpt-3.5-turbo", stream=False, agent_id=None, is_category=False, message=None):
        """生成流式响应
        
        Args:
            history: 对话历史
            model_name: 模型名称
            stream: 是否流式响应
            agent_id: 角色ID
            is_category: 是否是快捷提问类别
            message: 当前消息
            
        Returns:
            tuple: (回复内容, 音频数据)
        """
        try:
            # 确保TTS服务使用最新的配置
            self._refresh_tts_services()
            
            # 如果收到agent_id，先切换智能体
            if agent_id:
                self.change_agent(agent_id, "default_session")
            
            # 使用传入的message覆盖，或从对话历史中获取
            user_msg = message if message else (history[-1]["content"] if history else "")
            print(f"generate_response: 用户消息: {user_msg}, 是否是快捷提问: {is_category}")
            
            # 生成回复
            raw_response, audio_data = await self.generate_reply(
                message=user_msg,
                session_id="default", 
                agent_type=model_name,
                is_category=is_category
            )
            
            # 处理JSON格式回复
            response = raw_response
            expression = None
            
            # 处理双花括号格式 {{...}}
            if raw_response.strip().startswith('{{') and raw_response.strip().endswith('}}'):
                try:
                    # 去除双花括号
                    json_content = raw_response.strip()[2:-2].strip()
                    print("检测到双花括号格式，已修正为标准JSON")
                    
                    # 解析JSON
                    data = json.loads(json_content)
                    if 'reply' in data:
                        print(f"从双花括号JSON中提取reply内容")
                        response = data['reply']
                        if 'expression' in data:
                            expression = data['expression']
                            self.main_agent.expression = expression
                except json.JSONDecodeError:
                    print("双花括号内容不是有效的JSON格式，使用原始回复")
                except Exception as e:
                    print(f"处理双花括号JSON回复时出错: {e}")
            
            # 处理单花括号格式 {...}
            elif raw_response.strip().startswith('{') and raw_response.strip().endswith('}'):
                try:
                    data = json.loads(raw_response)
                    if 'reply' in data:
                        print("从JSON响应中提取reply字段")
                        response = data['reply']
                        if 'expression' in data:
                            expression = data['expression']
                            self.main_agent.expression = expression
                except json.JSONDecodeError:
                    print("回复不是有效的JSON格式，使用原始回复")
                except Exception as e:
                    print(f"处理JSON响应失败: {e}")
            
            # 如果不在引导模式中但已存在引导模式数据，清理引导模式的用户信息和对话历史
            if not is_category and not self.guidance_state["is_guiding"] and self.guided_user_info:
                # 重置引导模式数据
                self.guided_user_info = None
                self.guided_conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
                print("清理了旧的引导模式数据")
                
            # 记录用户消息和回复到对话历史
            await self.conversation_history.add_dialog(message=user_msg, reply=response)
            print(f"对话历史: 当前共有{len(self.conversation_history.turns)}轮对话")
            
            return response, audio_data
        except Exception as e:
            print(f"生成回复时出错: {e}")
            return "抱歉，我遇到了一些问题，请稍后再试。", None

    async def response_stream(self, message: str, session_id: str, agent_type: Optional[str] = None, personality: Optional[str] = None, is_category: bool = False):
        """流式生成回复，以generator形式返回
        
        Args:
            message: 用户消息
            session_id: 会话ID
            agent_type: 智能体类型
            personality: 智能体的性格描述
            is_category: 是否是快捷提问类别
            
        Yields:
            Dict: 包含回复文本部分的字典
        """
        try:
            # 使用stream=True调用generate_reply
            stream_response, _ = await self.generate_reply(
                message, 
                session_id, 
                agent_type, 
                personality, 
                is_category,
                stream=True
            )
            
            # 处理流式响应
            accumulated_text = ""
            async for text_chunk in stream_response:
                accumulated_text += text_chunk
                # 构建响应字典
                response_dict = {
                    "reply": accumulated_text,
                    "id": session_id,
                    "is_streaming": True
                }
                
                # 生成JSON响应并返回
                yield json.dumps(response_dict, ensure_ascii=False)
            
            # 确保流式回复内容存入历史记录
            if accumulated_text:
                # 找到最后一条对话，它应该是我们之前添加的带有空回复的对话
                last_dialog = self.main_agent.conversation_history.turns[-1]
                if last_dialog and last_dialog.get('response', '') == '':
                    # 更新最后一条对话的回复内容
                    last_dialog['response'] = accumulated_text
                    print(f"已更新流式回复到对话历史，内容长度: {len(accumulated_text)}")
                
                # 标记流式处理结束
                final_response = {
                    "reply": accumulated_text,
                    "id": session_id,
                    "is_streaming": False,
                    "is_complete": True
                }
                yield json.dumps(final_response, ensure_ascii=False)
                
        except Exception as e:
            error_msg = f"流式生成回复时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            error_response = {
                "reply": "抱歉，处理您的请求时出现了错误，请稍后再试。",
                "id": session_id,
                "is_streaming": False,
                "is_error": True
            }
            yield json.dumps(error_response, ensure_ascii=False)

    async def _get_conversation_summary(self, turns_to_summarize):
        """生成会话总结，适用于结束话题时
        
        Args:
            turns_to_summarize: 要总结的对话轮次
            
        Returns:
            str: 会话总结文本
        """
        try:
            # 获取当前角色是否是心理咨询师
            is_xinli_mode = self.guidance_state.get("current_category") in [
                "情感咨询师", "人际关系", "学业问题", "就业与职业规划压力", 
                "精神健康障碍", "自我认同与价值观冲突", "突发事件与危机情景"
            ]
            
            # 准备对话内容
            all_text = "\n".join([f"用户: {turn.ask}\n助手: {turn.answer}" for turn in turns_to_summarize])
            
            # 根据角色选择不同的总结提示
            if is_xinli_mode:
                summary_prompt = f"""作为专业心理医生，请对以下对话进行简短总结。
                
                总结要点：
                1. 用户提出的主要问题或困扰
                2. 用户表现出的情感状态和核心需求
                3. 你提供的关键建议和支持
                4. 鼓励性的结束语，体现专业心理医生的关怀和支持
                
                总结控制在150字以内，语气专业、温和，避免过度亲昵或使用非专业性语言。
                不要使用"我们"，而是使用"您"来指代用户，保持适当的专业距离。
                
                对话内容：
                {all_text}
                """
            else:
                # 普通角色的总结风格
                summary_prompt = f"""请对以下对话进行简短总结。
                
                请总结：
                1. 对话的主要内容
                2. 讨论的关键点
                3. 友好的结束语
                
                总结控制在100字以内。
                
                对话内容：
                {all_text}
                """
            
            # 使用LLM生成总结
            summary_response = await self.llm_service.generate_response(summary_prompt)
            return summary_response
        except Exception as e:
            print(f"生成对话总结时出错: {e}")
            return "已结束当前话题。您有什么其他想要讨论的问题吗？"

    @staticmethod
    def _format_guided_conversation_context(context, current_message=None):
        """格式化引导模式对话历史记录，增强记忆能力
        
        Args:
            context: 原始对话历史上下文
            current_message: 当前用户消息（可选）
            
        Returns:
            str: 格式化后的上下文
        """
        if not context:
            # 如果没有上下文但有当前消息
            if current_message:
                return f"对话历史：\n用户: {current_message}"
            return "对话历史：\n尚无对话历史"
            
        # 确保context是字符串
        if not isinstance(context, str):
            try:
                context = str(context)
            except:
                return "对话历史格式化错误"
                
        # 按行拆分对话历史
        lines = context.strip().split('\n')
        formatted_lines = []
        
        # 对话历史摘要标记
        summary_found = False
        
        # 将对话历史格式化为更明确的"用户-助手"交替格式
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 检测系统摘要行
            if "SYSTEM_SUMMARY" in line or "之前的对话摘要" in line:
                summary_found = True
                # 提取摘要内容并格式化为专门的摘要行
                if ": " in line:
                    summary_content = line.split(": ", 1)[1].strip()
                    formatted_lines.append(f"【对话摘要】: {summary_content}")
                else:
                    # 如果下一行是摘要内容
                    if i+1 < len(lines) and "之前的对话摘要" in lines[i+1]:
                        formatted_lines.append(f"【对话摘要】: {lines[i+1].strip()}")
                continue
            
            # 如果前一行已处理过摘要，则跳过摘要内容行
            if summary_found and i > 0 and ("SYSTEM_SUMMARY" in lines[i-1] or "之前的对话摘要" in lines[i-1]):
                summary_found = False
                continue
                
            # 检测并格式化对话行
            if line.startswith("用户:") or line.startswith("用户："):
                formatted_lines.append(f"用户: {line.split(':', 1)[1].strip()}")
            elif line.startswith("助手:") or line.startswith("助手："):
                # 对于助手回复，检查是否是JSON格式
                response_text = line.split(':', 1)[1].strip()
                try:
                    # 尝试解析JSON，如果成功则提取回复内容
                    response_json = json.loads(response_text)
                    if isinstance(response_json, dict) and "reply" in response_json:
                        formatted_lines.append(f"助手: {response_json['reply']}")
                    else:
                        formatted_lines.append(f"助手: {response_text}")
                except:
                    # 非JSON格式，直接使用原始文本
                    formatted_lines.append(f"助手: {response_text}")
            else:
                # 其他内容，如果看起来像对话，尝试推断角色
                if ": " in line or "： " in line:
                    parts = line.split(":", 1) if ": " in line else line.split("：", 1)
                    if len(parts) == 2:
                        role, content = parts
                        if "用户" in role.lower() or "user" in role.lower():
                            formatted_lines.append(f"用户: {content.strip()}")
                        elif "助手" in role.lower() or "assistant" in role.lower():
                            formatted_lines.append(f"助手: {content.strip()}")
                        else:
                            formatted_lines.append(line)
                    else:
                        formatted_lines.append(line)
        
        # 添加当前用户消息（如果有）
        if current_message:
            formatted_lines.append(f"用户: {current_message}")
            
        # 组合成格式化的上下文，并添加清晰的标题
        formatted_context = "对话历史：\n" + "\n".join(formatted_lines)
        
        return formatted_context

    def update_guided_user_info(self, key: str, value: str):
        """更新引导模式的局部用户信息
        
        Args:
            key: 信息键名，如"数学困难"、"喜欢的活动"等
            value: 信息值
        """
        if not self.guidance_state["is_guiding"]:
            return
        
        if not self.guided_user_info:
            self.guided_user_info = ""
        
        # 按行拆分当前用户信息
        info_lines = self.guided_user_info.split('\n')
        
        # 检查是否已存在相同的键
        key_exists = False
        for i, line in enumerate(info_lines):
            if line.startswith(f"{key}:") or line.startswith(f"{key}："):
                # 更新现有键的值
                info_lines[i] = f"{key}: {value}"
                key_exists = True
                break
        
        # 如果键不存在，添加新行
        if not key_exists:
            info_lines.append(f"{key}: {value}")
        
        # 重新组合用户信息
        self.guided_user_info = '\n'.join(info_lines)
        print(f"已更新引导模式局部用户信息: {key} = {value}")
        print(f"当前引导模式用户信息:\n{self.guided_user_info}")

    def _compress_guided_conversation_history(self, max_recent_turns=4):
        """压缩引导模式的对话历史，保留最重要的信息和最近几轮对话
        
        Args:
            max_recent_turns: 保留的最近对话轮数
        """
        if not self.guidance_state["is_guiding"] or len(self.guided_conversation_history.turns) <= max_recent_turns * 2:
            return
        
        print(f"开始压缩引导模式对话历史，当前对话历史长度: {len(self.guided_conversation_history.turns)}")
        
        # 提取所有对话轮次
        turns = self.guided_conversation_history.turns
        
        # 保留最近的几轮对话
        recent_turns = turns[-max_recent_turns*2:]
        
        # 为早期对话创建摘要
        early_turns = turns[:-max_recent_turns*2]
        if early_turns:
            # 创建一个摘要的轮次
            summary_text = f"之前的对话摘要：用户提到{self.guided_user_info}"
            
            # 使用摘要和最近的对话创建新的对话历史
            new_turns = []
            
            # 添加系统轮次来保存摘要
            new_turns.append({
                "ask": "SYSTEM_SUMMARY",
                "answer": summary_text,
                "time": early_turns[-1]["time"] if early_turns else turns[0]["time"]
            })
            
            # 添加最近的轮次
            new_turns.extend(recent_turns)
            
            # 更新对话历史
            self.guided_conversation_history.turns = new_turns
            
            print(f"对话历史压缩完成，压缩前: {len(turns)}轮，压缩后: {len(new_turns)}轮")
        else:
            print("没有早期对话需要压缩")