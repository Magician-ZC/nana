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
import db_manager

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
        self.current_user_id = "default_user"
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
        self.main_agent = MainAgent(self.llm_service, self.conversation_history, self.current_user_id)

    def _refresh_tts_services(self):
        """刷新TTS服务配置"""
        try:
            # 检查配置是否启用TTS
            if Config.is_tts_enabled():
                print("初始化普通TTS服务...")
                self.tts_service = TTSService()
            else:
                print("普通TTS服务已禁用")
                self.tts_service = None
                
            # 检查配置是否启用超拟人TTS
            if Config.is_super_tts_enabled():
                print("初始化超拟人TTS服务...")
                self.super_tts_service = SuperTTSService()
            else:
                print("超拟人TTS服务已禁用")
                self.super_tts_service = None
                
            print(f"TTS服务刷新完成: 普通TTS={self.tts_service is not None}, 超拟人TTS={self.super_tts_service is not None}")
            
        except Exception as e:
            print(f"刷新TTS服务失败: {e}")
            import traceback
            traceback.print_exc()
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

    async def switch_user(self, username: str, session_id: str):
        """切换当前用户
        
        Args:
            username: 用户名
            session_id: 会话ID
            
        Returns:
            bool: 是否成功切换
        """
        if not username:
            return False
            
        print(f"切换用户: {username}")
        
        # 更新当前用户ID
        self.current_user_id = username
        
        # 重置引导状态
        self._reset_guidance_state()
        
        # 初始化新的对话历史记录
        self.conversation_history = ConversationHistory(max_turns=Config.MAX_TURNS)
        
        # 重新初始化主智能体，使用新的用户ID和对话历史
        self.main_agent = MainAgent(self.llm_service, self.conversation_history, username)
        
        # 加载用户聊天历史
        await self._load_user_chat_history(username)
        
        # 加载用户配置并应用
        await self._load_user_settings(username)
        
        return True

    async def _load_user_chat_history(self, username: str):
        """加载用户聊天历史
        
        Args:
            username: 用户名
            
        Returns:
            bool: 是否成功加载
        """
        try:
            # 使用db_manager加载用户聊天历史
            chat_history = await db_manager.load_user_chat_history(username)
            
            if chat_history:
                # 为防止历史记录过长，只加载最近的20条（或配置的最大轮数）
                max_turns = min(len(chat_history), Config.MAX_TURNS)
                recent_history = chat_history[-max_turns:]
                
                print(f"为用户 {username} 加载了 {len(recent_history)} 条聊天历史")
                
                # 添加到对话历史
                for msg in recent_history:
                    if "user_message" in msg and "assistant_message" in msg:
                        await self.conversation_history.add_dialog(
                            msg["user_message"], 
                            msg["assistant_message"]
                        )
                
                return True
            else:
                print(f"用户 {username} 没有聊天历史")
                return False
                
        except Exception as e:
            print(f"加载用户聊天历史时出错: {e}")
            return False

    async def _load_user_settings(self, username: str):
        """加载用户设置并应用
        
        Args:
            username: 用户名
            
        Returns:
            bool: 是否成功加载
        """
        try:
            # 初始化用户信息管理器
            from user_info_manager import UserInfoManager
            user_info_manager = UserInfoManager(username)
            
            # 获取用户UI设置
            ui_settings = await user_info_manager.get_ui_settings()
            
            if ui_settings:
                # 应用UI设置到全局配置
                from config import Config
                
                # 更新全局TTS开关
                if "enable_tts_global" in ui_settings:
                    Config.ENABLE_TTS_GLOBAL = ui_settings["enable_tts_global"]
                
                # 更新TTS启用状态
                if "enable_tts" in ui_settings:
                    Config.ENABLE_TTS = ui_settings["enable_tts"]
                if "enable_super_tts" in ui_settings:
                    Config.ENABLE_SUPER_TTS = ui_settings["enable_super_tts"]
                
                # 更新TTS语音配置
                if "tts_voice" in ui_settings:
                    Config.TTS_VCN = ui_settings["tts_voice"]
                if "super_tts_voice" in ui_settings:
                    Config.SUPER_TTS_VCN = ui_settings["super_tts_voice"]
                
                # 更新其他配置
                if "tts_speed" in ui_settings:
                    Config.TTS_SPEED = ui_settings["tts_speed"]
                if "typing_speed" in ui_settings:
                    Config.TYPING_SPEED = ui_settings["typing_speed"]
                if "voice_input_mode" in ui_settings:
                    Config.VOICE_INPUT_MODE = ui_settings["voice_input_mode"]
                if "voice_timeout" in ui_settings:
                    Config.VOICE_TIMEOUT = ui_settings["voice_timeout"]
                
                # 重新初始化TTS服务以应用新设置
                self._refresh_tts_services()
                
                print(f"已加载并应用用户 {username} 的设置: {ui_settings}")
                return True
            else:
                print(f"用户 {username} 没有设置，使用默认配置")
                return False
                
        except Exception as e:
            print(f"加载用户设置时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def change_agent(self, agent_name: str, session_id: str) -> bool:
        """
        切换智能体
        :param agent_name: 智能体名称
        :param session_id: 会话ID
        :return: 是否成功切换
        """
        print(f"尝试切换智能体: {agent_name}")
        try:
            if agent_name in ["nanaA", "nanaB", "nanaC"]:
                success = self.main_agent.set_agent(agent_name)
                print(f"切换到内置智能体: {agent_name}, 结果: {'成功' if success else '失败'}")
                return success
            elif agent_name.startswith("custom_"):
                # 确保custom_agents_dir目录存在
                os.makedirs(self.custom_agents_dir, exist_ok=True)
                
                # 加载自定义角色
                config_path = os.path.join(self.custom_agents_dir, f"{agent_name}.json")
                prompt_path = os.path.join(self.custom_agents_dir, f"{agent_name}.txt")
                
                print(f"加载自定义智能体文件: config={config_path}, prompt={prompt_path}")
                
                if os.path.exists(config_path) and os.path.exists(prompt_path):
                    try:
                        # 读取配置文件
                        with open(config_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                        
                        # 读取提示词文件
                        with open(prompt_path, "r", encoding="utf-8") as f:
                            prompt = f.read()
                        
                        # 设置自定义角色
                        success = self.main_agent.set_custom_agent(prompt, config)
                        print(f"加载自定义智能体: {agent_name}, 结果: {'成功' if success else '失败'}")
                        return success
                    except Exception as e:
                        print(f"加载自定义角色失败: {e}")
                        return False
                else:
                    missing_files = []
                    if not os.path.exists(config_path):
                        missing_files.append(config_path)
                    if not os.path.exists(prompt_path):
                        missing_files.append(prompt_path)
                    print(f"自定义角色文件不存在: {agent_name}, 缺少文件: {', '.join(missing_files)}")
                    return False
            
            print(f"不支持的智能体类型: {agent_name}")
            return False
        except Exception as e:
            print(f"切换智能体时发生异常: {e}")
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
                
                # 获取TTS设置
                user_tts_enabled = Config.ENABLE_TTS
                user_super_tts_enabled = Config.ENABLE_SUPER_TTS
                
                try:
                    # 尝试从用户信息管理器获取设置
                    from user_info_manager import UserInfoManager
                    user_info_manager = UserInfoManager(self.current_user_id)
                    ui_settings = await user_info_manager.get_ui_settings()
                    
                    if ui_settings:
                        # 优先使用用户自定义设置
                        user_tts_enabled = ui_settings.get('enable_tts', Config.ENABLE_TTS)
                        user_super_tts_enabled = ui_settings.get('enable_super_tts', Config.ENABLE_SUPER_TTS)
                except Exception as e:
                    print(f"结束引导时获取用户TTS设置出错，使用全局设置: {e}")
                
                # 尝试生成语音
                if user_tts_enabled and Config.is_tts_enabled() and self.tts_service:
                    try:
                        print("为结束引导回复生成普通TTS...")
                        audio_data = self.tts_service.generate_audio(reply_text)
                        if audio_data and len(audio_data) > 100:
                            print(f"结束引导普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                    except Exception as e:
                        print(f"为结束引导回复生成普通语音时出错: {e}")
                
                if (not audio_data or len(audio_data) < 100) and user_super_tts_enabled and Config.is_super_tts_enabled() and self.super_tts_service:
                    try:
                        print("为结束引导回复生成超拟人TTS...")
                        audio_data = self.super_tts_service.generate_audio(reply_text)
                        if audio_data and len(audio_data) > 100:
                            print(f"结束引导超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                    except Exception as e:
                        print(f"为结束引导回复生成超拟人语音时出错: {e}")
                
                return reply_text, audio_data
                
            # 是否快速提问模式
            is_quick_question = is_category
            
            # 如果之前处于引导模式且尚未明确退出，则继续处于引导模式
            if self.guidance_state["is_guiding"] and not getattr(self.guidance_state, "confirmed_exit", False):
                print("检测到处于引导模式中，继续进行引导式对话")
                is_quick_question = True
                
                # 在上次更新时间超过5分钟后，自动退出引导模式
                if time.time() - self.guidance_state["last_update_time"] > 300:  # 5分钟 = 300秒
                    print("引导会话已超过5分钟未活动，自动退出引导模式")
                    is_quick_question = False
                    self._reset_guidance_state()
                    
                    # 添加一个提示信息表明引导已经超时结束
                    reply_text = "由于对话中断较长时间，我们的引导对话已经结束。您有什么新的问题吗？"
                    
                    # 生成语音
                    audio_data = None
                    
                    # 获取TTS设置
                    user_tts_enabled = Config.ENABLE_TTS
                    user_super_tts_enabled = Config.ENABLE_SUPER_TTS
                    
                    try:
                        # 尝试从用户信息管理器获取设置
                        from user_info_manager import UserInfoManager
                        user_info_manager = UserInfoManager(self.current_user_id)
                        ui_settings = await user_info_manager.get_ui_settings()
                        
                        if ui_settings:
                            # 优先使用用户自定义设置
                            user_tts_enabled = ui_settings.get('enable_tts', Config.ENABLE_TTS)
                            user_super_tts_enabled = ui_settings.get('enable_super_tts', Config.ENABLE_SUPER_TTS)
                    except Exception as e:
                        print(f"引导超时时获取用户TTS设置出错，使用全局设置: {e}")
                    
                    # 尝试生成语音
                    if user_tts_enabled and Config.is_tts_enabled() and self.tts_service:
                        try:
                            print("为引导超时回复生成普通TTS...")
                            audio_data = self.tts_service.generate_audio(reply_text)
                            if audio_data and len(audio_data) > 100:
                                print(f"引导超时普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                        except Exception as e:
                            print(f"为引导超时结束生成语音时出错: {e}")
                    
                    if (not audio_data or len(audio_data) < 100) and user_super_tts_enabled and Config.is_super_tts_enabled() and self.super_tts_service:
                        try:
                            print("为引导超时回复生成超拟人TTS...")
                            audio_data = self.super_tts_service.generate_audio(reply_text)
                            if audio_data and len(audio_data) > 100:
                                print(f"引导超时超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                        except Exception as e:
                            print(f"为引导超时结束生成超拟人语音时出错: {e}")
                    
                    return reply_text, audio_data
                
                # 更新最后活动时间
                self.guidance_state["last_update_time"] = time.time()

            # 使用流式模式还是常规模式
            if stream:
                reply_stream = self.response_stream(message, session_id, agent_type, personality, is_quick_question)
                return reply_stream, None
            else:
                # 非流式模式：生成完整回复后返回
                reply, audio_data = await self._generate_complete_reply(message, session_id, agent_type, personality, is_quick_question)
                
                # 确保reply是文本内容，而不是JSON
                if isinstance(reply, str):
                    reply = reply.strip()
                    if (reply.startswith('{') and reply.endswith('}')):
                        try:
                            # 尝试解析JSON
                            reply_json = json.loads(reply)
                            if 'reply' in reply_json:
                                # 只取reply字段的内容
                                reply = reply_json['reply']
                                print("在generate_reply中从JSON提取纯文本回复:", reply)
                        except json.JSONDecodeError:
                            # 尝试修复双花括号格式
                            if reply.startswith('{{') and reply.endswith('}}'):
                                try:
                                    fixed_json = reply.replace('{{', '{').replace('}}', '}')
                                    reply_json = json.loads(fixed_json)
                                    if 'reply' in reply_json:
                                        reply = reply_json['reply']
                                        print("在generate_reply中从双花括号JSON提取reply字段")
                                except:
                                    print("在generate_reply中修复双花括号格式失败")
                
                # 保存当前回复内容
                self.current_response = reply
                
                # 返回文本回复和音频数据
                return reply, audio_data
                
        except Exception as e:
            error_msg = f"生成回复时出错: {str(e)}"
            traceback.print_exc()
            print(error_msg)
            return f"抱歉，我遇到了一些问题: {str(e)}", None

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

    async def _generate_complete_reply(self, message: str, session_id: str, agent_type: Optional[str] = None, personality: Optional[str] = None, is_category: bool = False) -> Tuple[str, Optional[bytes]]:
        """生成完整回复（内部方法）
        
        Args:
            message: 用户消息
            session_id: 会话ID
            agent_type: 智能体类型
            personality: 智能体性格描述
            is_category: 是否是快捷提问类别
            
        Returns:
            Tuple[str, Optional[bytes]]: (回复文本, 语音数据)
        """
        try:
            # 使用main_agent生成回复
            reply_text, expression = await self.main_agent.reply(
                message=message,
                personality=personality,
                is_category=is_category
            )
            
            # 确保纯文本回复格式，移除JSON
            if isinstance(reply_text, str):
                # 检查是否是JSON格式
                reply_text = reply_text.strip()
                if (reply_text.startswith('{') and reply_text.endswith('}')):
                    try:
                        # 尝试解析JSON
                        reply_json = json.loads(reply_text)
                        if 'reply' in reply_json:
                            # 只取reply字段的内容
                            reply_text = reply_json['reply']
                            print("从JSON中提取纯文本回复:", reply_text)
                    except json.JSONDecodeError:
                        # 不是标准JSON，检查是否是双花括号格式
                        if reply_text.startswith('{{') and reply_text.endswith('}}'):
                            print("检测到双花括号格式，尝试修正")
                            fixed_json = reply_text.replace('{{', '{').replace('}}', '}')
                            try:
                                reply_json = json.loads(fixed_json)
                                if 'reply' in reply_json:
                                    reply_text = reply_json['reply']
                                    print("从双花括号JSON中提取reply字段")
                            except json.JSONDecodeError:
                                print("双花括号内容不是有效的JSON格式，继续处理")
            
            # 生成语音 - 根据用户设置决定是否生成
            audio_data = None
            
            # 获取当前用户的TTS设置
            user_tts_enabled = Config.ENABLE_TTS
            user_super_tts_enabled = Config.ENABLE_SUPER_TTS
            user_tts_global_enabled = Config.ENABLE_TTS_GLOBAL
            
            try:
                # 尝试从用户信息管理器获取设置
                from user_info_manager import UserInfoManager
                user_info_manager = UserInfoManager(self.current_user_id)
                ui_settings = await user_info_manager.get_ui_settings()
                
                if ui_settings:
                    # 优先使用用户自定义设置
                    user_tts_global_enabled = ui_settings.get('enable_tts_global', Config.ENABLE_TTS_GLOBAL)
                    user_tts_enabled = ui_settings.get('enable_tts', Config.ENABLE_TTS)
                    user_super_tts_enabled = ui_settings.get('enable_super_tts', Config.ENABLE_SUPER_TTS)
                    print(f"从用户信息管理器获取TTS设置: 全局TTS开关={user_tts_global_enabled}, 普通TTS={user_tts_enabled}, 超拟人TTS={user_super_tts_enabled}")
            except Exception as e:
                print(f"获取用户TTS设置时出错，使用全局设置: {e}")
                
            # 只有当启用了全局TTS开关和普通TTS时才尝试生成
            if user_tts_global_enabled and user_tts_enabled and Config.is_tts_enabled() and self.tts_service:
                try:
                    print("尝试生成普通TTS...")
                    audio_data = self.tts_service.generate_audio(reply_text)
                    if audio_data and len(audio_data) > 100:
                        print(f"普通TTS生成成功，音频大小: {len(audio_data)} 字节")
                    else:
                        print("普通TTS生成失败: 生成的音频数据无效或过小")
                except Exception as e:
                    print(f"生成普通TTS时出错: {e}")
            else:
                print(f"跳过普通TTS生成: 用户设置={user_tts_enabled}, 全局设置={Config.ENABLE_TTS}, 服务可用={self.tts_service is not None}")
            
            # 只有当启用了全局TTS开关和超拟人TTS且普通TTS失败时才尝试生成
            if (not audio_data or len(audio_data) < 100) and user_tts_global_enabled and user_super_tts_enabled and Config.is_super_tts_enabled() and self.super_tts_service:
                try:
                    print("尝试生成超拟人TTS...")
                    audio_data = self.super_tts_service.generate_audio(reply_text)
                    if audio_data and len(audio_data) > 100:
                        print(f"超拟人TTS生成成功，音频大小: {len(audio_data)} 字节")
                    else:
                        print("超拟人TTS生成失败: 生成的音频数据无效或过小")
                except Exception as e:
                    print(f"生成超拟人TTS时出错: {e}")
            elif not audio_data or len(audio_data) < 100:
                print(f"跳过或无法生成超拟人TTS: 全局TTS开关={user_tts_global_enabled}, 用户设置={user_super_tts_enabled}, 全局设置={Config.ENABLE_SUPER_TTS}, 服务可用={self.super_tts_service is not None}")
            
            return reply_text, audio_data
        except Exception as e:
            print(f"生成完整回复时出错: {e}")
            traceback.print_exc()
            return f"抱歉，生成回复时遇到了问题: {str(e)}", None
    
    async def get_response(self, message: str, personality: Optional[str] = None, session_id: str = "default", user_id: str = "default_user") -> Tuple[str, Optional[bytes]]:
        """处理WebSocket聊天请求
        
        Args:
            message: 用户消息
            personality: 可选的性格描述
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            Tuple[str, Optional[bytes]]: (回复文本, 语音数据)
        """
        # 如果用户ID与当前用户不同，切换用户
        if user_id != self.current_user_id:
            print(f"WebSocket请求中检测到不同用户，从 {self.current_user_id} 切换到 {user_id}")
            await self.switch_user(user_id, session_id)
        
        # 生成回复
        reply, audio_data = await self.generate_reply(
            message, 
            session_id,
            personality=personality
        )
        
        return reply, audio_data