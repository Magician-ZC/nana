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
from embedding import EmbeddingService
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

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
        
        # 初始化向量服务用于快速回复
        self.embedding_service = EmbeddingService(
            Config.EMBEDDING_API_KEY,  # 使用专门的Embedding API密钥
            Config.EMBEDDING_API_URL,
            Config.EMBEDDING_MODEL,
            Config.EMBEDDING_DIMENSION
        )
        
        # 加载向量数据库 (如果存在)
        self.vector_db = self._load_vector_db()

    def _load_vector_db(self):
        """加载向量数据库，如果不存在则返回空数据库"""
        vector_db_path = "save/vector_db.json"
        if os.path.exists(vector_db_path):
            try:
                with open(vector_db_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载向量数据库失败: {e}")
        return {"questions": [], "embeddings": [], "answers": []}

    def _is_user_info_related(self, message: str) -> bool:
        """判断用户消息是否与个人信息相关"""
        personal_keywords = [
            "我的", "我是", "我们", "我想", "我要", "我有", "我感觉", "我觉得", 
            "我喜欢", "我讨厌", "我的家", "我的工作", "我的学习", "我的健康",
            "我的朋友", "我的家人", "我的情感", "我最近", "我今天", "我昨天",
            "你记得我", "你知道我", "还记得我", "帮我", "告诉我", "我多大",
            "你认识我", "我们见过", "我们聊过", "你了解我", "名字", "年龄", 
            "性别", "专业", "学校", "工作", "家庭", "爱好", "能力", "性格"
        ]
        
        for keyword in personal_keywords:
            if keyword in message:
                return True
        return False

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
        
    async def fast_reply(self, message: str) -> Tuple[str, str]:
        """
        使用向量检索快速生成回复，不涉及用户信息处理
        
        Args:
            message: 用户消息
            
        Returns:
            Tuple[str, str]: (回复文本, 表情)
        """
        try:
            # 首先检查向量数据库是否为空
            if not self.vector_db or not self.vector_db.get("embeddings") or len(self.vector_db["embeddings"]) == 0:
                print("向量数据库为空，无法使用快速回复")
                return None, None
                
            # 获取消息的向量表示
            try:
                embedding = self.embedding_service.get_embedding(message)
                if not embedding:
                    print("无法获取消息的向量表示，跳过快速回复")
                    return None, None
            except Exception as e:
                print(f"获取向量表示时出错: {e}")
                return None, None
                
            # 计算与所有已知问题的相似度
            try:
                similarities = []
                for stored_embedding in self.vector_db["embeddings"]:
                    similarity = cosine_similarity([embedding], [stored_embedding])[0][0]
                    similarities.append(similarity)
                    
                # 找到最相似的问题
                max_similarity_index = np.argmax(similarities)
                max_similarity = similarities[max_similarity_index]
                
                # 如果相似度超过阈值，返回对应回答
                if max_similarity > 0.85:  # 设置一个相对严格的阈值
                    answer = self.vector_db["answers"][max_similarity_index]
                    # 随机选择一个适合的表情
                    expression = "开心"  # 默认表情
                    
                    print(f"使用向量检索快速回复，相似度: {max_similarity:.4f}")
                    return answer, expression
            except Exception as e:
                print(f"计算相似度时出错: {e}")
                return None, None
                
        except Exception as e:
            print(f"快速回复处理出错: {e}")
            
        return None, None

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
            
            # 对于非分类问题，尝试快速回复
            reply = None
            expression = None
            guidance_message = None
            
            if not is_category and not self._is_user_info_related(message):
                # 尝试使用向量检索进行快速回复
                print("尝试使用向量检索进行快速回复...")
                reply, expression = await self.fast_reply(message)
            
            # 如果快速回复未成功，使用完整流程
            if not reply:
                # 使用 MainAgent 生成回复和表情，传入性格描述和快捷提问标志
                reply, expression = await self.main_agent.reply(message, personality=personality, is_category=is_category)
            
            # 确保回复不为空
            if not reply:
                return "抱歉，我现在无法回答您的问题，请稍后再试。", None, "生气", None
            
            # 检查是否有引导决策消息
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
            
            # 异步处理TTS生成
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
            
            # 如果有引导决策消息，同样为其生成语音并保存到临时属性中
            if guidance_message:
                try:
                    # 使用异步方式生成语音，避免阻塞
                    loop = asyncio.get_running_loop()
                    
                    # 如果有超拟人TTS服务并启用了超拟人TTS
                    if self.super_tts_service:
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
                    
                    # 如果超拟人TTS失败或未启用，尝试使用普通TTS
                    if not hasattr(self.main_agent.conversation_history, 'guidance_audio') and self.tts_service:
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
                
                except Exception as e:
                    print(f"生成引导决策语音时出错: {e}")
            
            return reply, audio_data, expression, guidance_message
            
        except Exception as e:
            print(f"生成回复时出错: {e}")
            return "抱歉，发生了错误，请稍后再试。", None, "生气", None